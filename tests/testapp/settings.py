import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'data.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

SITE_ID = 1

APP_BASEDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# use 12 factor app config in the enviroment: http://www.12factor.net/config
if all((var in os.environ for var in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_STORAGE_BUCKET_NAME'))):
    DEFAULT_FILE_STORAGE = 'testapp.s3.utils.MediaRootS3BotoStorage'
    STATICFILES_STORAGE = 'testapp.s3.utils.StaticRootS3BotoStorage'
    AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
    AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
    AWS_STORAGE_BUCKET_NAME = os.environ['AWS_STORAGE_BUCKET_NAME']
    AWS_PRELOAD_METADATA = True
    AWS_S3_SECURE_URLS = False
    AWS_QUERYSTRING_AUTH = False
    AWS_HEADERS = { 'Cache-Control': 'max-age=2592000' }

MEDIA_ROOT = os.path.join(APP_BASEDIR, 'upload')
MEDIA_URL = os.environ.get('MEDIA_URL', '/upload/')

STATIC_ROOT = os.path.join(APP_BASEDIR, 'static')
STATIC_URL = os.environ.get('STATIC_URL', '/static/')

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

SECRET_KEY = '6+up74k924#oo@lror$ch8%l))q2d4(&amp;nn^z@mzi1kf7$y5$6x'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'testapp.urls'

WSGI_APPLICATION = 'testapp.wsgi.application'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'mediavariations',
    'feincms',
    'feincms.module.medialibrary',
    'testapp',
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

BLITLINE_APPLICATION_ID = os.environ.get('BLITLINE_APPLICATION_ID', None)

MEDIAVARIATIONS_SPECS =  {
    'blitline' : 'mediavariations.contrib.blitline.specs.Generic',
    'pdf2jpg' : 'mediavariations.contrib.blitline.specs.Pdf2Jpeg',
}

MEDIAVARIATIONS_FEINCMS_ADMINACTION_APPLY_SPECS = (
    'mediavariations.contrib.pypdf.specs.PageRange',
)
