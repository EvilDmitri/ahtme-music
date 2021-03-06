# coding=utf-8
import webapp2
import os
import os.path
import urllib
import logging

from mutagen.mp3 import MP3
import datetime

from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.ext import blobstore, db
from google.appengine.ext.blobstore import BlobInfo
# from google.appengine.ext import webapp
from google.appengine.ext.db import EntityNotFoundError
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app


from webapp2_extras import auth
from webapp2_extras import sessions

from webapp2_extras.auth import InvalidAuthIdError
from webapp2_extras.auth import InvalidPasswordError

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
    'smirnov': 'Смирнов',
    'oxana': 'Оксана',
    'jelena': 'Елена',
    'irena': 'Ирена',
    'common': 'Общая'


}


def secs_to_minutes(secs):
    return datetime.datetime.fromtimestamp(secs).strftime('%M:%S')


def user_required(handler):
    """
    Decorator that checks if there's a user associated with the current session.
    Will also fail if there's no session present.
  """

    def check_login(self, *args, **kwargs):
        auth = self.auth
        if not auth.get_user_by_session():
            self.redirect(self.uri_for('login'), abort=True)
        else:
            return handler(self, *args, **kwargs)

    return check_login


class BaseHandler(webapp2.RequestHandler):
    @webapp2.cached_property
    def auth(self):
        """Shortcut to access the auth instance as a property."""
        return auth.get_auth()

    @webapp2.cached_property
    def user_info(self):
        """Shortcut to access a subset of the user attributes that are stored
    in the session.

    The list of attributes to store in the session is specified in
      config['webapp2_extras.auth']['user_attributes'].
    :returns
      A dictionary with most user information
    """
        return self.auth.get_user_by_session()

    @webapp2.cached_property
    def user(self):
        """Shortcut to access the current logged in user.

    Unlike user_info, it fetches information from the persistence layer and
    returns an instance of the underlying model.

    :returns
      The instance of the user model associated to the logged in user.
    """
        u = self.user_info
        return self.user_model.get_by_id(u['user_id']) if u else None

    @webapp2.cached_property
    def user_model(self):
        """Returns the implementation of the user model.

    It is consistent with config['webapp2_extras.auth']['user_model'], if set.
    """
        return self.auth.store.user_model

    @webapp2.cached_property
    def session(self):
        """Shortcut to access the current session."""
        return self.session_store.get_session(backend="datastore")

    def render_template(self, view_filename, params=None):
        if not params:
            params = {}
        user = self.user_info
        params['user'] = user
        template = JINJA_ENVIRONMENT.get_template(view_filename)
        self.response.write(template.render(params))

    def display_message(self, message):
        """Utility function to display a template with a simple message."""
        params = {
            'message': message
        }
        self.render_template('/templates/message.html', params)

    # this is needed for webapp2 sessions to work
    def dispatch(self):
        # Get a session store for this request.
        self.session_store = sessions.get_store(request=self.request)

        try:
            # Dispatch the request.
            webapp2.RequestHandler.dispatch(self)
        finally:
            # Save all sessions.
            self.session_store.save_sessions(self.response)


class UserMusic(db.Model):
    user = db.StringProperty()
    blob = blobstore.BlobReferenceProperty()
    blob_key = ndb.BlobKeyProperty()
    length = db.StringProperty()


# class UserMusic(ndb.Model):
#     user = ndb.StringProperty()
#     blob_key = ndb.BlobKeyProperty()
#     blob = blobstore.BlobReferenceProperty()


class MainHandler(BaseHandler):
    def get(self):
        # files = UserMusic.all()
        # template_values = {
        #     'blobs': files
        # }
        template = JINJA_ENVIRONMENT.get_template('templates/main.html')
        self.response.write(template.render())


class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        collective = self.request.get('collective')
        # user = users.get_current_user().user_id()
        # print user, ' = ', collective

        try:
            upload = self.get_uploads()[0]
            audio = MP3(upload.open())
            length = int(audio.info.length)

            user_music = UserMusic(
                user=collective,
                # test='test field',
                # user=users.get_current_user().user_id(),
                blob=upload,
                blob_key=upload.key(),
                length=str(secs_to_minutes(length)))

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
        print 'IN GET'
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


class CollectiveHandler(BaseHandler):
    def getRecordDate(self, item):
        creation = None
        try:
            creation = item.blob.creation
        except EntityNotFoundError:
            pass
        return creation

    def get(self, collective):
        # files = sorted(UserMusic.query())
        # files = sorted(UserMusic.all())
        files = UserMusic.all()
        if files.count() > 1:
            files.filter('user =', collective)
            files = sorted(files, key=self.getRecordDate, reverse=True)

        try:
            user = self.user.auth_ids[0]
        except:
            user = None

        template_values = {
            # 'user': user,
            'blobs': files,
            'upload_url': blobstore.create_upload_url('/upload'),
            'collective': collective,
            'collective_name': collectives[collective],
            'user': user
        }

        # print self.user.auth_ids[0]

        template = JINJA_ENVIRONMENT.get_template('templates/list.html')
        self.response.write(template.render(template_values))


class DeleteHandler(webapp2.RequestHandler):
    def get(self, blob_key, collective):
        print 'IN DELETE'
        try:
            blob_key = urllib.unquote(blob_key)
            record = UserMusic.get_by_id(int(blob_key))

            record.blob.delete()
            record.delete()
        except:
            self.error(404)
        self.redirect('/collective/'+collective)


class LoginHandler(BaseHandler):
    def get(self):
        self._serve_page()

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')
        print password, username
        try:
            u = self.auth.get_user_by_password(username, password, remember=True,
                                               save_session=True)
            self.redirect('/collective/' + username)
        except (InvalidAuthIdError, InvalidPasswordError) as e:
            logging.info('Login failed for user %s because of %s', username, type(e))
            self._serve_page(True)

    def _serve_page(self, failed=False):
        username = self.request.get('username')
        params = {
            'username': username,
            'failed': failed
        }
        self.render_template('templates/login.html', params)


class LogoutHandler(BaseHandler):
    def get(self):
        self.auth.unset_session()
        self.redirect('/')


class SignupHandler(BaseHandler):
    def get(self):
        self.render_template('templates/signup.html')

    def post(self):
        user_name = self.request.get('username')
        # email = self.request.get('email')
        name = self.request.get('username')
        password = self.request.get('password')
        # last_name = self.request.get('lastname')

        unique_properties = ['name']
        user_data = self.user_model.create_user(user_name,
                                                unique_properties,
                                                name=name, password_raw=password,
                                                verified=True)
        if not user_data[0]:  # user_data is a tuple
            self.display_message('Unable to create user for email %s because of \
        duplicate keys %s' % (user_name, user_data[1]))
            return

        user = user_data[1]
        # user_id = user.get_id()
        user.put()
        self.redirect('/signup')

        # token = self.user_model.create_signup_token(user_id)
        #
        # verification_url = self.uri_for('verification', type='v', user_id=user_id,
        #                                 signup_token=token, _full=True)
        #
        # msg = 'Send an email to user in order to verify their address. \
        #   They will be able to do so by visiting <a href="{url}">{url}</a>'
        #
        # self.display_message(msg.format(url=verification_url))


class MeasureHandler(BaseHandler):
    def get(self):
        files = UserMusic.all()
        for f in files:
            if f.length is None:
                audio = MP3(f.blob.open())
                length = int(audio.info.length)
                f.length = str(secs_to_minutes(length))
                f.put()
        self.redirect('/')


config = {
    'webapp2_extras.auth': {
        'user_model': 'models.User',
        'user_attributes': ['name']
    },
    'webapp2_extras.sessions': {
        'secret_key': 'MY_SECRET_KEY'
    }
}


app = webapp2.WSGIApplication([('/', MainHandler),
                               ('/collective/([^/]+)?', CollectiveHandler),
                               ('/upload', UploadHandler),
                               ('/delete/([^/]+)/([^/]+)??', DeleteHandler),
                               ('/([^/]+)?/([^/]+)?', GetHandler),
                               ('/signup', SignupHandler),
                               ('/login', LoginHandler),
                               ('/logout', LogoutHandler),
                               # ('/measure', MeasureHandler),
                               # Obsolete route handler (retains backward compatibility)
                               # See also app.yaml config "url: /get/(.*?)/(.*)"
                               ('/get/([^/]+)?/([^/]+)?', GetHandler)], debug=True, config=config)
