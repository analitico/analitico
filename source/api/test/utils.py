
import rest_framework.test

from django.urls import reverse
from django.test import TestCase
from api.models import Project, Token, Call, User

# pylint: disable=no-member


class APITestCase(rest_framework.test.APITestCase):
    """ Base class for testing analitico APIs """

    def setup_basics(self):
        self.user1 = User.objects.create_user(email='user1@analitico.ai', is_superuser=True) # 1st user is admin
        self.user2 = User.objects.create_user(email='user2@analitico.ai') # 2nd is a regular user
        self.user3 = User.objects.create_user(email='user3@analitico.ai') # 3rd is a regular user

        self.token1 = Token.objects.create(pk='tok_user1', user=self.user1)
        self.token2 = Token.objects.create(pk='tok_user2', user=self.user2)
        self.token3 = Token.objects.create(pk='tok_user3', user=self.user3)


    def setUp(self):
        """ Prepare test users with test auth tokens """
        self.setup_basics()


    def auth_token(self, token=None):
        """ Append authorization token to self.client calls """        
        if token is not None:
            self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token.id)
        else:
            self.client.logout()
