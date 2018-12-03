import unittest

from django.utils.crypto import get_random_string

class TestDjango(unittest.TestCase):

    def test_get_random_string_doesnt_repeat(self):
        s1 = get_random_string()
        s2 = get_random_string()
        self.assertNotEqual(s1, s2)




if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDjango)
    unittest.TextTestRunner(verbosity=2).run(suite)

    