import unittest

from django.test import TestCase
from django.utils.crypto import get_random_string

class DjangoTests(TestCase):

    def test_get_random_string_doesnt_repeat(self):
        s1 = get_random_string()
        s2 = get_random_string()
        self.assertNotEqual(s1, s2)
