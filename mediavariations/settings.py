from django.conf import settings as django_settings


SPECS = getattr(django_settings, 'MEDIAVARIATIONS_SPECS', {})