from django.contrib.contenttypes import generic
from django.utils.translation import ugettext_lazy as _

from ... import settings
from ...models import Variation
from ...utils import get_object


def _admin_action_factory(specpath):
    spec_class = get_object(specpath)

    def admin_action(modeladmin, request, queryset):
        for mf in queryset:
            spec = spec_class(variation=mf, original=mf.file)
            mf.file = spec.process()
            mf.save()

    admin_action.short_description = _('Apply variation "%s" on this mediafile' % spec_class.get_shortname())

    return admin_action


def variations(cls, admin_cls):
    """
    extension for FeinCMS MediaFile, which adds the generic backrelation and the admin actions
    """

    cls.add_to_class('variations', generic.GenericRelation(Variation))

    class VariationInline(generic.GenericTabularInline):
        model = Variation
        extra = 0
        readonly_fields = ('spec', 'options', 'field', 'progress', 'processed', 'created', 'modified')
    admin_cls.inlines.append(VariationInline)

    for specpath in settings.FEINCMS_ADMINACTION_APPLY_SPECS:
        admin_cls.actions.append(_admin_action_factory(specpath))