import unittest
import os
import sys

import analitico.mixin


class MyClass1(analitico.mixin.SettingsMixin):
    """ Class has no __init__ method """

    pass


class MyClass2(analitico.mixin.SettingsMixin):
    """ Class with passthrough init method """

    mickey = "empty"

    def __init__(self, mickey, *args, **kwargs):
        # here we call super().__init__ correctly and pass down the settings
        super().__init__(*args, **kwargs)
        self.mickey = mickey


class MyClass3(analitico.mixin.SettingsMixin):
    """ Class with no passthrough init method """

    mickey = "empty"

    def __init__(self, mickey, *args, **kwargs):
        # here we don't call super().__init__ and loose all settings but mickey's
        self.mickey = mickey


class MixinTests(unittest.TestCase):
    """ Unit testing for mixin classes """

    def test_mixin_settings(self):
        """ Basic basic functionality of SettingsMixin """
        obj1 = MyClass1(mickey="smart", goofy="funny", minnie="cute")

        self.assertEqual(obj1.mickey, "smart")
        self.assertEqual(obj1.goofy, "funny")
        self.assertEqual(obj1.minnie, "cute")

    def test_mixin_settings_missing_attribute(self):
        """ Basic missing setting in SettingsMixin """
        obj1 = MyClass1(mickey="smart", goofy="funny", minnie="cute")

        with self.assertRaises(AttributeError):
            var1 = obj1.pinocchio

    def test_mixin_settings_init_passthrough(self):
        """ Basic passthrough initialization of SettingsMixin """
        obj1 = MyClass2(mickey="smart", goofy="funny", minnie="cute")

        self.assertEqual(obj1.mickey, "smart")
        self.assertEqual(obj1.goofy, "funny")
        self.assertEqual(obj1.minnie, "cute")

        # bogus setting not defined
        with self.assertRaises(AttributeError):
            var1 = obj1.pinocchio

    def test_mixin_settings_init_no_passthrough(self):
        """ Basic passthrough initialization of SettingsMixin """
        obj1 = MyClass3(mickey="smart", goofy="funny", minnie="cute")
        self.assertEqual(obj1.mickey, "smart")

        # no super().__init__ so these are not defined
        with self.assertRaises(AttributeError):
            self.assertEqual(obj1.goofy, "funny")
        with self.assertRaises(AttributeError):
            self.assertEqual(obj1.minnie, "cute")

        # bogus setting also not defined
        with self.assertRaises(AttributeError):
            var1 = obj1.pinocchio
