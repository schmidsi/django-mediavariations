from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.db import models

from .utils import get_object


class Variation(models.Model):
    """
    The Mediavariation model holds the reference to the variation and also
    to the original FileField.
    """

    spec = models.CharField(max_length=100)
    options = models.TextField(blank=True)

    file = models.FileField(blank=True, upload_to="mediavariations/%Y/%m/")

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    field = models.CharField(max_length=50)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)


    def save(self, process=True, *args, **kwargs):
        """
        simply try to guess the mediafile field: fieldname of hte first
        instance of models.FileField.
        """

        if not self.field:
            for field in self.content_object._meta.fields:
                if isinstance(field, models.FileField):
                    self.field = field.attname
                    break

        super(Variation, self).save(*args, **kwargs)

        if process:
            self.process()



    def process(self):
        spec = get_object(self.spec)()
        url_or_file = spec.process(self)

        if isinstance(url_or_file, str):
            self.file.path = url_or_file
        else:
            self.file = url_or_file

        self.save(process=False)

