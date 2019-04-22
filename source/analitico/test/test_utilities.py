import unittest
from analitico.utilities import get_dict_dot

TST_DICT = {
    "parent_1": {
        "child_1": {"grandchild_1_1": 10, "grandchild_1_2": 20},
        "child_2": {"grandchild_2_1": "30", "grandchild_2_2": "40"},
        "child_3": 24,
    },
    "parent_2": 42,
}


class UtilitiesTests(unittest.TestCase):
    def test_get_dict_dot(self):
        self.assertEqual(get_dict_dot(TST_DICT, "parent_1.child_1.grandchild_1_1"), 10)
        self.assertEqual(get_dict_dot(TST_DICT, "parent_1.child_1.grandchild_1_2"), 20)
        self.assertEqual(get_dict_dot(TST_DICT, "parent_1.child_3"), 24)

    def test_get_dict_dot_missing_value(self):
        self.assertEqual(get_dict_dot(TST_DICT, "parent_4"), None)
        self.assertEqual(get_dict_dot(TST_DICT, "parent_4", 38), 38)
        self.assertEqual(get_dict_dot(TST_DICT, "parent_4", "Mickey"), "Mickey")
        self.assertEqual(get_dict_dot(TST_DICT, "parent_2.unknown"), None)
        self.assertEqual(get_dict_dot(TST_DICT, "parent_2.unknown", 38), 38)
        self.assertEqual(get_dict_dot(TST_DICT, "parent_2.unknown", "Mickey"), "Mickey")
        self.assertEqual(get_dict_dot(TST_DICT, "parent_1.child_3.unknown"), None)
        self.assertEqual(get_dict_dot(TST_DICT, "parent_1.child_3.unknown", 38), 38)
        self.assertEqual(get_dict_dot(TST_DICT, "parent_1.child_3.unknown", "Mickey"), "Mickey")
        self.assertEqual(get_dict_dot(TST_DICT, "parent_2"), 42)

    def test_get_dict_dot_missing_key(self):
        self.assertEqual(get_dict_dot(TST_DICT, None), None)
        self.assertEqual(get_dict_dot(TST_DICT, None, 24), 24)
