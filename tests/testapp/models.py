from feincms.module.medialibrary.models import MediaFile
from mediavariations.contrib.feincms.extensions import variations


MediaFile.register_extension(variations)