"""
S3 Storage Backend for Django websites.
Uses the boto AWS API library.

Based on the backend from django-storages.

This storage class makes the following assumptions:
 * Files are saved to the S3 server, by the django site or other processes
 * Files are never deleted
 * Existing files are never modified while the app server is running

This will still work with static files that get modified by collectstatic,
as long as you restart your app server after running collectstatic.

--------------------------------------------------------------------------------

Copyright (c) 2008-2012 Morningstar Enterprises Inc., Alan Justino da Silva,
 and authors listed in the django-storages AUTHORS file and the django-storages
public CMS repository. All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice, 
       this list of conditions and the following disclaimer.
    
    2. Redistributions in binary form must reproduce the above copyright 
       notice, this list of conditions and the following disclaimer in the
       documentation and/or other materials provided with the distribution.

    3. Neither the name of Django-OAuth nor the names of its contributors may 
       be used to endorse or promote products derived from this software 
       without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
import os
import re
import time
import mimetypes
import calendar
from collections import namedtuple
from datetime import datetime
from dateutil import tz, parser as dateparser

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO  # noqa

from django.conf import settings
from django.core.files.base import File
from django.core.files.storage import Storage
from django.core.exceptions import ImproperlyConfigured, SuspiciousOperation
from django.utils.encoding import force_unicode, smart_str

try:
    from boto.s3.connection import S3Connection, SubdomainCallingFormat
    from boto.exception import S3ResponseError
    from boto.s3.key import Key
    from boto.utils import parse_ts
except ImportError:
    raise ImproperlyConfigured("Could not load Boto's S3 bindings.\n"
                               "See http://code.google.com/p/boto/")

ACCESS_KEY_NAME = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
SECRET_KEY_NAME = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
HEADERS = getattr(settings, 'AWS_HEADERS', {})
STORAGE_BUCKET_NAME = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
AUTO_CREATE_BUCKET = getattr(settings, 'AWS_AUTO_CREATE_BUCKET', False)
DEFAULT_ACL = getattr(settings, 'AWS_DEFAULT_ACL', 'public-read')
BUCKET_ACL = getattr(settings, 'AWS_BUCKET_ACL', DEFAULT_ACL)
QUERYSTRING_AUTH = getattr(settings, 'AWS_QUERYSTRING_AUTH', True)
QUERYSTRING_EXPIRE = getattr(settings, 'AWS_QUERYSTRING_EXPIRE', 3600)
REDUCED_REDUNDANCY = getattr(settings, 'AWS_REDUCED_REDUNDANCY', False)
LOCATION = getattr(settings, 'AWS_LOCATION', '')
CUSTOM_DOMAIN = getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', None)
CALLING_FORMAT = getattr(settings, 'AWS_S3_CALLING_FORMAT',
                         SubdomainCallingFormat())
SECURE_URLS = getattr(settings, 'AWS_S3_SECURE_URLS', True)
FILE_NAME_CHARSET = getattr(settings, 'AWS_S3_FILE_NAME_CHARSET', 'utf-8')
FILE_OVERWRITE = getattr(settings, 'AWS_S3_FILE_OVERWRITE', True)
FILE_BUFFER_SIZE = getattr(settings, 'AWS_S3_FILE_BUFFER_SIZE', 5242880)
IS_GZIPPED = getattr(settings, 'AWS_IS_GZIPPED', False)
PRELOAD_METADATA = getattr(settings, 'AWS_PRELOAD_METADATA', False)
GZIP_CONTENT_TYPES = getattr(settings, 'GZIP_CONTENT_TYPES', (
    'text/css',
    'application/javascript',
    'application/x-javascript',
))

if IS_GZIPPED:
    from gzip import GzipFile

def safe_join(base, *paths):
    """
    A version of django.utils._os.safe_join for S3 paths.

    Joins one or more path components to the base path component
    intelligently. Returns a normalized version of the final path.

    The final path must be located inside of the base path component
    (otherwise a ValueError is raised).

    Paths outside the base path indicate a possible security
    sensitive operation.
    """
    from urlparse import urljoin
    base_path = force_unicode(base)
    base_path = base_path.rstrip('/')
    paths = [force_unicode(p) for p in paths]

    final_path = base_path
    for path in paths:
        final_path = urljoin(final_path.rstrip('/') + "/", path.rstrip("/"))

    # Ensure final_path starts with base_path and that the next character after
    # the final path is '/' (or nothing, in which case final_path must be
    # equal to base_path).
    base_path_len = len(base_path)
    if not final_path.startswith(base_path) \
       or final_path[base_path_len:base_path_len + 1] not in ('', '/'):
        raise ValueError('the joined path is located outside of the base path'
                         ' component')

    return final_path.lstrip('/')

CachedKey = namedtuple('CachedKey', 'size last_modified') # storing actual Key objects uses way too much memory

cached_entries = {} # dict where key is bucket name, value is a dict of
                    # CachedKey objects. This is to reduce memory usage and
                    # increase speed when multiple S3BotoStorage objects exist
                    # for the same bucket (allows use of prefixes, differing
                    # redundancy settings, etc. )

class S3BotoStorage(Storage):
    """
    Amazon Simple Storage Service using Boto
    
    This storage backend supports opening files in read or write
    mode and supports streaming(buffering) data in chunks to S3
    when writing.
    """

    def __init__(self, bucket=STORAGE_BUCKET_NAME, access_key=None,
            secret_key=None, bucket_acl=BUCKET_ACL, acl=DEFAULT_ACL,
            headers=HEADERS, gzip=IS_GZIPPED,
            gzip_content_types=GZIP_CONTENT_TYPES,
            querystring_auth=QUERYSTRING_AUTH,
            querystring_expire=QUERYSTRING_EXPIRE,
            reduced_redundancy=REDUCED_REDUNDANCY,
            custom_domain=CUSTOM_DOMAIN,
            secure_urls=SECURE_URLS,
            location=LOCATION,
            file_name_charset=FILE_NAME_CHARSET,
            preload_metadata=PRELOAD_METADATA,
            calling_format=CALLING_FORMAT):
        self.bucket_acl = bucket_acl
        self.bucket_name = bucket
        self.acl = acl
        self.headers = headers
        self.preload_metadata = preload_metadata
        self.gzip = gzip
        self.gzip_content_types = gzip_content_types
        self.querystring_auth = querystring_auth
        self.querystring_expire = querystring_expire
        self.reduced_redundancy = reduced_redundancy
        self.custom_domain = custom_domain
        self.secure_urls = secure_urls
        self.location = location or ''
        self.location = self.location.lstrip('/')
        self.file_name_charset = file_name_charset

        if not access_key and not secret_key:
            access_key, secret_key = self._get_access_keys()

        self.connection = S3Connection(access_key, secret_key,
            calling_format=calling_format)
        self._entries = None

    @property
    def bucket(self):
        """
        Get the current bucket. If there is no current bucket object
        create it.
        """
        if not hasattr(self, '_bucket'):
            self._bucket = self._get_or_create_bucket(self.bucket_name)
        return self._bucket

    @property
    def entries(self):
        """
        Get the cached files for the bucket.
        """
        global cached_entries
        
        if self._entries is None: # this part only ever gets executed once:
            if self.preload_metadata:
                try:
                    self._entries = cached_entries[self.bucket_name]
                except KeyError:
                    self._entries = dict((self._decode_name(entry.key), CachedKey(entry.size, entry.last_modified))
                                    for entry in self.bucket.list())
                    cached_entries[self.bucket_name] = self._entries
            else:
                self._entries = {}
        return self._entries
    
    def _get_key(self, name):
        """ Get this key from the bucket, if not already in the entries cache """
        key_name = self._encode_name(name)
        try:
            return self.entries[key_name]
        except KeyError:
            key = self.bucket.get_key(key_name)
            if key and self.preload_metadata:
                self.entries[key_name] = CachedKey(key.size, key.last_modified)
            return key
    
    def _delete_key(self, name):
        """ Delete this key from the bucket and from the entries """
        key_name = self._encode_name(name)
        self.entries.pop(key_name, None) # Remove from preloaded cache, if we're using that
        self.bucket.delete_key(key_name)

    def _get_access_keys(self):
        """
        Gets the access keys to use when accessing S3. If none
        are provided to the class in the constructor or in the 
        settings then get them from the environment variables.
        """
        access_key = ACCESS_KEY_NAME
        secret_key = SECRET_KEY_NAME
        if (access_key or secret_key) and (not access_key or not secret_key):
            # TODO: this seems to be broken
            access_key = os.environ.get(ACCESS_KEY_NAME)
            secret_key = os.environ.get(SECRET_KEY_NAME)

        if access_key and secret_key:
            # Both were provided, so use them
            return access_key, secret_key

        return None, None

    def _get_or_create_bucket(self, name):
        """Retrieves a bucket if it exists, otherwise creates it."""
        try:
            return self.connection.get_bucket(name,
                validate=AUTO_CREATE_BUCKET)
        except S3ResponseError:
            if AUTO_CREATE_BUCKET:
                bucket = self.connection.create_bucket(name)
                bucket.set_acl(self.bucket_acl)
                return bucket
            raise ImproperlyConfigured("Bucket specified by "
                "AWS_STORAGE_BUCKET_NAME does not exist. "
                "Buckets can be automatically created by setting "
                "AWS_AUTO_CREATE_BUCKET=True")

    def _clean_name(self, name):
        """
        Cleans the name so that Windows style paths work
        """
        # Useful for windows' paths
        return os.path.normpath(name).replace('\\', '/')

    def _normalize_name(self, name):
        """
        Normalizes the name so that paths like /path/to/ignored/../something.txt
        work. We check to make sure that the path pointed to is not outside
        the directory specified by the LOCATION setting.
        """
        try:
            return safe_join(self.location, name)
        except ValueError:
            raise SuspiciousOperation("Attempted access to '%s' denied." %
                                      name)

    def _encode_name(self, name):
        return smart_str(name, encoding=self.file_name_charset)

    def _decode_name(self, name):
        return force_unicode(name, encoding=self.file_name_charset)

    def _compress_content(self, content):
        """Gzip a given string content."""
        zbuf = StringIO()
        zfile = GzipFile(mode='wb', compresslevel=6, fileobj=zbuf)
        zfile.write(content.read())
        zfile.close()
        content.file = zbuf
        return content

    def _open(self, name, mode='rb'):
        name = self._normalize_name(self._clean_name(name))
        f = S3BotoStorageFile(name, mode, self)
        if not f.key:
            raise IOError('File does not exist: %s' % name)
        return f

    def _save(self, name, content):
        cleaned_name = self._clean_name(name)
        name = self._normalize_name(cleaned_name)
        headers = self.headers.copy()
        content_type = getattr(content, 'content_type',
            mimetypes.guess_type(name)[0] or Key.DefaultContentType)

        if self.gzip and content_type in self.gzip_content_types:
            content = self._compress_content(content)
            headers.update({'Content-Encoding': 'gzip'})

        content.name = cleaned_name
        encoded_name = self._encode_name(name)
        key = self.bucket.get_key(encoded_name)
        if not key:
            key = self.bucket.new_key(encoded_name)

        key.set_metadata('Content-Type', content_type)
        key.set_contents_from_file(content, headers=headers, policy=self.acl,
                                 reduced_redundancy=self.reduced_redundancy)
        if self.preload_metadata:
            #self.entries[encoded_name] = CachedKey(key.size, key.last_modified)
            # The above doesn't work because 'last_modified' doesn't get updated
            # when boto does an S3 PUT request :-( so instead, we invalidate the
            # cache, so next time, we'll load new metadata with a HEAD request:
            self.entries.pop(encoded_name, None)
        return cleaned_name

    def delete(self, name):
        name = self._normalize_name(self._clean_name(name))
        self._delete_key(name)

    def exists(self, name):
        name = self._normalize_name(self._clean_name(name))
        key_name = self._encode_name(name)
        if self.entries and key_name in self.entries:
            return True
        k = self.bucket.get_key(key_name)
        if k:
            if self.entries:
                # Update this key in the cache; it has been created in another process
                self.entries[key_name] = CachedKey(k.size, k.last_modified)
            return True
        return False

    def listdir(self, name):
        name = self._normalize_name(self._clean_name(name))
        # for the bucket.list and logic below name needs to end in /
        # But for the root path "" we leave it as an empty string
        if name:
            name += '/'

        dirlist = self.bucket.list(self._encode_name(name))
        files = []
        dirs = set()
        base_parts = name.split("/")[:-1]
        for item in dirlist:
            parts = item.name.split("/")
            parts = parts[len(base_parts):]
            if len(parts) == 1:
                # File
                files.append(parts[0])
            elif len(parts) > 1:
                # Directory
                dirs.add(parts[0])
        return list(dirs), files

    def size(self, name):
        name = self._normalize_name(self._clean_name(name))
        return self._get_key(name).size

    def modified_time(self, name):
        name = self._normalize_name(self._clean_name(name))
        entry = self._get_key(name)
        if not entry:
            raise IOError("File does not exist.")
        last_modified_date = dateparser.parse(entry.last_modified)
        # if the date has no timzone, assume UTC
        if last_modified_date.tzinfo == None:
            last_modified_date = last_modified_date.replace(tzinfo=tz.tzutc())
        # convert date to local time without timezone
        return last_modified_date.astimezone(tz.tzlocal()).replace(tzinfo=None)

    def url(self, name):
        name = self._normalize_name(self._clean_name(name))
        if self.custom_domain:
            return "%s://%s/%s" % ('https' if self.secure_urls else 'http',
                                   self.custom_domain, name)
        return self.connection.generate_url(self.querystring_expire,
            method='GET', bucket=self.bucket.name, key=self._encode_name(name),
            query_auth=self.querystring_auth, force_http=not self.secure_urls)

    def get_available_name(self, name):
        """ Overwrite existing file with the same name. """
        if FILE_OVERWRITE:
            name = self._clean_name(name)
            return name
        return super(S3BotoStorage, self).get_available_name(name)


class S3BotoStorageFile(File):
    """
    The default file object used by the S3BotoStorage backend.
    
    This file implements file streaming using boto's multipart
    uploading functionality. The file can be opened in read or
    write mode.

    This class extends Django's File class. However, the contained
    data is only the data contained in the current buffer. So you
    should not access the contained file object directly. You should
    access the data via this class.

    Warning: This file *must* be closed using the close() method in
    order to properly write the file to S3. Be sure to close the file
    in your application.
    """
    # TODO: Read/Write (rw) mode may be a bit undefined at the moment. Needs testing.
    # TODO: When Django drops support for Python 2.5, rewrite to use the 
    #       BufferedIO streams in the Python 2.6 io module.

    def __init__(self, name, mode, storage, buffer_size=FILE_BUFFER_SIZE):
        self._storage = storage
        self.name = name[len(self._storage.location):].lstrip('/')
        self.full_name = name
        self._mode = mode
        self.key = storage._get_key(name) # Note: this will usually be a
                                          # CachedKey object...
        self._is_dirty = False
        self._file = None
        self._multipart = None
        # 5 MB is the minimum part size (if there is more than one part).
        # Amazon allows up to 10,000 parts.  The default supports uploads
        # up to roughly 50 GB.  Increase the part size to accommodate 
        # for files larger than this.
        self._write_buffer_size = buffer_size
        self._write_counter = 0

    @property
    def real_key(self):
        " Ensure that we have a full Key object, and not just a CachedKey "
        if type(self.key) is CachedKey:
            self.key = self._storage.bucket.get_key(self._storage._encode_name(self.full_name))
            if not self.key and 'w' in self._mode:
                self.key = self._storage.bucket.new_key(self._storage._encode_name(self.full_name))
        return self.key

    @property
    def size(self):
        return self.key.size

    @property
    def file(self):
        if self._file is None:
            self._file = StringIO()
            if 'r' in self._mode:
                self._is_dirty = False
                self.real_key.get_contents_to_file(self._file)
                self._file.seek(0)
        return self._file

    def read(self, *args, **kwargs):
        if 'r' not in self._mode:
            raise AttributeError("File was not opened in read mode.")
        return super(S3BotoStorageFile, self).read(*args, **kwargs)

    def write(self, *args, **kwargs):
        if 'w' not in self._mode:
            raise AttributeError("File was not opened in write mode.")
        self._is_dirty = True
        if self._multipart is None:
            provider = self.real_key.bucket.connection.provider
            upload_headers = {
                provider.acl_header: self._storage.acl
            }
            upload_headers.update(self._storage.headers)
            self._multipart = self._storage.bucket.initiate_multipart_upload(
                self.real_key.name,
                headers = upload_headers,
                reduced_redundancy = self._storage.reduced_redundancy
            )
        if self._write_buffer_size <= self._buffer_file_size:
            self._flush_write_buffer()
        return super(S3BotoStorageFile, self).write(*args, **kwargs)

    @property
    def _buffer_file_size(self):
        pos = self.file.tell()
        self.file.seek(0,os.SEEK_END)
        length = self.file.tell()
        self.file.seek(pos)
        return length

    def _flush_write_buffer(self):
        """
        Flushes the write buffer.
        """
        if self._buffer_file_size:
            self._write_counter += 1
            self.file.seek(0)
            self._multipart.upload_part_from_file(
                self.file,
                self._write_counter,
                headers=self._storage.headers
            )
            self.file.close()
            self._file = None

    def close(self):
        if self._is_dirty:
            self._flush_write_buffer()
            self._multipart.complete_upload()
        else:
            if not self._multipart is None:
                self._multipart.cancel_upload()
        self.real_key.close()
