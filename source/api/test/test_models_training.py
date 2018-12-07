
from django.test import TestCase

from django.core.validators import validate_slug
from api.models.training import generate_training_id


class TestApiModelsTraining(TestCase):

    def test_generate_training_id(self):
        self.assertEqual(generate_training_id()[:4], 'trn_')
        self.assertEqual(len(generate_training_id()), 16)

    def test_generate_training_id_valid_slug(self):
        # will raise an exception if not a valid slug
        validate_slug(generate_training_id()) 
