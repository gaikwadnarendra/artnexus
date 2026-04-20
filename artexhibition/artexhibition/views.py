from django.shortcuts import render,redirect,HttpResponse
from django.contrib.auth import authenticate, login,logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from artapp.models import *
from django.contrib.auth import *
from django.db import IntegrityError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import random
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.db.models import *
from django.core.mail import *
from django.conf import settings
from django.shortcuts import get_object_or_404, render, redirect
import json
import re
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

User = get_user_model()

# #temporary
# from django.contrib.auth import get_user_model
# from django.http import HttpResponse

# User = get_user_model()

# def fix_admin(request):
#     try:
#         user = User.objects.filter(username__iexact='admin').first()

#         if user:
#             user.set_password('admin123')
#             user.save()
#             return HttpResponse("Password Reset Done ✅")
#         else:
#             User.objects.create_superuser(
#                 username='admin',
#                 email='admin@gmail.com',
#                 password='admin123'
#             )
#             return HttpResponse("Admin Created ✅")

#     except Exception as e:
#         return HttpResponse(f"Error: {str(e)}")


@csrf_exempt
def chatbot(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST request required"}, status=405)

    try:
        data = json.loads(request.body)
        messages = data.get("messages", [])

        if not messages:
            return JsonResponse({"error": "No messages provided"}, status=400)

        user_msg = messages[-1]["content"]
        user_lower = user_msg.lower()

        # =====================================================
        # 🧠 1. SMART INTENT DETECTION
        # =====================================================
        def detect_intent(msg):
            msg = msg.lower()

            if any(w in msg for w in ["show", "display", "list", "find", "buy"]):
                return "search"

            if any(w in msg for w in ["under", "price", "cheap", "cost"]):
                return "search"

            if "artist" in msg or "by" in msg:
                return "search"

            if "cart" in msg:
                return "cart"

            if "wishlist" in msg:
                return "wishlist"

            if "order" in msg:
                return "order"

            return "chat"

        intent = detect_intent(user_msg)

        # =====================================================
        # 🎨 2. SEARCH FLOW
        # =====================================================
        if intent == "search":

            # 🔥 AI FILTER EXTRACTION
            filter_prompt = f"""
            Extract filters from user query.

            Fields:
            - artist
            - price_max
            - art_type
            - medium
            - sort (cheap, expensive, latest)

            Return ONLY JSON:
            {{
                "artist": null,
                "price_max": null,
                "art_type": null,
                "medium": null,
                "sort": null
            }}

            Query: "{user_msg}"
            """

            filters = {}

            try:
                res = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "mistralai/mistral-7b-instruct",
                        "messages": [{"role": "user", "content": filter_prompt}],
                        "temperature": 0,
                    },
                    timeout=10,
                )

                if res.status_code == 200:
                    content = res.json()["choices"][0]["message"]["content"]
                    filters = json.loads(content)

            except:
                filters = {}

            # =====================================================
            # 🗄️ DB QUERY
            # =====================================================
            products = Artproducts.objects.all()

            # ALL ART
            if "all" in user_lower:
                products = products.order_by("-creationdate")

            # ARTIST
            if filters.get("artist"):
                products = products.filter(
                    artist__name__icontains=filters["artist"]
                )

            # PRICE
            if filters.get("price_max"):
                products = products.filter(
                    sellingprice__lte=filters["price_max"]
                )

            # ART TYPE
            if filters.get("art_type"):
                products = products.filter(
                    arttype__arttype__icontains=filters["art_type"]
                )

            # MEDIUM
            if filters.get("medium"):
                products = products.filter(
                    artmedium__artmedium__icontains=filters["medium"]
                )

            # =====================================================
            # 🔥 SORTING
            # =====================================================
            if filters.get("sort") == "cheap":
                products = products.order_by("sellingprice")

            elif filters.get("sort") == "expensive":
                products = products.order_by("-sellingprice")

            elif filters.get("sort") == "latest":
                products = products.order_by("-creationdate")

            else:
                products = products.order_by("sellingprice")

            products = products[:5]

            # =====================================================
            # 🎯 RESPONSE
            # =====================================================
            if products.exists():
                reply = "🎨 Here are some artworks:\n\n"

                for p in products:
                    reply += f"""
                            🖼️ {p.title}
                            👨‍🎨 {p.artist.name if p.artist else 'Unknown'}
                            💰 ₹{p.sellingprice}

                        """

                # 🔥 RECOMMENDATION
                first = products.first()

                similar = Artproducts.objects.filter(
                    Q(arttype=first.arttype) |
                    Q(artmedium=first.artmedium)
                ).exclude(id=first.id)[:3]

                if similar:
                    reply += "\n🔥 You may also like:\n\n"
                    for s in similar:
                        reply += f"• {s.title} - ₹{s.sellingprice}\n"

            else:
                reply = "😔 No artworks found."

            return JsonResponse({"reply": reply})

        # =====================================================
        # 🛒 3. CART FUNCTIONALITY
        # =====================================================
        elif intent == "cart":
            if not request.user.is_authenticated:
                return JsonResponse({"reply": "⚠️ Please login first."})

            # simple product detect (first match)
            product = Artproducts.objects.filter(
                title__icontains=user_msg
            ).first()

            if product:
                cart_item, created = Cart.objects.get_or_create(
                    user=request.user,
                    product=product
                )
                if not created:
                    cart_item.quantity += 1
                    cart_item.save()

                return JsonResponse({
                    "reply": f"✅ Added {product.title} to cart."
                })

            return JsonResponse({"reply": "❌ Product not found."})

        # =====================================================
        # ❤️ 4. WISHLIST
        # =====================================================
        elif intent == "wishlist":
            if not request.user.is_authenticated:
                return JsonResponse({"reply": "⚠️ Please login first."})

            product = Artproducts.objects.filter(
                title__icontains=user_msg
            ).first()

            if product:
                Wishlist.objects.get_or_create(
                    user=request.user,
                    product=product
                )

                return JsonResponse({
                    "reply": f"❤️ Added {product.title} to wishlist."
                })

            return JsonResponse({"reply": "❌ Product not found."})

        # =====================================================
        # 📦 5. ORDER TRACK
        # =====================================================
        elif intent == "order":
            if not request.user.is_authenticated:
                return JsonResponse({"reply": "⚠️ Please login first."})

            orders = Order.objects.filter(user=request.user).order_by("-created_at")[:3]

            if orders:
                reply = "📦 Your recent orders:\n\n"
                for o in orders:
                    reply += f"• Order #{o.id} - {o.status}\n"
            else:
                reply = "No orders found."

            return JsonResponse({"reply": reply})

        # =====================================================
        # 🤖 6. NORMAL CHAT
        # =====================================================
        else:
            chat_prompt = f"""
            You are ArtNexus AI 🎨.
            Be friendly and helpful.

            User: {user_msg}
            """

            res = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gryphe/mythomax-l2-13b",
                    "messages": [{"role": "user", "content": chat_prompt}],
                    "temperature": 0.7,
                },
                timeout=20,
            )

            reply = res.json()["choices"][0]["message"]["content"]

            return JsonResponse({"reply": reply})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
# @csrf_exempt
# def chatbot(request):
#     if request.method != "POST":
#         return JsonResponse({"error": "POST request required"}, status=405)

#     try:
#         data = json.loads(request.body)
#         messages = data.get("messages", [])

#         if not messages:
#             return JsonResponse({"error": "No messages provided"}, status=400)

#         user_msg = messages[-1]["content"]
#         user_lower = user_msg.lower()

#         # =========================================================
#         # 🔥 1. HYBRID INTENT DETECTION (FINAL FIX)
#         # =========================================================
#         search_keywords = [
#             "show", "art", "painting", "artwork",
#             "buy", "price", "under", "cheap", "find"
#         ]

#         intent = "chat"

#         if any(word in user_lower for word in search_keywords):
#             intent = "search"

#         # ❗ override for question-type queries
#         if any(word in user_lower for word in ["what", "help", "explain", "meaning", "why"]):
#             intent = "chat"

#         # =========================================================
#         # 🎨 2. SEARCH FLOW (DB + AI FILTER)
#         # =========================================================
#         if intent == "search":

#             # 🔥 AI FILTER (optional but powerful)
#             filter_prompt = f"""
#             Extract filters from user query.

#             Fields:
#             - artist
#             - price_max
#             - art_type

#             Return ONLY JSON:
#             {{"artist": null, "price_max": null, "art_type": null}}

#             Query: "{user_msg}"
#             """

#             filters = {}

#             try:
#                 res = requests.post(
#                     "https://openrouter.ai/api/v1/chat/completions",
#                     headers={
#                         "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
#                         "Content-Type": "application/json",
#                     },
#                     json={
#                         "model": "mistralai/mistral-7b-instruct",
#                         "messages": [{"role": "user", "content": filter_prompt}],
#                         "temperature": 0,
#                     },
#                     timeout=10,
#                 )

#                 print(f"OpenRouter Status: {res.status_code}")
#                 print(f"OpenRouter Response: {res.text}")

#                 if res.status_code == 200:
#                     content = res.json()["choices"][0]["message"]["content"]
#                     filters = json.loads(content)

#             except:
#                 filters = {}

#             # =====================================================
#             # 🔥 DB QUERY
#             # =====================================================
#             products = Artproducts.objects.all()

#             if filters.get("artist"):
#                 products = products.filter(
#                     artist__name__icontains=filters["artist"]
#                 )

#             if filters.get("price_max"):
#                 products = products.filter(
#                     sellingprice__lte=filters["price_max"]
#                 )

#             if filters.get("art_type"):
#                 products = products.filter(
#                     arttype__name__icontains=filters["art_type"]
#                 )

#             # =====================================================
#             # 🔥 SMART SORTING
#             # =====================================================
#             if filters.get("artist"):
#                 products = products.annotate(
#                     match_score=Case(
#                         When(artist__name__icontains=filters["artist"], then=Value(2)),
#                         default=Value(0),
#                         output_field=IntegerField(),
#                     )
#                 ).order_by("-match_score", "sellingprice")
#             else:
#                 products = products.order_by("sellingprice")

#             products = products[:5]

#             # =====================================================
#             # 🔥 RESPONSE + RECOMMENDATION
#             # =====================================================
#             if products.exists():
#                 reply = "🎨 Here are artworks:\n\n"

#                 for p in products:
#                     reply += f"""• {p.title}
#                         Price: ${p.sellingprice}
#                         Artist: {p.artist.name}
#                     """

#                 # 🔥 SIMILAR PRODUCTS
#                 first = products.first()

#                 similar = Artproducts.objects.filter(
#                     arttype=first.arttype
#                 ).exclude(id=first.id)[:3]

#                 if similar:
#                     reply += "\n🔥 You may also like:\n\n"
#                     for s in similar:
#                         reply += f"""• {s.title}
#                         Price: ${s.sellingprice}

#                         """

#             else:
#                 reply = "😔 No matching artworks found."

#             return JsonResponse({"reply": reply})

#         # =========================================================
#         # 🤖 3. NORMAL CHAT (AI)
#         # =========================================================
#         chat_prompt = f"""
#                         You are ArtNexus AI 🎨.
#                         Be friendly and helpful.

#                         User: {user_msg}
#                         """

#         res = requests.post(
#             "https://openrouter.ai/api/v1/chat/completions",
#             headers={
#                 "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
#                 "Content-Type": "application/json",
#             },
#             json={
#                 "model": "gryphe/mythomax-l2-13b",
#                 "messages": [{"role": "user", "content": chat_prompt}],
#                 "temperature": 0.7,
#                 "max_tokens": 300,
#             },
#             timeout=20,
#         )

#         reply = res.json()["choices"][0]["message"]["content"]

#         return JsonResponse({"reply": reply})

#     except Exception as e:
#         import traceback
#         error_detail = traceback.format_exc()
#         print(f"CHATBOT ERROR: {error_detail}")  # Render logs mein dikhega
#         return JsonResponse({"error": str(e), "detail": error_detail}, status=500)
    
@csrf_exempt
def chat_page(request):
    return render(request, "chat.html")
    
# Main Logic

def BASE(request):    
       return render(request,'base.html')


def BASE1(request):    
    return render(request,'base1.html')

def Header(request):
    arttypes = Arttype.objects.all() 
    return render(request,'includes1/header.html', {'arttypes': arttypes})


def Index(request):
    artproducts1 = Artproducts.objects.all()
     
    context = {
        
        "artproducts1":artproducts1,
      
    }
    return render(request,'index.html',context)

def ABOUTUS(request):
    first_page = Page.objects.first()
    context = {
        "page": first_page,
    }
    return render(request, 'aboutus.html', context)

def CONTACTUS(request):
    first_page = Page.objects.first()
    context = {
        "page": first_page,
    }
    return render(request, 'contactus.html', context)

def VIEW_SINGLEPRODUCTS(request,id):    
    sinprod = Artproducts.objects.get(id =id)
     
    context = {
        
        "sinprod":sinprod,
      
    }
    return render(request,'single-artproduct-details.html',context)

def arttype_detail(request, id):
    arttype_id = get_object_or_404(Arttype, id=id)
    artproducts = Artproducts.objects.filter(arttype=arttype_id)  # Using the related_name 'artproducts'
    return render(request, 'arttype_prodetail.html', {'arttype_id': arttype_id, 'artproducts': artproducts})

def ENQUIRY(request,id):    
    sinprod = Artproducts.objects.get(id =id)
     
    context = {
        
        "sinprod":sinprod,
      
    }
    return render(request,'enquiry.html',context)


def ENQUIRY_DETAILS(request):
    if request.method == "POST":
        try:
            # Retrieve the Artproducts instance using the provided prod_id
            prod_id = request.POST['prod_id']
            art_product = Artproducts.objects.get(pk=prod_id)

            # Create the Enquiry object with the Artproducts instance
            enquirynumber = random.randint(100000000, 999999999)
            enq_obj = Enquiry(
                enquirynumber=enquirynumber,
                fullname=request.POST['fullname'],
                prod_id=art_product,
                email=request.POST['email'],
                mobnum=request.POST['mobnum'],
                message=request.POST['message'],
            )
            enq_obj.save()           
            return redirect('thank_you', enquirynumber=enquirynumber)
        except Artproducts.DoesNotExist:
            messages.error(request, "The selected product does not exist")
        except IntegrityError:
            messages.error(request, "Email and Mobile number must be unique")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
    
    return render(request, 'enquiry.html')

def THANKYOU(request, enquirynumber):
    context = {
        "enquirynumber": enquirynumber,
    }
    return render(request, 'thankyou.html', context)


def ARTPRODUCTLIST(request):
    query      = request.GET.get('q', '').strip()
    art_type   = request.GET.get('arttype', '').strip()
    price_min  = request.GET.get('price_min', '').strip()
    price_max  = request.GET.get('price_max', '').strip()
    sort_by    = request.GET.get('sort', '').strip()
 
    artproduct_list = Artproducts.objects.all()
 
    # ── SEARCH ──
    if query:
        artproduct_list = artproduct_list.filter(
            Q(title__icontains=query) |
            Q(artist__name__icontains=query) |
            Q(artmedium__artmedium__icontains=query) |
            Q(description__icontains=query)
        )
 
    # ── FILTER: Art Type ──
    if art_type:
        artproduct_list = artproduct_list.filter(arttype__id=art_type)
 
    # ── FILTER: Price Range ──
    if price_min:
        try:
            artproduct_list = artproduct_list.filter(sellingprice__gte=float(price_min))
        except ValueError:
            pass
    if price_max:
        try:
            artproduct_list = artproduct_list.filter(sellingprice__lte=float(price_max))
        except ValueError:
            pass
 
    # ── SORT ──
    sort_map = {
        'price_low':  'sellingprice',
        'price_high': '-sellingprice',
        'newest':     '-id',
        'oldest':     'id',
        'name_az':    'title',
        'name_za':    '-title',
    }
    artproduct_list = artproduct_list.order_by(sort_map.get(sort_by, '-id'))
 
    # ── SUGGESTIONS (AJAX) ──
    if request.GET.get('suggest'):
        q = request.GET.get('q', '').strip()
        suggestions = []
        if q:
            titles   = Artproducts.objects.filter(title__icontains=q).values_list('title', flat=True).distinct()[:4]
            artists  = Artproducts.objects.filter(artist__name__icontains=q).values_list('artist__name', flat=True).distinct()[:2]
            mediums  = Artproducts.objects.filter(artmedium__artmedium__icontains=q).values_list('artmedium__artmedium', flat=True).distinct()[:2]
            for t in titles:
                suggestions.append({'label': t, 'type': 'Artwork'})
            for a in artists:
                if a:
                    suggestions.append({'label': a, 'type': 'Artist'})
            for m in mediums:
                suggestions.append({'label': m, 'type': 'Medium'})
        return JsonResponse({'suggestions': suggestions[:7]})
 
    # ── PAGINATION ──
    paginator = Paginator(artproduct_list, 9)
    page_number = request.GET.get('page')
    try:
        artproducts = paginator.page(page_number)
    except PageNotAnInteger:
        artproducts = paginator.page(1)
    except EmptyPage:
        artproducts = paginator.page(paginator.num_pages)
 
    # ── ART TYPES for filter dropdown ──
    from artapp.models import Arttype   # adjust import to your app
    arttypes = Arttype.objects.all()
 
    context = {
        'artproducts': artproducts,
        'arttypes':    arttypes,
        'query':       query,
        'art_type':    art_type,
        'price_min':   price_min,
        'price_max':   price_max,
        'sort_by':     sort_by,
        'total_count': artproduct_list.count(),
    }
    return render(request, 'artproducts-list.html', context)

def LOGIN(request):
    return render(request,'login.html')

def doLogin(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
       

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            user_type = user.user_type
            if user_type == '1':
                return redirect('dashboard')
            elif user_type == '2':
                return redirect('dashboard')
        else:
            messages.error(request, 'Email or Password is not valid')
            return redirect('login')  # Redirect back to the login page with an error message
    else:
        # If the request method is not POST, redirect to the login page with an error message
        messages.error(request, 'Invalid request method')
        return redirect('login')

def doLogout(request):
    logout(request)
    request.session.flush()  # Clear the session including CSRF token
    return redirect('login')

from django.contrib.admin.views.decorators import staff_member_required

@login_required(login_url = '/')
def admin_orders(request):
    orders = Order.objects.all().order_by('-created_at')
    order_stats = {
        'Total Orders':   orders.count(),
        'Pending':        orders.filter(status='pending').count(),
        'Confirmed':      orders.filter(status='confirmed').count(),
        'Shipped':        orders.filter(status='shipped').count(),
        'Delivered':      orders.filter(status='delivered').count(),
        'Cancelled':      orders.filter(status='cancelled').count(),
    }
    return render(request, 'admin_orders.html', {
        'orders': orders,
        'order_stats': order_stats,
    })



@login_required(login_url = '/')
def admin_update_order_status(request, order_id):
    order = Order.objects.get(id=order_id)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        order.status = new_status
        order.save()
        messages.success(request, f'Order #{order.id} status updated to {new_status}.')
    return redirect('admin_orders')

@login_required(login_url = '/')
def DASHBOARD(request):
    artist_count = Artist.objects.all().count
    type_count = Arttype.objects.all().count
    med_count = Artmedium.objects.all().count
    artprod_count = Artproducts.objects.all().count
    unreadenq_count = Enquiry.objects.filter(status='').count()
    readenq_count = Enquiry.objects.filter(status='Answered').count()
    context = {'artist_count':artist_count,
    'type_count': type_count,
    'med_count':med_count,
    'artprod_count':artprod_count,
    'unreadenq_count':unreadenq_count,
    'readenq_count':readenq_count,
         
    }       
    return render(request,'dashboard.html',context)



@login_required(login_url = '/')
def ADMIN_PROFILE(request):
    user = CustomUser.objects.get(id = request.user.id)
    context = {
        "user":user,
    }
    return render(request,'profile.html',context)


@login_required(login_url = '/')
def ADMIN_PROFILE_UPDATE(request):
    if request.method == "POST":
        profile_pic = request.FILES.get('profile_pic')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        username = request.POST.get('username')
        print(profile_pic)
        

        try:
            customuser = CustomUser.objects.get(id = request.user.id)
            customuser.first_name = first_name
            customuser.last_name = last_name
            

            
            if profile_pic !=None and profile_pic != "":
               customuser.profile_pic = profile_pic
            customuser.save()
            messages.success(request,"Your profile has been updated successfully")
            return redirect('admin_profile')

        except:
            messages.error(request,"Your profile updation has been failed")
    return render(request, 'profile.html')


login_required(login_url='/')
def CHANGE_PASSWORD(request):
     context ={}
     ch = User.objects.filter(id = request.user.id)
     
     if len(ch)>0:
            data = User.objects.get(id = request.user.id)
            context["data"]= data            
     if request.method == "POST":        
        current = request.POST["cpwd"]
        new_pas = request.POST['npwd']
        user = User.objects.get(id = request.user.id)
        un = user.username
        check = user.check_password(current)
        if check == True:
          user.set_password(new_pas)
          user.save()
          messages.success(request,'Password Change  Succeesfully!!!')
          user = User.objects.get(username=un)
          login(request,user)
        else:
          messages.success(request,'Current Password wrong!!!')
          return redirect("change_password")
     return render(request,'change-password.html')


@login_required(login_url = '/')
def ADD_ARTIST(request):
    if request.method == "POST":
        try:
            artist_obj = Artist(
                name=request.POST['name'],
                mobnum=request.POST['mobnum'],
                email=request.POST['email'],
                edudetails=request.POST['edudetails'],
                awarddetails=request.POST['awarddetails'],
                
                images = request.FILES.get('images')
                
            )
            artist_obj.save()
            messages.success(request, "Artist details has been created successfully")
            return redirect('add_artist')
        except IntegrityError:
            messages.error(request, "Email and Mobilenumber must be unique")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
    
    return render(request,'add-artist.html')


@login_required(login_url='/')
def MANAGE_ARTIST(request):    
    artist_list = Artist.objects.all()
    paginator = Paginator(artist_list, 10)  # Show 10 categories per page

    page_number = request.GET.get('page')
    try:
        artists = paginator.page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        artists = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        artists = paginator.page(paginator.num_pages)

    context = {
    'artists':artists,}
    return render(request, 'manage-artist.html', context)

@login_required(login_url='/')
def DELETE_ARTIST(request,id):
    art = Artist.objects.get(id=id)
    art.delete()
    messages.success(request,'Record Delete Succeesfully!!!')
    
    return redirect('manage_artist')


@login_required(login_url='/')
def VIEW_ARTIST(request,id):    
    artist_data = Artist.objects.get(id =id)    
    context = {
        
        "artist_data":artist_data,
    }
    return render(request,'update_artist.html',context)

@login_required(login_url='/')
def EDIT_ARTIST(request):
    if request.method == "POST":
        artist_id = request.POST.get('artist_id')
        try:
            artist_edit = Artist.objects.get(id=artist_id)
        except Notes.DoesNotExist:
            messages.error(request, "Artist details does not exist")
            return redirect('manage_artist')

        # Create a dictionary with updated data
        updated_artist = {
            
            'name': request.POST['name'],
            'mobnum': request.POST['mobnum'],
            'email': request.POST['email'],
            'edudetails': request.POST['edudetails'],
            'awarddetails': request.POST['awarddetails'],
            'images': request.FILES.get('images')
        }

        # Update the artist_edit object with the updated artist
        for field, value in updated_artist.items():
            if value:
                setattr(artist_edit, field, value)

        
        artist_edit.save()
        messages.success(request, "Artist details has been updated successfully")
        return redirect('manage_artist')

    return render(request, 'manage-artist.html')

@login_required(login_url='/')
def ADD_ARTTYPE(request):
    if request.method == "POST":
        arttype_value = request.POST.get('arttype')
        if arttype_value:
            try:
                type_obj = Arttype(arttype=arttype_value)
                type_obj.save()
                messages.success(request, "Art type has been created successfully")
                return redirect('add_arttype')
            except IntegrityError:
                messages.error(request, "This art type already exists.")
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
        else:
            messages.error(request, "Please provide a valid art type.")
    
    return render(request, 'add-arttype.html')


@login_required(login_url='/')
def ADD_ARTMEDIUM(request):
    if request.method == "POST":
        artmedium_value = request.POST.get('artmedium')
        if artmedium_value:
            try:
                medium_obj = Artmedium(artmedium=artmedium_value)
                medium_obj.save()
                messages.success(request, "Art medium has been created successfully")
                return redirect('add_artmedium')
            except IntegrityError:
                messages.error(request, "This art medium already exists.")
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
        else:
            messages.error(request, "Please provide a valid art type.")
    
    return render(request, 'add-artmedium.html')


@login_required(login_url='/')
def MANAGE_ARTTYPE(request):    
    type_list = Arttype.objects.all()
    paginator = Paginator(type_list, 10)  # Show 10 categories per page

    page_number = request.GET.get('page')
    try:
        arttype = paginator.page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        arttype = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        arttype = paginator.page(paginator.num_pages)

    context = {
    'arttype':arttype,}
    return render(request, 'manage-arttype.html', context)

@login_required(login_url='/')
def DELETE_ARTTYPE(request,id):
    arttype = Arttype.objects.get(id=id)
    arttype.delete()
    messages.success(request,'Record Delete Succeesfully!!!')
    
    return redirect('manage_arttype')


@login_required(login_url='/')
def MANAGE_ARTMEDIUM(request):    
    medium_list = Artmedium.objects.all()
    paginator = Paginator(medium_list, 10)  # Show 10 categories per page

    page_number = request.GET.get('page')
    try:
        medium = paginator.page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        medium = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        medium = paginator.page(paginator.num_pages)

    context = {
    'medium':medium,}
    return render(request, 'manage-artmedium.html', context)

@login_required(login_url='/')
def DELETE_ARTMEDIUM(request,id):
    artmed = Artmedium.objects.get(id=id)
    artmed.delete()
    messages.success(request,'Record Delete Succeesfully!!!')
    
    return redirect('manage_artmedium')


@login_required(login_url='/')
def add_artproduct(request):
    if request.method == "POST":
        try:
            referencenumber = random.randint(100000000, 999999999)
            title = request.POST.get('title')
            images = request.FILES.get('images')
            image1 = request.FILES.get('image1')
            image2 = request.FILES.get('image2')
            image3 = request.FILES.get('image3')
            image4 = request.FILES.get('image4')
            dimension = request.POST.get('dimension')
            orientation = request.POST.get('orientation')
            size = request.POST.get('size')
            artist_id = request.POST.get('artist')
            arttype_id = request.POST.get('arttype')
            artmedium_id = request.POST.get('artmedium')
            sellingprice = request.POST.get('sellingprice')
            description = request.POST.get('description')

            artist = Artist.objects.get(id=artist_id) if artist_id else None
            arttype = Arttype.objects.get(id=arttype_id) if arttype_id else None
            artmedium = Artmedium.objects.get(id=artmedium_id) if artmedium_id else None

            artproduct = Artproducts(
                referencenumber=referencenumber,
                title=title,
                images=images,
                image1=image1,
                image2=image2,
                image3=image3,
                image4=image4,
                dimension=dimension,
                orientation=orientation,
                size=size,
                artist=artist,
                arttype=arttype,
                artmedium=artmedium,
                sellingprice=sellingprice,
                description=description,
            )
            artproduct.save()
            messages.success(request, "Art product has been created successfully")
            return redirect('add_artproduct')
        except IntegrityError:
            messages.error(request, "A product with this reference number already exists.")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

    artists = Artist.objects.all()
    arttypes = Arttype.objects.all()
    artmediums = Artmedium.objects.all()
    return render(request, 'add-artproduct.html', {
        'artists': artists,
        'arttypes': arttypes,
        'artmediums': artmediums,
    })


@login_required(login_url='/')
def MANAGE_ARTPRODUCTS(request):    
    product_list = Artproducts.objects.all()
    paginator = Paginator(product_list, 10)  # Show 10 categories per page

    page_number = request.GET.get('page')
    try:
       products = paginator.page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        products = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        products = paginator.page(paginator.num_pages)

    context = {
    'products':products,}
    return render(request, 'manage-artproducts.html', context)

@login_required(login_url='/')
def DELETE_ARTPRODUCT(request,id):
    artpro = Artproducts.objects.get(id=id)
    artpro.delete()
    messages.success(request,'Record Delete Succeesfully!!!')
    
    return redirect('manage_artproduct')

@login_required(login_url='/')
def VIEW_ARTPRODUCTS(request,id):    
    prod = Artproducts.objects.get(id =id)
    artists = Artist.objects.all()
    arttypes = Arttype.objects.all()
    artmediums = Artmedium.objects.all()    
    context = {
        
        "prod":prod,
        "artists":artists,
        "arttypes":arttypes,
        "artmediums":artmediums,
    }
    return render(request,'update_artproducts.html',context)

@login_required(login_url='/')
def VIEW_PRODUCTS(request, prod_id):    
    prod = get_object_or_404(Artproducts, id=prod_id)
    artists = Artist.objects.all()
    arttypes = Arttype.objects.all()
    artmediums = Artmedium.objects.all()    

    context = {
        "prod": prod,
        "artists": artists,
        "arttypes": arttypes,
        "artmediums": artmediums,
    }
    return render(request, 'update_artproducts.html', context)

@login_required(login_url='/')
def EDIT_ARTPRODUCTS(request):
    if request.method == "POST":
        pro_id = request.POST.get('pro_id')
        try:
            prod_edit = Artproducts.objects.get(id=pro_id)
        except Artproducts.DoesNotExist:
            messages.error(request, "Data does not exist")
            return redirect('manage_artproduct')

        # Create a dictionary with updated data
        updated_prod = {
            'title': request.POST.get('title'),
            'dimension': request.POST.get('dimension'),
            'orientation': request.POST.get('orientation'),
            'size': request.POST.get('size'),
            'sellingprice': request.POST.get('sellingprice'),
            'description': request.POST.get('description'),
        }

        # Update the prod_edit object with the updated data
        for field, value in updated_prod.items():
            if value:
                setattr(prod_edit, field, value)

        # Handle foreign key fields separately
        try:
            artist_id = request.POST.get('artist')
            if artist_id:
                prod_edit.artist = Artist.objects.get(id=artist_id)
            arttype_id = request.POST.get('arttype')
            if arttype_id:
                prod_edit.arttype = Arttype.objects.get(id=arttype_id)
            artmedium_id = request.POST.get('artmedium')
            if artmedium_id:
                prod_edit.artmedium = Artmedium.objects.get(id=artmedium_id)
        except (Artist.DoesNotExist, Arttype.DoesNotExist, Artmedium.DoesNotExist) as e:
            messages.error(request, f"Related entity error: {str(e)}")
            return redirect('manage_artproduct')

        # Handle file uploads separately
        image_fields = ['images', 'image1', 'image2', 'image3', 'image4']
        for image_field in image_fields:
            if image_field in request.FILES:
                setattr(prod_edit, image_field, request.FILES[image_field])

        prod_edit.save()
        messages.success(request, "Data has been updated successfully")
        return redirect('manage_artproduct')

    return render(request, 'manage-artproducts.html')


@login_required(login_url='/')
def WEBSITE_UPDATE(request):
    if request.method == "POST":
        try:
            web_id = request.POST.get('web_id')
            page = Page.objects.get(id=web_id)
            page.pagetitle = request.POST.get('pagetitle')
            page.address = request.POST.get('address')
            page.aboutus = request.POST.get('aboutus')
            page.mobilenumber = request.POST.get('mobilenumber')
            page.email = request.POST.get('email')
            page.save()
            messages.success(request, "Page has been updated successfully")
            return redirect('website_update')
        except Page.DoesNotExist:
            messages.error(request, "Page does not exist")
            return redirect('website_update')
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('website_update')
    
    pages = Page.objects.all()
    context = {
        "pages": pages,
    }
    return render(request, 'website.html', context)


@login_required(login_url='/')
def TOTALENQUIRY(request):    
    total_enq = Enquiry.objects.all()
    paginator = Paginator(total_enq, 10)  # Show 10 enquiries per page

    page_number = request.GET.get('page')
    try:
        tot_enq = paginator.page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        tot_enq = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        tot_enq = paginator.page(paginator.num_pages)

    context = {
        'tot_enq': tot_enq,
    }
    return render(request, 'total_enquiry.html', context)


@login_required(login_url='/')
def UNANSWERED_ENQUIRY(request):    
    unanswered_enq = Enquiry.objects.filter(status='')
    paginator = Paginator(unanswered_enq, 10)  # Show 10 enquiries per page

    page_number = request.GET.get('page')
    try:
        unanswered_enq = paginator.page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        unanswered_enq = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        unanswered_enq = paginator.page(paginator.num_pages)

    context = {
        'unanswered_enq': unanswered_enq,
    }
    return render(request, 'unanswered-enquiry.html', context)

@login_required(login_url='/')
def ANSWERED_ENQUIRY(request):    
    answered_enq = Enquiry.objects.filter(status='Answered')
    paginator = Paginator(answered_enq, 10)  # Show 10 enquiries per page

    page_number = request.GET.get('page')
    try:
        answered_enq = paginator.page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        answered_enq = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        answered_enq = paginator.page(paginator.num_pages)

    context = {
        'answered_enq': answered_enq,
    }
    return render(request, 'answered-enquiry.html', context)


@login_required(login_url='/')
def VIEW_ENQUIRY(request, id):    
    view_enq = get_object_or_404(Enquiry, id=id)

    context = {
        'view_enq': view_enq,
    }
    return render(request, 'view-enquiry-details.html', context)


#New added for mail

from threading import Thread
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect
from django.conf import settings

def send_email_background(subject, html_content, from_email, to_email):
    import logging
    logger = logging.getLogger(__name__)
    try:
        email = EmailMultiAlternatives(subject, "", from_email, [to_email])
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        logger.error(f"✅ EMAIL SENT TO: {to_email}")  # error level so it shows in Render
        print(f"✅ EMAIL SENT TO: {to_email}", flush=True)
    except Exception as e:
        logger.error(f"❌ EMAIL FAILED: {str(e)}")
        print(f"❌ EMAIL FAILED: {str(e)}", flush=True)

@login_required(login_url='/')
def UPDATE_ENQUIRY_REMARK(request):
    if request.method == "POST":
        enq_id = request.POST.get('enq_id')
        remark = request.POST.get('remark')

        enquiry = Enquiry.objects.get(id=enq_id)

        # ✅ Update DB first
        enquiry.remark = remark
        enquiry.status = "Answered"
        enquiry.save()

        # 📧 Build email content
        subject = "ArtNexus - Enquiry Response"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; background-color:#f4f4f4; padding:20px;">
          <div style="max-width:600px; margin:auto; background:white; padding:20px; border-radius:10px;">
            <h2 style="color:#333;">Hello {enquiry.fullname},</h2>
            <p>Thank you for contacting <b>ArtNexus</b></p>
            <hr>
            <h3 style="color:#444;">Your Enquiry:</h3>
            <p style="background:#f9f9f9; padding:10px; border-radius:5px;">
                {enquiry.message}
            </p>
            <h3 style="color:#444;">Our Response:</h3>
            <p style="background:#e8f5e9; padding:10px; border-radius:5px;">
                {remark}
            </p>
            <hr>
            <p>Regards,<br><b>ArtNexus Team</b></p>
          </div>
        </body>
        </html>
        """

        # ✅ Send email in background thread (won't block/timeout Gunicorn)
        t = Thread(
            target=send_email_background,
            args=(
                subject,
                html_content,
                f"ArtNexus <{settings.EMAIL_HOST_USER}>",
                enquiry.email
            )
        )
        t.daemon = True
        t.start()

        messages.success(request, "Reply sent + Email delivered")
        return redirect('answered_enquiry')
    
def SEARCH_ENQUIRY(request):
    if request.method == "GET":
        query = request.GET.get('query', '')
        if query:
            # Filter records where email or mobilenumber contains the query
            searchenq = Enquiry.objects.filter(enquirynumber__icontains=query) | Enquiry.objects.filter(mobnum__icontains=query) | Enquiry.objects.filter(fullname__icontains=query)
            messages.info(request, "Search against " + query)
            return render(request, 'search-enquiry.html', {'searchenq': searchenq, 'query': query})
        else:
            print("No Record Found")
            return render(request, 'search-enquiry.html', {})

# ✅ REGISTER VIEW
def REGISTER(request):
    if request.method == "POST":
        fullname = request.POST.get('fullname')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return redirect('register')

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return redirect('register')

        # ✅ User create karo
        user = CustomUser.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=fullname,
            user_type=2  # normal user
        )
        user.save()
        messages.success(request, "Registration successful! Please login.")
        return redirect('user_login')

    return render(request, 'register.html')


# ✅ USER LOGIN VIEW
def USER_LOGIN(request):
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, username=email, password=password)

        if user is not None:
            if user.user_type == '2':  # normal user only
                login(request, user)
                messages.success(request, "Login successful!")
                return redirect('index')
            else:
                messages.error(request, "Admin cannot login here!")
                return redirect('user_login')
        else:
            messages.error(request, "Invalid email or password!")
            return redirect('user_login')

    return render(request, 'user_login.html')


# ✅ USER LOGOUT VIEW
def USER_LOGOUT(request):
    logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect('index')

# ✅ Add to wishlist
@login_required
def add_to_wishlist(request, pid):
    product = Artproducts.objects.get(id=pid)

    Wishlist.objects.get_or_create(
        user=request.user,
        product=product
    )
    messages.success(request, f'"{product.title}" added to Wishlist!')
    return redirect(request.META.get('HTTP_REFERER'))


# ✅ Remove from wishlist
@login_required
def remove_from_wishlist(request, pid):
    product = Artproducts.objects.get(id=pid)

    Wishlist.objects.filter(
        user=request.user,
        product=product
    ).delete()

    return redirect('wishlist')


# ✅ Wishlist page
@login_required
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)

    return render(request, 'wishlist.html', {
        'wishlist_items': wishlist_items
    })

# ✅ Add to Cart
@login_required
def add_to_cart(request, pid):
    product = Artproducts.objects.get(id=pid)
    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        product=product
    )
    if not created:
        cart_item.quantity += 1
        cart_item.save()

    messages.success(request, f'"{product.title}" added to cart!')
    return redirect(request.META.get('HTTP_REFERER'))


# ✅ Remove from Cart
@login_required
def remove_from_cart(request, pid):
    product = Artproducts.objects.get(id=pid)
    Cart.objects.filter(user=request.user, product=product).delete()
    messages.success(request, 'Item removed from cart.')
    return redirect('cart')


# ✅ Update Cart Quantity
@login_required
def update_cart(request, pid):
    product = Artproducts.objects.get(id=pid)
    quantity = int(request.POST.get('quantity', 1))
    if quantity > 0:
        cart_item = Cart.objects.get(user=request.user, product=product)
        cart_item.quantity = quantity
        cart_item.save()
    else:
        Cart.objects.filter(user=request.user, product=product).delete()
    return redirect('cart')


# ✅ Cart Page
@login_required
def cart_view(request):
    cart_items = Cart.objects.filter(user=request.user).select_related('product')
    total = sum(item.total_price() for item in cart_items)
    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'total': total
    })

import razorpay
from django.conf import settings

@login_required
def checkout_view(request):
    cart_items = Cart.objects.filter(user=request.user).select_related('product')

    if not cart_items.exists():
        messages.error(request, 'Your cart is empty!')
        return redirect('cart')

    total = sum(item.total_price() for item in cart_items)

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        city = request.POST.get('city')
        state = request.POST.get('state')
        pincode = request.POST.get('pincode')

        # Create Order
        order = Order.objects.create(
            user=request.user,
            payment_method=payment_method,
            payment_status=True if payment_method == 'cod' else False,
            full_name=full_name,
            email=email,
            phone=phone,
            address=address,
            city=city,
            state=state,
            pincode=pincode,
        )

        # Create Order Items
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.sellingprice
            )

        if payment_method == 'cod':
            # Clear cart
            cart_items.delete()
            messages.success(request, 'Order placed successfully!')
            return redirect('order_confirmation', order_id=order.id)

        elif payment_method == 'razorpay':
            client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
            amount = int(total * 100)  # paise mein
            razorpay_order = client.order.create({
                'amount': amount,
                'currency': 'INR',
                'payment_capture': 1
            })
            order.razorpay_order_id = razorpay_order['id']
            order.save()

            return render(request, 'razorpay_payment.html', {
                'order': order,
                'razorpay_order_id': razorpay_order['id'],
                'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                'total': amount,
                'full_name': full_name,
                'email': email,
                'phone': phone,
            })

    return render(request, 'checkout.html', {
        'cart_items': cart_items,
        'total': total,
    })


# ✅ Razorpay Payment Verification
@login_required
def payment_success(request):
    if request.method == 'POST':
        payment_id = request.POST.get('razorpay_payment_id')
        order_id   = request.POST.get('razorpay_order_id')
        signature  = request.POST.get('razorpay_signature')

        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id':   order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature':  signature,
            })
            order = Order.objects.get(razorpay_order_id=order_id)
            order.razorpay_payment_id = payment_id
            order.payment_status = True
            order.status = 'confirmed'
            order.save()
            Cart.objects.filter(user=request.user).delete()
            messages.success(request, 'Payment successful! Order confirmed.')
            return redirect('order_confirmation', order_id=order.id)

        except razorpay.errors.SignatureVerificationError:
            messages.error(request, 'Payment verification failed. Contact support.')
            return redirect('cart')


# ✅ Order Confirmation
@login_required
def order_confirmation(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)
    return render(request, 'order_confirmation.html', {'order': order})

@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'my_orders.html', {'orders': orders})