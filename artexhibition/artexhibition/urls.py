"""
URL configuration for artexhibition project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('base/', views.BASE, name='base'),
    path('base1/', views.BASE1, name='base1'),
    path('Dashboard', views.DASHBOARD, name='dashboard'),
    path('', views.Index, name='index'),
    # path('fix-admin/', views.fix_admin),
    path('Aboutus', views.ABOUTUS, name='aboutus'),
    path('Contactus', views.CONTACTUS, name='contactus'),
    path('Artproductlist', views.ARTPRODUCTLIST, name='art_product_list'),
    path('Login', views.LOGIN, name='login'),
    path('doLogout', views.doLogout, name='logout'),
    path('doLogin', views.doLogin, name='doLogin'),
    path('AdminProfile', views.ADMIN_PROFILE, name='admin_profile'),
    path('AdminProfile/update', views.ADMIN_PROFILE_UPDATE, name='admin_profile_update'),
    path('Password', views.CHANGE_PASSWORD, name='change_password'),
    path('AddArtist', views.ADD_ARTIST, name='add_artist'),
    path('ManageArtist', views.MANAGE_ARTIST, name='manage_artist'),
    path('DeleteArtist/<str:id>', views.DELETE_ARTIST, name='delete_artist'),
    path('ViewArtist/<str:id>', views.VIEW_ARTIST, name='view_artist'),
    path('EditArtist', views.EDIT_ARTIST, name='edit_artist'),
    path('AddArttype', views.ADD_ARTTYPE, name='add_arttype'),
    path('AddArtmedium', views.ADD_ARTMEDIUM, name='add_artmedium'),
    path('ManageArttype', views.MANAGE_ARTTYPE, name='manage_arttype'),
    path('DeleteArttype/<str:id>', views.DELETE_ARTTYPE, name='delete_arttype'),
    path('ManageArtmedium', views.MANAGE_ARTMEDIUM, name='manage_artmedium'),
    path('DeleteArtmedium/<str:id>', views.DELETE_ARTMEDIUM, name='delete_artmedium'),
    path('AddAddartproduct', views.add_artproduct, name='add_artproduct'),
    path('ManageArtproduct', views.MANAGE_ARTPRODUCTS, name='manage_artproduct'),
    path('DeleteArtProduct/<str:id>', views.DELETE_ARTPRODUCT, name='delete_artproduct'),
    path('ViewArtProduct/<str:id>', views.VIEW_ARTPRODUCTS, name='view_artproduct'),
    path('ViewProduct/<int:prod_id>/', views.VIEW_PRODUCTS, name='view_product'),
    path('EditArtProduct', views.EDIT_ARTPRODUCTS, name='edit_artproduct'),
    path('ViewSingleProduct/<str:id>', views.VIEW_SINGLEPRODUCTS, name='view_singleproduct'),
    path('Enquiry/<str:id>', views.ENQUIRY, name='enquiry'),
    path('EnquiryDetails', views.ENQUIRY_DETAILS, name='enquiry_details'),
    path('thank_you/<int:enquirynumber>/', views.THANKYOU, name='thank_you'),
    path('arttype/<int:id>/', views.arttype_detail, name='arttype_detail'),
    path('TotalEnquiry', views.TOTALENQUIRY, name='totalenquiry'),
    path('AnsweredEnquiry', views.ANSWERED_ENQUIRY, name='answered_enquiry'),
    path('UnansweredEnquiry', views.UNANSWERED_ENQUIRY, name='unanswered_enquiry'),
    path('ViewEnquiry/<str:id>', views.VIEW_ENQUIRY, name='view-enquiry'),
    path('UpdateEnquiryRemark', views.UPDATE_ENQUIRY_REMARK, name='update-enquiry-remark'),
    path('SearchEnquiry', views.SEARCH_ENQUIRY, name='search_enquiry'),
    #Website Page
    path('Website/update', views.WEBSITE_UPDATE, name='website_update'),
    path('chatbot/', views.chatbot, name='chatbot'),
    path('chat/', views.chat_page, name='chat'),
    #User login
    path('register/', views.REGISTER, name='register'),
    path('user-login/', views.USER_LOGIN, name='user_login'),
    path('user-logout/', views.USER_LOGOUT, name='user_logout'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('add-to-wishlist/<int:pid>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('remove-from-wishlist/<int:pid>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    
]+static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
