import webapp2
import os
import urllib
import logging

from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.ext import blobstore, db
from google.appengine.ext.blobstore import BlobInfo
# from google.appengine.ext import webapp
from google.appengine.ext.db import EntityNotFoundError
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import jinja2

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


class UserMusic(db.Model):
    user = ndb.StringProperty()
    blob = blobstore.BlobReferenceProperty()


# class UserMusic(ndb.Model):
#     user = ndb.StringProperty()
#     blob_key = ndb.BlobKeyProperty()
#     blob = blobstore.BlobReferenceProperty()


class MainHandler(webapp2.RequestHandler):
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
        try:
            upload = self.get_uploads()[0]
            user_music = UserMusic(
                user='antares',
                # user=users.get_current_user().user_id(),
                # blob=upload,
                # blob_key=upload.key())
                blob=upload)

            print user_music
            user_music.put()
            self.redirect('/')
        except:
            self.error(500)

        # blob_info = self.get_uploads('file')[0]  # 'file' is file upload field in the form
        # record = FileRecord(blob=blob_info)
        # record.put()
        # self.redirect('/')


class GetHandler(blobstore_handlers.BlobstoreDownloadHandler):
  def get(self, blob_key, filename):
    logging.info('GetHandler blob_key=%s filename=%s' % (blob_key, filename))
    blob_key = str(urllib.unquote(blob_key))
    record = UserMusic.get_by_id(int(blob_key))

    # Set content type and open file instead of download
    self.response.headers['Content-Type'] = record.blob.content_type

    # Add cache headers. Can cache forever because of unique ID in URL
    self.response.headers['Cache-Control'] = 'public'
    self.response.headers['Cache-Control: max-age'] = '31536000'
    self.response.headers['Expires'] = 'Thu, 31 Dec 2037 00:00:00 GMT'
    self.send_blob(record.blob)

#
# class RemoveBLob(webapp.RequestHandler):
#     def get(self):
#         print self.request.get('key')
#         #
#         # blob_key = str(urllib.unquote(blob_key))
#         # if not blobstore.get(blob_key):
#         #     self.error(404)
#         # else:
#         #     print blob_key
#         #     blobstore.delete(blob_key)


class MainPage(webapp2.RequestHandler):
    def getRecordDate(self, item):
        # creation = None
        # try:
        #     creation = item.blob.creation
        # except EntityNotFoundError:
        #     pass
        return item.blob.creation

    def get(self):
        # for b in blobstore.BlobInfo.all():
        #     self.response.out.write('<li><a href="/serve/%s' % str(b.key()) + '">' + str(b.filename) + '</a>')
        # blobs = blobstore.BlobInfo.all()

        # files = sorted(UserMusic.query())
        files = sorted(UserMusic.all())
        # files = sorted(UserMusic.all(), key=self.getRecordDate, reverse=True)
        print files


        template_values = {
            # 'user': user,
            'blobs': files,
            'upload_url': blobstore.create_upload_url('/upload')
        }

        template = JINJA_ENVIRONMENT.get_template('templates/list.html')
        self.response.write(template.render(template_values))


class DeleteHandler(webapp2.RequestHandler):
    def get(self, blob_key):
        try:
            blob_key = urllib.unquote(blob_key)
            record = UserMusic.get_by_id(int(blob_key))

            record.blob.delete()
            record.delete()
        except:
            self.error(404)
        self.redirect('/')



app = webapp2.WSGIApplication([('/', MainPage),
                               ('/upload', UploadHandler),
                               ('/delete/([^/]+)?', DeleteHandler),
                               ('/([^/]+)?/([^/]+)?', GetHandler),

                               # Obsolete route handler (retains backward compatibility)
                               # See also app.yaml config "url: /get/(.*?)/(.*)"
                               ('/get/([^/]+)?/([^/]+)?', GetHandler)], debug=True)
