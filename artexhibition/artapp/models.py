from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings
from cloudinary.models import CloudinaryField

class CustomUser(AbstractUser):
    USER ={
        (1,'admin'),   
        (2, 'user'),
    }
    user_type = models.CharField(choices=USER,max_length=50,default=1)

    # profile_pic = models.ImageField(upload_to='media/profile_pic')
    images = CloudinaryField('image', folder='media/profile_pis')

class Artist(models.Model):
    name = models.CharField(max_length=250)
    phone_regex = RegexValidator(regex=r'^\d{10,11}$', message="Phone number must be entered in the format: '9999999999'. Up to 11 digits allowed.")
    mobnum = models.CharField(validators=[phone_regex], max_length=11, verbose_name='Mobile Number', help_text='Enter a valid mobile number', unique=True)
    email = models.EmailField(unique=True)
    edudetails = models.TextField()
    awarddetails = models.TextField()
    # images = models.ImageField(upload_to='media/artistprofile_pic')
    images = CloudinaryField('image', folder='media/artistprofile_pic')
    creationdate = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Arttype(models.Model):
    arttype = models.CharField(max_length=250)
    creationdate = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Artmedium(models.Model):
    artmedium = models.CharField(max_length=250)
    creationdate = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Artproducts(models.Model):
    referencenumber = models.IntegerField(default=0, unique=True)  # Ensure unique reference number
    title = models.CharField(max_length=250)
    images = CloudinaryField('image', folder='artnexus/images')
    image1 = CloudinaryField('image', folder='artnexus/images')
    image2 = CloudinaryField('image', folder='artnexus/images')
    image3 = CloudinaryField('image', folder='artnexus/images')
    image4 = CloudinaryField('image', folder='artnexus/images')
    dimension = models.CharField(max_length=250)
    orientation = models.CharField(max_length=250)
    size = models.CharField(max_length=250)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, null=True, blank=True, related_name='artproducts')
    arttype = models.ForeignKey(Arttype, on_delete=models.CASCADE, null=True, blank=True, related_name='artproducts')
    artmedium = models.ForeignKey(Artmedium, on_delete=models.CASCADE, null=True, blank=True, related_name='artproducts')
    sellingprice = models.DecimalField(max_digits=10, decimal_places=2)  # Use DecimalField for prices
    description = models.TextField()
    creationdate = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Page(models.Model):
    pagetitle = models.CharField(max_length=250)
    address = models.CharField(max_length=250)
    aboutus = models.TextField()
    email = models.EmailField(max_length=200)
    mobilenumber = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Enquiry(models.Model):
    enquirynumber = models.IntegerField(default=0, unique=True)  # Ensure unique enquiry number
    prod_id = models.ForeignKey(Artproducts, on_delete=models.CASCADE, null=True, blank=True, related_name='artproducts')
    fullname = models.CharField(max_length=250,blank=True)
    email = models.EmailField(max_length=200,blank=True)
    mobnum = models.CharField(max_length=15,blank=True)  # CharField for mobile numbers
    message = models.TextField(blank=True)
    enquiry_date = models.DateTimeField(default=timezone.now)  # Set default for existing rows
    status = models.CharField(max_length=250,blank=True)
    remark = models.CharField(max_length=250, blank=True)
    remark_date = models.DateTimeField(auto_now=True)

class Wishlist(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='wishlist')
    product = models.ForeignKey(Artproducts, on_delete=models.CASCADE, related_name='wishlist')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    product = models.ForeignKey(Artproducts, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

    def total_price(self):
        return self.quantity * self.product.sellingprice

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    PAYMENT_CHOICES = [
        ('razorpay', 'Razorpay'),
        ('cod', 'Cash on Delivery'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES)
    payment_status = models.BooleanField(default=False)
    razorpay_order_id = models.CharField(max_length=200, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=200, blank=True, null=True)
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)

    def total_amount(self):
        return sum(item.total_price() for item in self.order_items.all())

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    product = models.ForeignKey(Artproducts, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def total_price(self):
        return self.quantity * self.price