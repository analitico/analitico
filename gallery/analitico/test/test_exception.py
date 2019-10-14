import unittest
import os.path
import pandas as pd
import random
import string
import pytest

from analitico import AnaliticoException
from analitico.factory import Factory
from analitico.schema import generate_schema

from .test_mixin import TestMixin

# pylint: disable=no-member


@pytest.mark.django_db
class ExceptionTests(unittest.TestCase, TestMixin):
    """ Unit testing of AnaliticoException """

    def test_exception_basics(self):
        try:
            raise AnaliticoException("A problem", item_id="it_001", extra={"recipe_id": "rx_002"})
        except AnaliticoException as e:
            self.assertEqual(e.message, "A problem")
            self.assertEqual(e.extra["item_id"], "it_001")
            self.assertEqual(e.extra["recipe_id"], "rx_002")

    def test_exception_formatting(self):
        try:
            raise AnaliticoException("A problem %d", 1, item_id="it_001", extra={"recipe_id": "rx_002"})
        except AnaliticoException as e:
            self.assertEqual(e.message, "A problem 1")
            self.assertEqual(e.extra["item_id"], "it_001")
            self.assertEqual(e.extra["recipe_id"], "rx_002")

    def test_exception_formatting_multiple(self):
        try:
            raise AnaliticoException("A problem %d with %s", 1, "this", item_id="it_001", extra={"recipe_id": "rx_002"})
        except AnaliticoException as e:
            self.assertEqual(e.message, "A problem 1 with this")

    def test_exception_with_inner(self):
        try:
            try:
                raise AnaliticoException("Inner exception %d", 1, item_id="it_001", extra={"recipe_id": "rx_002"})
            except AnaliticoException as e1:
                self.assertEqual(e1.message, "Inner exception 1")
                self.assertEqual(e1.extra["item_id"], "it_001")
                self.assertEqual(e1.extra["recipe_id"], "rx_002")
                raise AnaliticoException("Outer exception %d", 2, test_id="tx001") from e1
        except AnaliticoException as e2:
            self.assertEqual(e2.message, "Outer exception 2")
            print(e2)
