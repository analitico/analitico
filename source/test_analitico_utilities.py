import unittest

from analitico.utilities import get_dict_dot

DICTIONARY = {
    'first': {
        'second': {
            'third': 5,
            'alt-third': 6,
            'stringhy': 'me-string'
        },
        'key2': 50
    },
    'lev0-key1': 60
}

class TestAnaliticoUtilities(unittest.TestCase):

    def test_get_dict_dot(self):
        self.assertEqual(get_dict_dot(DICTIONARY, 'first.second.third'), 5)
        self.assertEqual(get_dict_dot(DICTIONARY, 'first.second.alt-third'), 6)
        self.assertEqual(get_dict_dot(DICTIONARY, 'first.second.stringhy'), 'me-string')
        self.assertEqual(get_dict_dot(DICTIONARY, 'first.key2'), 50)
        self.assertEqual(get_dict_dot(DICTIONARY, 'lev0-key1'), 60)


    def test_get_dict_dot_invalid(self):
        self.assertEqual(get_dict_dot(DICTIONARY, None), None)
        self.assertEqual(get_dict_dot(DICTIONARY, '.'), None)
        self.assertEqual(get_dict_dot(DICTIONARY, '...'), None)
        self.assertEqual(get_dict_dot(DICTIONARY, 'first.missing.third'), None)
        self.assertEqual(get_dict_dot(DICTIONARY, 'mis.missing.third'), None)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAnaliticoUtilities)
    unittest.TextTestRunner(verbosity=2).run(suite)
