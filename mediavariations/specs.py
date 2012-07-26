import os

from django.utils import simplejson
from django.core.files.storage import get_storage_class


class Base(object):
    defaults = {}

    def __init__(self, **kwargs):
        # write down all init args to object attrs -> s = Spec(a=2); s.a -> 2
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

        if hasattr(self, 'variation'):
            if not hasattr(self, 'original'):
                self.original = getattr(self.variation.content_object, self.variation.field)
            self.path = getattr(self, 'path', os.path.split(self.original.name)[0])
            self.filename = getattr(self, 'filename', os.path.split(self.original.name)[1])
            self.basename = getattr(self, 'basename', os.path.splitext(self.filename)[0])
            self.ext = getattr(self, 'ext', os.path.splitext(self.filename)[1])
            self.variation_filename = getattr(self, 'variation_filename',
                self.get_variation_filename())
            self.variation_directory = getattr(self, 'variation_directory',
                self.variation.file.field.get_directory_name())
            self.variation_path = getattr(self, 'variation_path',
                os.path.join(self.variation_directory, self.variation_filename))
            self.storage = getattr(self, 'starage', get_storage_class()())

    @classmethod
    def get_shortname(self):
        return self.__name__.lower()

    def get_variation_filename(self):
        return '%s_%s_%s%s' % (self.basename, self.get_shortname(), self.get_options_hash(), self.ext)

    def get_options(self):
        try:
            self.options = self.defaults.copy()
            self.options.update(simplejson.loads(self.variation.options))
            return self.options
        except AttributeError:
            return self.defaults

    def get_options_hash(self):
        return hash(simplejson.dumps(self.get_options()))

    def get_progress(self):
        """
        override this function if you can return a progress
        """
        return 0.0
