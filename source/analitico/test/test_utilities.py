
import api.utilities

from django.test import TestCase
from django.core.validators import validate_slug
from api.models.training import generate_training_id
from analitico.utilities import get_dict_dot

TST_DICT = {
    'parent_1': {
        'child_1': {
            'grandchild_1_1': 10,
            'grandchild_1_2': 20 
        },
        'child_2': {
            'grandchild_2_1': '30',
            'grandchild_2_2': '40' 
        },
        'child_3': 24
    },
    'parent_2': 42
}

class TestUtilities(TestCase):

    def test_get_dict_dot(self):
        self.assertEqual(get_dict_dot(TST_DICT, 'parent_1.child_1.grandchild_1_1'), 10)
        self.assertEqual(get_dict_dot(TST_DICT, 'parent_1.child_1.grandchild_1_2'), 20)
        self.assertEqual(get_dict_dot(TST_DICT, 'parent_1.child_3'), 24)

    def test_get_dict_dot_default1(self):
        self.assertEqual(get_dict_dot(TST_DICT, 'parent_4'), None)
        self.assertEqual(get_dict_dot(TST_DICT, 'parent_4', 38), 38)
        self.assertEqual(get_dict_dot(TST_DICT, 'parent_4', 'Mickey'), 'Mickey')

    def test_get_dict_dot_default2(self):
        self.assertEqual(get_dict_dot(TST_DICT, 'parent_2.unknown'), None)
        self.assertEqual(get_dict_dot(TST_DICT, 'parent_2.unknown', 38), 38)
        self.assertEqual(get_dict_dot(TST_DICT, 'parent_2.unknown', 'Mickey'), 'Mickey')

    def test_get_dict_dot_default3(self):
        self.assertEqual(get_dict_dot(TST_DICT, 'parent_1.child_3.unknown'), None)
        self.assertEqual(get_dict_dot(TST_DICT, 'parent_1.child_3.unknown', 38), 38)
        self.assertEqual(get_dict_dot(TST_DICT, 'parent_1.child_3.unknown', 'Mickey'), 'Mickey')
        self.assertEqual(get_dict_dot(TST_DICT, 'parent_2'), 42)

    def test_get_dict_dot_no_key(self):
        self.assertEqual(get_dict_dot(TST_DICT, None), None)
        self.assertEqual(get_dict_dot(TST_DICT, None, 24), 24)
