from .models import Arttype,Enquiry
from django.conf import settings
import os

def arttypes_processor(request):
    arttypes = Arttype.objects.all()
    return {'arttypes': arttypes}


def enquiry_processor(request):
    enq_details = Enquiry.objects.filter(status='')
    enq_status = Enquiry.objects.filter(status='').count()
    return {'enq_status': enq_status,
    'enq_details':enq_details,}

def google_analytics(request):
    return {
        'GA_TRACKING_ID': settings.GOOGLE_ANALYTICS_ID
    }