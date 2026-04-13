from .models import Arttype,Enquiry

def arttypes_processor(request):
    arttypes = Arttype.objects.all()
    return {'arttypes': arttypes}


def enquiry_processor(request):
    enq_details = Enquiry.objects.filter(status='')
    enq_status = Enquiry.objects.filter(status='').count()
    return {'enq_status': enq_status,
    'enq_details':enq_details,}