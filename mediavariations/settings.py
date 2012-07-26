from django.conf import settings as django_settings


# a dictionary with shortnames for specs
SPECS = getattr(django_settings, 'MEDIAVARIATIONS_SPECS', {})

# a list of specs, which will be available as admin action to direct apply to a feincms
# mediafile. direct apply means, that the targeted mediafile will be changed instead of
# a mediavariation is created
FEINCMS_ADMINACTION_APPLY_SPECS = getattr(django_settings, 'MEDIAVARIATIONS_FEINCMS_ADMINACTION_APPLY_SPECS', ())