from datetime import datetime

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
    options = models.TextField(default="{}")

    file = models.FileField(blank=True, upload_to="mediavariations/%Y/%m/")

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    field = models.CharField(max_length=50)

    progress = models.FloatField(null=True) # progress with null -> not started yet
    processed = models.DateTimeField(null=True)

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

    def delete(self, *args, **kwargs):
        """
        ensure, that the files are also deleted
        """

        self.file.delete(save=False)

        super(Variation, self).delete(*args, **kwargs)

    def process(self):
        spec_class = get_object(self.spec)
        self.spec_instance = spec_class(variation=self)
        self.file = self.spec_instance.process()

        self.progress = 0.0 # this indicates, that processing is started
        self.save(process=False)

    def get_progress(self):
        self.progress = self.spec_instance.get_progress()

        if self.progress >= 1.0:
            self.processed = datetime.now()

        self.save(process=False)
        return self.progress
