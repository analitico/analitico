import unittest
import tempfile
import numpy as np
import os

from analitico.utilities import get_dict_dot, save_json, read_json, read_text, save_text, copy_directory

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

    def test_copy_directory(self):
        source = tempfile.TemporaryDirectory()
        destination = tempfile.TemporaryDirectory()
        symlinked_dir = tempfile.TemporaryDirectory()
        symlinked_dir_basename = os.path.basename(symlinked_dir.name)

        f1 = "f1.txt"
        save_text("micky", os.path.join(source.name, f1))
        f2 = "f2.txt"
        save_text("mouse", os.path.join(source.name, f2))
        # duplicate f2 into the destination folder
        save_text("batman", os.path.join(destination.name, f2))
        f3 = "f3.txt"
        save_text("superman", os.path.join(symlinked_dir.name, f3))
        # create the symlink to the folder
        os.symlink(symlinked_dir.name, os.path.join(source.name, symlinked_dir_basename))

        copy_directory(source.name, destination.name)

        # all files are copied
        self.assertTrue(os.path.exists(os.path.join(destination.name, f1)))
        self.assertTrue(os.path.exists(os.path.join(destination.name, f2)))
        self.assertTrue(os.path.exists(os.path.join(destination.name, symlinked_dir_basename, f3)))

        # existing f2 file is ovewritten
        self.assertEqual("mouse", read_text(os.path.join(destination.name, f2)))

        # symbolic link is followed
        copied_symlinked_folder = os.path.join(destination.name, symlinked_dir_basename)
        self.assertFalse(os.path.islink(copied_symlinked_folder))
        self.assertTrue(os.path.exists(os.path.join(copied_symlinked_folder, f3)))

        # missing destination directory is created
        with tempfile.TemporaryDirectory() as temp:
            destination_missing = os.path.join(temp, "subfolder")
            copy_directory(source.name, destination_missing)
            self.assertTrue(os.path.exists(destination_missing))
