import os
import urllib

from django.conf import settings
from django.core.files.storage import get_storage_class
from django.utils import simplejson


class Generic(object):
    def get_shortname(self):
        return 'generic'

    def process(self, variation):
        options = simplejson.loads(variation.options)
        original = getattr(variation.content_object, variation.field)
        path, filename = os.path.split(original.name)
        basename, ext = os.path.splitext(filename)
        newname = '%s_%s_%s%s' % (basename, self.get_shortname(), variation.id, ext)
        storage = get_storage_class()()

        options[0]['save'] = {
            'image_identifier' : newname,
            's3_destination' : {
                'bucket' : settings.AWS_STORAGE_BUCKET_NAME,
                'key' : os.path.join(storage.location, variation.file.field.get_directory_name(), newname)
            }
        }

        job = {
            'application_id' : settings.BLITLINE_APPLICATION_ID,
            'src' : original.url,
            'functions' : options,
        }

        job_json = simplejson.dumps(job)
        params = urllib.urlencode({'json' : job_json})
        raw = urllib.urlopen('http://api.blitline.com/job', params).read()

        parsed = simplejson.loads(raw)

        print parsed

        return parsed['results']['images'][0]['s3_url']