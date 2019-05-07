import unittest
import tempfile
import numpy as np

from analitico.utilities import get_dict_dot, save_json, read_json, read_text, save_text

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

    def test_save_json(self):
        values1 = {"key1": "value1", "key2": 5}

        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json") as f:
            save_json(values1, f.name)
            values2 = read_json(f.name)

            self.assertEqual(values1["key1"], values2["key1"])
            self.assertEqual(values1["key2"], values2["key2"])

    def test_save_json_with_nan(self):
        """ Test saving a numpy.nan value (should get converted to null) """
        # NaN should be encoded as null, non "NaN" according to ECMA-262
        # https://simplejson.readthedocs.io/en/latest/ (find: ignore_nan)

        values1 = {"nanKey": np.nan}

        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json") as f:
            save_json(values1, f.name, indent=0)

            json2 = read_text(f.name)
            self.assertEqual(json2, '{\n"nanKey": null\n}')

            values2 = read_json(f.name)
            self.assertEqual(values2["nanKey"], None)
