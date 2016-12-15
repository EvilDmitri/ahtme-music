# coding=utf-8
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

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

collectives = {
    'antares': 'Антарес',
    'arlekin': 'Арлекин',
    'step': 'Степ-студия',
    'viva': 'Viva Dance',
    'smirnov': 'Смирнов'

}


class UserMusic(db.Model):
    user = db.StringProperty()
    blob = blobstore.BlobReferenceProperty()
    blob_key = ndb.BlobKeyProperty()


# class UserMusic(ndb.Model):
#     user = ndb.StringProperty()
#     blob_key = ndb.BlobKeyProperty()
#     blob = blobstore.BlobReferenceProperty()


class MainHandler(webapp2.RequestHandler):
    def get(self):
        template_values = {
            'blobs': blobstore.BlobInfo.all()
        }
        template = JINJA_ENVIRONMENT.get_template('templates/main.html')
        self.response.write(template.render(template_values))


class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        collective = self.request.get('collective')
        try:
            upload = self.get_uploads()[0]
            user_music = UserMusic(
                user=collective,
                # test='test field',
                # user=users.get_current_user().user_id(),
                blob=upload,
                blob_key=upload.key())

            print user_music
            user_music.put()
            self.redirect('/collective/' + collective)
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


class CollectiveHandler(webapp2.RequestHandler):
    def getRecordDate(self, item):
        # creation = None
        # try:
        #     creation = item.blob.creation
        # except EntityNotFoundError:
        #     pass
        return item.blob.creation

    def get(self, collective):
        # files = sorted(UserMusic.query())
        # files = sorted(UserMusic.all())
        files = UserMusic.all()
        files.filter('user =', collective)
        # files = sorted(UserMusic.all(), key=self.getRecordDate, reverse=True)
        print files

        template_values = {
            # 'user': user,
            'blobs': files,
            'upload_url': blobstore.create_upload_url('/upload'),
            'collective': collective,
            'collective_name': collectives[collective]
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


app = webapp2.WSGIApplication([('/', MainHandler),
                               ('/collective/([^/]+)?', CollectiveHandler),
                               ('/upload', UploadHandler),
                               ('/delete/([^/]+)?', DeleteHandler),
                               ('/([^/]+)?/([^/]+)?', GetHandler),

                               # Obsolete route handler (retains backward compatibility)
                               # See also app.yaml config "url: /get/(.*?)/(.*)"
                               ('/get/([^/]+)?/([^/]+)?', GetHandler)], debug=True)
