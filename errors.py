import re

error_messages = {
                  "username_error": "That's not a valid username.", 
                  "password_error": "That wasn't a valid password.", 
                  "verify_error": "Your passwords didn't match.", 
                  "email_error": "That's not a valid email."
                  }

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
  return username and USER_RE.match(username)

USER_PWD = re.compile(r"^.{3,20}$")
def valid_password(password):
  return password and USER_PWD.match(password)

USER_EMAIL = re.compile(r"^[\S]+@[\S]+\.[\S]+$")
def valid_email(email):
  return not email or USER_EMAIL.match(email)

def GenerateErrorMessages(user_name, user_password, user_verify, user_email):
  params = dict(username = user_name, email = user_email) 
  count = 0
    
  if not valid_username(user_name):
    params['username_error'] = error_messages["username_error"]
    count+= 1
          
  if not valid_password(user_password):
    params['password_error'] = error_messages["password_error"]
    count+= 1
      
  if not(user_password == user_verify):
    params['verify_error'] = error_messages["verify_error"]
    count+= 1
   
  if not valid_email(user_email):
    params['email_error'] = error_messages["email_error"]
    count+= 1
    
  return (count, params)
  


