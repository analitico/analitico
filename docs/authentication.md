#
# Social Authentication and Token Authorization
#

Analitico has built in accounts with email and password as well as social login via external providers like Google, GitHub, etc. Once registered users can create login tokens which are then used by their code to access the Analitico APIs.

Social authentication using Github, Google and other OAuth and OpenID networks is implemented using the external library django-allauth. Integrated set of Django applications addressing authentication, registration, account management as well as 3rd party (social) account authentication. This library offers not just the auth workflows but also code to validate emails, merge accounts, change emails, etc.
https://www.intenct.nl/projects/django-allauth/

Home  
https://www.intenct.nl/projects/django-allauth/

Documentation  
https://django-allauth.readthedocs.io/en/latest/

http://127.0.0.1:8000/accounts/email/

##
## URLs
##

^accounts/ ^ ^signup/$ [name='account_signup']  
^accounts/ ^ ^login/$ [name='account_login']  
^accounts/ ^ ^logout/$ [name='account_logout']  
^accounts/ ^ ^password/change/$ [name='account_change_password']  
^accounts/ ^ ^password/set/$ [name='account_set_password']  
^accounts/ ^ ^inactive/$ [name='account_inactive']  
^accounts/ ^ ^email/$ [name='account_email']  
^accounts/ ^ ^confirm-email/$ [name='account_email_verification_sent']  
^accounts/ ^ ^confirm-email/(?P<key>[-:\w]+)/$ [name='account_confirm_email']  
^accounts/ ^ ^password/reset/$ [name='account_reset_password']  
^accounts/ ^ ^password/reset/done/$ [name='account_reset_password_done']  
^accounts/ ^ ^password/reset/key/(?P<uidb36>[0-9A-Za-z]+)-(?P<key>.+)/$ [name='account_reset_password_from_key']  
^accounts/ ^ ^password/reset/key/done/$ [name='account_reset_password_from_key_done']  
^accounts/ ^social/  
^accounts/ ^google/  

Adding a social login to an existing login:  
http://127.0.0.1:8000/accounts/social/connections/

##
## Documentation
##

Django User model  
https://docs.djangoproject.com/en/2.1/ref/contrib/auth/

Django: Custom user model (used to have email instead of username as primary key)  
https://docs.djangoproject.com/en/2.1/topics/auth/customizing/#auth-custom-user

Customizing authentication in Django (used to implement Bearer tokens)  
https://docs.djangoproject.com/en/2.1/topics/auth/customizing/

How to Use Django's Built-in Login System  
https://simpleisbetterthancomplex.com/tutorial/2016/06/27/how-to-use-djangos-built-in-login-system.html

##
## Articles
##

##
## Other Libraries (that do not work well)
##

### django-social-auth
Seems to implement social authentication on various networks specifically implemented for Django. However the project seems dead and now merged into the larger python-social-auth.
https://github.com/omab/django-social-auth

### python-social-auth
General python social auth library implementing OAuht1, OAuth2 and OpenID. Has specific plugins for Django. Should work well (on paper) however after a few hours of trying (on 2019-01-19) I gave up on this one because some bug prevents it from working with the custom user model we use in Django (to replace username with email as the primary key).
https://github.com/omab/python-social-auth

How to add Google and Github OAuth in Django  
https://fosstack.com/how-to-add-google-authentication-in-django/

How to Add Social Login to Django  
https://simpleisbetterthancomplex.com/tutorial/2016/10/24/how-to-add-social-login-to-django.html

Python Social Auth: Django settings  
https://python-social-auth-docs.readthedocs.io/en/latest/configuration/settings.html
