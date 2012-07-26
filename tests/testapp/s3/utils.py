#from storages.backends.s3boto import S3BotoStorage
from .storage import S3BotoStorage

StaticRootS3BotoStorage = lambda: S3BotoStorage(location='static', reduced_redundancy=True)
MediaRootS3BotoStorage  = lambda: S3BotoStorage(location='upload')