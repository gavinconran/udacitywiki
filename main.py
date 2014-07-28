import os
import webapp2
from google.appengine.ext import db
from google.appengine.api import memcache
import jinja2
import random
import hashlib
import hmac
import errors
import string
from xml.dom import minidom
import json
import time
import logging

SECRET = 'gavinconran'

def hash_str(s):
        return hmac.new(SECRET, s).hexdigest()

def make_secure_val(s):
        return "%s|%s" % (s, hash_str(s))

def check_secure_val(h):
        val = h.split('|')[0]
        if h == make_secure_val(val):
                return val
        
def make_salt():
    return ''.join(random.choice(string.letters) for x in xrange(5))
        
def make_pw_hash(name, pw, salt=None):
    if not salt:
        salt=make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s,%s' % (h, salt)

def valid_pw(name, pw, h):
    salt = h.split(',')[1]
    return h == make_pw_hash(name, pw, salt)        

template_dir = os.path.join(os.path.dirname(__file__), "")
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

class Handler(webapp2.RequestHandler):
  def write(self, *a, **kw):
    self.response.out.write(*a, **kw)
    
  def render_str(self, template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)
  
  def render(self, template, **kw):
    self.write(self.render_str(template, **kw))
    
  def set_cookie(self, user_name):
        cookie_val = make_secure_val(str(user_name))
        self.response.headers.add_header('Set-Cookie', 'userid=%s; Path=/' % cookie_val)
        self.redirect("/welcome")
  
  def render_json(self, d):
    self.response.headers={'Content-Type':'application/json; charset=utf-8'}
    self.response.out.write(json.dumps(d))

# memcached DB query    
def top_posts(update = False):
        key = 'top'
        posts = memcache.get(key)
        if posts is None or update:
          logging.error("DB QUERY")
          posts = db.GqlQuery("SELECT * "
                             "FROM Post "
                             #"WHERE ANCESTOR IS :1 "
                             "ORDER BY created DESC "
                             "LIMIT 10"#,
                             #art_key
                             )
          posts = list(posts)
          memcache.set(key, posts)
        return posts      

     
def timecache(key):
  lasttime = memcache.get(key)
  if lasttime is None:
    lasttime = time.time()
    memcache.set(key, lasttime)
  return lasttime  
  
      
class MainPage(Handler):
    def get(self):
        #starttime = timecache(key='index')
        posts = top_posts()
        #timetaken = time.time() - starttime
    	self.render("index.html", posts = posts) #, timetaken = str(int(timetaken)))

class Flush(Handler):
    def get(self):
        memcache.flush_all()
        self.redirect('/')
        
        
class MainPageJSON(Handler):
    def get(self):
        posts = db.GqlQuery("SELECT * FROM Post ORDER BY created DESC limit 10")
        postslist = []
        postdict = {}
        for post in posts:
          postdict['subject'] = post.subject
          postdict['content'] = post.content
          postslist.append(postdict)
        
        self.render_json(postslist)       

class NewPost(Handler):
    def get(self):
        self.render("front.html", myaction="Enter a new post")
        
    def post(self):
    	subject = self.request.get("subject") 
    	content = self.request.get("content")
        if subject and content:
           p = Post(subject = subject, content = content.replace('\n', '<br>'))
           p.put()
           # rerun the query and update memcache
           top_posts(True) 
           self.redirect('/%s' % str(p.key().id()))
        else:
           error = "we need both a subject and some content!" 
           self.render("front.html", myaction="Enter a new post", subject=subject, content=content, error = error)
            
class PostPage(Handler):
    def get(self, post_id):
      key = db.Key.from_path('Post', int(post_id))
      post = db.get(key)
    
      if not post:
        self.error(404)
        return      
      #starttime = timecache(key=str(key))
      #timetaken = time.time() - starttime
      self.render("permalink.html", post = post) #, timetaken = str(int(timetaken)))

class PostPageJSON(Handler):
    def get(self, post_id):
      key = db.Key.from_path('Post', int(post_id))
      post = db.get(key)
    
      if not post:
        self.error(404)
        return
      postdict = {'subject': post.subject, 'content': post.content}
      self.render_json(postdict)
            
class Signup(Handler):
    def get(self):    
      self.render("signon.html")
    
    def post(self):
      user_name = self.request.get('username')
      user_password = self.request.get('password')
      user_verify = self.request.get('verify')
      user_email = self.request.get('email')
    
      (count, params) = errors.GenerateErrorMessages(user_name, user_password, user_verify, user_email)
    
      if count == 0:
        user_db = db.GqlQuery("SELECT * FROM User WHERE name=:1", user_name) 
        user = user_db.get()
        if user:
          username_error = "That user already exists"
          self.render("signon.html", username_error = username_error)
        else:  
          user = User(name = user_name, password = make_pw_hash(user_name, user_password), email = user_email)
          user.put()
          # set cookie
          user_id=str(user.key().id())
          self.set_cookie(user_id)
      else:
        self.render("signon.html", **params)
      
class Logon(Handler):
    def get(self):
      self.render("logon.html")
    
    def post(self):
      user_name = self.request.get('username')
      user_password = self.request.get('password')
    
      user_db = db.GqlQuery("SELECT * FROM User WHERE name=:1", user_name) 
      user = user_db.get()
      if user:
        # set cookie
        user_id=str(user.key().id())
        self.set_cookie(user_id)
      else:  
        self.render("logon.html", logon_error = "Invalid user")
            
class Welcome(Handler):
    def get(self):  
      self.response.headers['Content-Type'] = 'text/plain'
      userid_cookie_str = self.request.cookies.get('userid')
      self.response.headers['Content-Type'] = 'text/html'
      if userid_cookie_str:
        cookie_val = check_secure_val(userid_cookie_str)
        if cookie_val:
          user = User.get(db.Key.from_path('User', int(cookie_val)))
          self.render("welcome.html", username = user.name.capitalize())
        else:
          self.redirect('/signup')
      else:
        self.redirect('/signup')  

class Logout(Handler):
    def get(self):
      self.response.headers.add_header('Set-Cookie', "userid=deleted;  Expires=Thu, 01-Jan-1970 00:00:00 GMT")
      self.redirect('/logon')  
      
class User(db.Model):
      name = db.StringProperty(required = True)
      password = db.StringProperty(required = True)
      email = db.StringProperty()
      created = db.DateTimeProperty(auto_now_add = True)
      last_modified = db.DateTimeProperty(auto_now = True)
        
class Post(db.Model):
      subject = db.StringProperty(required = True)
      content = db.TextProperty(required = True)
      created = db.DateTimeProperty(auto_now_add = True)
      last_modified = db.DateTimeProperty(auto_now = True)
      
      
APP = webapp2.WSGIApplication([('/signup/?', Signup),
                               ('/welcome', Welcome),
                               ('/logon/?', Logon),
                               ('/logout/?', Logout),
                               ('/?', MainPage),
                               ('/.json', MainPageJSON),
                               ('/newpost/?', NewPost),
                               ('/([0-9]+)', PostPage),
                               ('/([0-9]+).json', PostPageJSON),
                               ('/flush/?', Flush)],
                              debug=True)
