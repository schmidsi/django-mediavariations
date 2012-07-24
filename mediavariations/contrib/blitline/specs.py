import os
import urllib

from django.conf import settings
from django.core.files.storage import get_storage_class
from django.utils import simplejson

from ...specs import Base


class Generic(Base):
    defaults = {
        'functions' : [
            {'name' : 'no_op',
             'params' : {}},
        ],
    }

    def process(self):
        options = self.get_options()
        original = getattr(self.variation.content_object, self.variation.field)
        path, filename = os.path.split(original.name)
        basename, ext = os.path.splitext(filename)
        variation_name = '%s_%s_%s%s' % (basename, self.get_shortname(), self.get_options_hash(), ext) #
        variation_directory = self.variation.file.field.get_directory_name()
        variation_path = os.path.join(variation_directory, variation_name)
        storage = get_storage_class()()

        # extend the options
        options['functions'][0]['save'] = {
            'image_identifier' : variation_name,
            's3_destination' : {
                'bucket' : settings.AWS_STORAGE_BUCKET_NAME,
                'key' : os.path.join(storage.location, variation_path)
            }
        }

        # extend the options with blitline auth infos and source url
        options.update({
            'application_id' : settings.BLITLINE_APPLICATION_ID,
            'src' : original.url,
        })

        job_json = simplejson.dumps(options)

        params = urllib.urlencode({'json' : job_json})
        raw = urllib.urlopen('http://api.blitline.com/job', params).read()

        parsed = simplejson.loads(raw)

        # if the result is not as expected, this fails.
        self.blitline_job_response = parsed
        self.blitlite_job_id = parsed['results']['job_id']
        return os.path.join(variation_directory, parsed['results']['images'][0]['image_identifier'])

    def get_progress(self):
        raw = urllib.urlopen('http://api.blitline.com/poll?job_id=%s' % self.blitlite_job_id).read()
        parsed = simplejson.loads(raw)

        if parsed.get('is_complete', False):
            return 1.0
        else:
            # 0.1 indicates, that the processing is started
            return 0.0


class Pdf2Jpeg(Generic):
    """
    pdf2jpeg conversion is simply a noop on blitline
    """
    pass