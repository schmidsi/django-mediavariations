from django.core.files import File
from django.core.files.images import get_image_dimensions
from django.test import TestCase

from feincms.module.medialibrary.models import MediaFile

from mediavariations.models import Variation


class BindingTest(TestCase):
    def setUp(self):
        self.mediafile = MediaFile(file=File(open('mediavariations/fixtures/elephant_test_image.jpg')))
        self.mediafile.save()

    def test_setup(self):
        self.assertEqual(self.mediafile.type, 'image')
        self.assertEqual(get_image_dimensions(self.mediafile.file), (404, 346))

    def test_blitline(self):
        self.variation = Variation(
            content_object=self.mediafile,
            spec = 'mediavariations.contrib.blitline.specs.Generic',
            options = '''
                [{ "name": "crop",
                   "params" : { "x": 5, "y": 5, "width": 40,"height": 40 }
                }]
            '''
        )
        self.variation.save()

        # auto medialfield discovery
        self.assertEqual(self.variation.field, 'file')

        # test image
        self.assertEqual(get_image_dimensions(self.variation.file), (40, 40))
