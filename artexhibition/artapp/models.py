from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class CustomUser(AbstractUser):
    USER ={
        (1,'admin'),
        
        
    }
    user_type = models.CharField(choices=USER,max_length=50,default=1)

    profile_pic = models.ImageField(upload_to='media/profile_pic')

class Artist(models.Model):
    name = models.CharField(max_length=250)
    phone_regex = RegexValidator(regex=r'^\d{10,11}$', message="Phone number must be entered in the format: '9999999999'. Up to 11 digits allowed.")
    mobnum = models.CharField(validators=[phone_regex], max_length=11, verbose_name='Mobile Number', help_text='Enter a valid mobile number', unique=True)
    email = models.EmailField(unique=True)
    edudetails = models.TextField()
    awarddetails = models.TextField()
    images = models.ImageField(upload_to='media/artistprofile_pic')
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
    images = models.ImageField(upload_to='artpics/images')
    image1 = models.ImageField(upload_to='artpics/images')
    image2 = models.ImageField(upload_to='artpics/images')
    image3 = models.ImageField(upload_to='artpics/images')
    image4 = models.ImageField(upload_to='artpics/images')
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