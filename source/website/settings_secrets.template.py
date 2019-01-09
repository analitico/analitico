
# Instructions:
# Fill out with your credentials then rename 'settings_secrets.py'
#
# This file contains only those settings that need to remain
# private and cannot be checked in to the main repository. 
# The CD/CI chain will deploy this file directly on the servers.
# This also allows devs to direct the app to their own database.

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'egYrJNYFoUThmuwqPzN3UxtxwXnM4z9ccocYTU8n0Q'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# https://docs.djangoproject.com/en/2.1/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'mysql.connector.django',
        'NAME': 'your-schema',
        'USER': 'your-user',
        'PASSWORD': 'your-password',
        'PORT': '3306',
        'HOST': '127.0.0.1',
    }
}
