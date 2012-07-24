from django import template
from django.contrib.contenttypes.models import ContentType
from django.utils import simplejson

from .. import settings
from ..models import Variation

register = template.Library()


@register.filter
def mediavariation(object, spec, field=None, **kwargs):
    variation, created = Variation.objects.get_or_create(
        content_type = ContentType.objects.get_for_model(object),
        object_id = object.pk,
        spec = settings.SPECS[spec],
        options = simplejson.dumps(kwargs)
    )

    return unicode(variation.file.url)

