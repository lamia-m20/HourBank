from django.conf import settings


def site_contact(request):
    return {'default_from_email': settings.DEFAULT_FROM_EMAIL}
