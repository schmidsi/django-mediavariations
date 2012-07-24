import os

from time import sleep

from django.core.files import File
from django.core.files.images import get_image_dimensions
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from feincms.module.medialibrary.models import MediaFile

from mediavariations.models import Variation


class BindingTest(TestCase):
    def setUp(self):
        self.mediafile = MediaFile(file=File(open('mediavariations/fixtures/elephant_test_image.jpg')))
        self.mediafile.save()

    def tearDown(self):
        """
        delete the mediafile
        """

        mediafile_variations = Variation.objects.filter(
            content_type = ContentType.objects.get_for_model(self.mediafile),
            object_id = self.mediafile.pk
        )

        for variation in mediafile_variations:
            variation.delete()

        self.mediafile.delete()

    def test_setup(self):
        self.assertEqual(self.mediafile.type, 'image')
        self.assertEqual(get_image_dimensions(self.mediafile.file), (404, 346))

    def test_blitline(self):
        self.variation = Variation(
            content_object=self.mediafile,
            spec = 'mediavariations.contrib.blitline.specs.Generic',
            options = '''
                {"functions":
                    [{ "name": "crop",
                       "params" : { "x": 5, "y": 5, "width": 40,"height": 40 }
                    }]
                }
            '''
        )
        self.variation.save()

        # auto medialfield discovery
        self.assertEqual(self.variation.field, 'file')

        # wait for image to be processed
        while (not self.variation.processed):
            self.variation.get_progress()
            sleep(1)

        # test image
        self.assertEqual(get_image_dimensions(self.variation.file), (40, 40))

    def test_templatetag(self):
        from mediavariations.templatetags.mediavariations import mediavariation

        self.variated_url = mediavariation(self.mediafile, 'blitline')

        path, filename = os.path.split(self.mediafile.file.name)
        basename, ext = os.path.splitext(filename)
        
        self.assertTrue(basename in self.variated_url)

