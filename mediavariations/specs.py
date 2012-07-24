from django.utils import simplejson

class Base(object):
    defaults = {}

    def __init__(self, **kwargs):
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    @classmethod
    def get_shortname(self):
        return self.__name__.lower()

    def get_options(self):
        try:
            self.options = self.defaults.copy()
            self.options.update(simplejson.loads(self.variation.options))
            return self.options
        except AttributeError:
            raise NotImplementedError(
                'A mediavariation spec currently needs a variation object associated with an'
                'options attribute')

    def get_options_hash(self):
        return hash(simplejson.dumps(self.get_options()))

    def get_progress(self):
        """
        override this function if you can return a progress
        """
        return 0.0
