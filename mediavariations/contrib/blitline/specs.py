import os
import urllib

from django.conf import settings
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

        # extend the options
        options['functions'][0]['save'] = {
            'image_identifier' : self.variation_filename,
            's3_destination' : {
                'bucket' : settings.AWS_STORAGE_BUCKET_NAME,
                'key' : os.path.join(self.storage.location, self.variation_path)
            }
        }

        # extend the options with blitline auth infos and source url
        options.update({
            'application_id' : settings.BLITLINE_APPLICATION_ID,
            'src' : self.original.url,
        })

        job_json = simplejson.dumps(options)

        params = urllib.urlencode({'json' : job_json})
        raw = urllib.urlopen('http://api.blitline.com/job', params).read()

        parsed = simplejson.loads(raw)

        # if the result is not as expected, this fails.
        self.blitline_job_response = parsed
        self.blitlite_job_id = parsed['results']['job_id']
        return os.path.join(self.variation_directory, parsed['results']['images'][0]['image_identifier'])

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
    pdf2jpeg conversion is simply a noop on blitline and forces .jpg extension
    """
    ext = '.jpg'
