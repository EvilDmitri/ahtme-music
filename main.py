import webapp2
import os
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.ext import blobstore
from google.appengine.ext import webapp
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import jinja2

# https://cloud.google.com/appengine/docs/python/getting-started/generating-dynamic-content-templates
JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

class MainHandler(webapp.RequestHandler):
    def get(self):
        upload_url = blobstore.create_upload_url('/upload')
        self.response.out.write('<html><body>')
        self.response.out.write('<form action="%s" method="POST" enctype="multipart/form-data">' % upload_url)
        self.response.out.write(
            """Upload File: <input type="file" name="file"><br> <input type="submit" name="submit" value="Submit">
            </form></body></html>""")

        for b in blobstore.BlobInfo.all():
            self.response.out.write('<li><a href="/serve/%s' % str(b.key()) + '">' + str(b.filename) + '</a>')


class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        upload_files = self.get_uploads('file')
        blob_info = upload_files[0]
        # user = users.get_current_user()
        # print 'user - ', user
        # print 'blob_info', dir(blob_info)
        self.redirect('/')


class ServeHandler(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self, blob_key):
        blob_key = str(urllib.unquote(blob_key))
        if not blobstore.get(blob_key):
            self.error(404)
        else:
            self.send_blob(blobstore.BlobInfo.get(blob_key), save_as=True)


class RemoveBLob(webapp.RequestHandler):
    def get(self):
        print self.request.get('key')
        #
        # blob_key = str(urllib.unquote(blob_key))
        # if not blobstore.get(blob_key):
        #     self.error(404)
        # else:
        #     print blob_key
        #     blobstore.delete(blob_key)


app = webapp2.WSGIApplication([('/', MainHandler),
                               ('/upload', UploadHandler),
                               ('/serve/([^/]+)?', ServeHandler),
                               ('/delete', RemoveBLob)
                               ], debug=True)
