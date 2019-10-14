import unittest

import analitico.mixin


class MyClass1(analitico.mixin.AttributeMixin):
    """ Class has no __init__ method """

    pass


class MyClass2(analitico.mixin.AttributeMixin):
    """ Class with passthrough init method """

    mickey = "empty"

    def __init__(self, mickey, *args, **kwargs):
        # here we call super().__init__ correctly and pass down the attributes
        super().__init__(*args, **kwargs)
        self.mickey = mickey


class MyClass3(analitico.mixin.AttributeMixin):
    """ Class with no passthrough init method """

    mickey = "empty"

    def __init__(self, mickey, **kwargs):
        # here we don't call super().__init__ and loose all attributes but mickey's
        self.mickey = mickey


class AttributesMixinTests(unittest.TestCase):
    """ Unit testing for mixin classes """

    def test_mixin_attributes(self):
        """ Basic basic functionality of AttributeMixin """
        obj1 = MyClass1(mickey="smart", goofy="funny", minnie="cute")

        self.assertEqual(obj1.mickey, "smart")
        self.assertEqual(obj1.goofy, "funny")
        self.assertEqual(obj1.minnie, "cute")

    def test_mixin_attributes_missing_attribute(self):
        """ Basic missing attribute in AttributeMixin """
        obj1 = MyClass1(mickey="smart", goofy="funny", minnie="cute")

        with self.assertRaises(AttributeError):
            obj1.pinocchio

    def test_mixin_attributes_init_passthrough(self):
        """ Basic passthrough initialization of AttributeMixin """
        obj1 = MyClass2(mickey="smart", goofy="funny", minnie="cute")

        self.assertEqual(obj1.mickey, "smart")
        self.assertEqual(obj1.goofy, "funny")
        self.assertEqual(obj1.minnie, "cute")

        # bogus attribute not defined
        with self.assertRaises(AttributeError):
            obj1.pinocchio

    def test_mixin_attributes_init_no_passthrough(self):
        """ Basic passthrough initialization of AttributeMixin """
        obj1 = MyClass3(mickey="smart", goofy="funny", minnie="cute")
        self.assertEqual(obj1.mickey, "smart")

        # no super().__init__ so these are not defined
        with self.assertRaises(AttributeError):
            self.assertEqual(obj1.goofy, "funny")
        with self.assertRaises(AttributeError):
            self.assertEqual(obj1.minnie, "cute")

        # bogus attribute also not defined
        with self.assertRaises(AttributeError):
            obj1.pinocchio
