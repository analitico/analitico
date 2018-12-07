
from django.test import TestCase

from s24.categories import s24_get_category, s24_get_category_id, s24_get_category_slug

class TestSupermercatoCategories(TestCase):

    def test_get_category(self):
        # Pelati e Passate
        id, name, slug = s24_get_category(100160) 
        self.assertEqual(id, 27)
        self.assertEqual(name, 'Sughi, Scatolame, Condimenti')
        self.assertEqual(slug, 'sughi-scatolame-condimenti')
        # Olio e Aceto
        id, name, slug = s24_get_category(6158) 
        self.assertEqual(id, 55)
        self.assertEqual(name, 'Condimenti e sottoli')
        self.assertEqual(slug, 'sdm-condimenti-sottoli')


    def test_get_category_slug(self):
        slug = s24_get_category_slug(100160) 
        self.assertEqual(slug, 'sughi-scatolame-condimenti')
        slug = s24_get_category_slug(6158) 
        self.assertEqual(slug, 'sdm-condimenti-sottoli')


    def test_get_category_levels(self):
        # Antipasti/main
        id, name, slug = s24_get_category(6123, 0) 
        self.assertEqual(id, 48)
        self.assertEqual(name, 'Piatti pronti')
        self.assertEqual(slug, 'sdm-piatti-pronti')
        # Antipasti/sub
        id, name, slug = s24_get_category(6123, 1) 
        self.assertEqual(id, 100532)
        self.assertEqual(name, 'Antipasti')
        self.assertEqual(slug, '2-sdm-antipasti')
        # Antipasti/2
        id, name, slug = s24_get_category(6123, 2) 
        self.assertEqual(id, 6123)
        self.assertEqual(name, 'Antipasti')
        self.assertEqual(slug, '3-sdm-antipasti')


    def test_get_main_category_id(self):
        # Pelati e Passate
        id = s24_get_category_id(100160) 
        self.assertEqual(id, 27)
        # Olio e Aceto
        id = s24_get_category_id(6158) 
        self.assertEqual(id, 55)
        # Vitamine e minerali
        id = s24_get_category_id(564) 
        self.assertEqual(id, 13)
        # Gin e Vodka
        id = s24_get_category_id(810) 
        self.assertEqual(id, 16)


    def test_get_sub_category_id(self):
        # Pelati e Passate
        id = s24_get_category_id(100160, 1) 
        self.assertEqual(id, 100160)
        # Olio e Aceto
        id = s24_get_category_id(6158, 1) 
        self.assertEqual(id, 100576)
        # Vitamine e minerali
        id = s24_get_category_id(564, 1) 
        self.assertEqual(id, 100172)
        # Gin e Vodka
        id = s24_get_category_id(810, 1) 
        self.assertEqual(id, 100195)
        
    def test_get_category_missing_depth(self):
        category_id = s24_get_category_id(20, 1) # 20 is itself a main category
        self.assertIsNone(category_id)

        
    def test_get_category_missing_id(self):
        category_id = s24_get_category_id(-20) # -20 is not a valid id
        self.assertIsNone(category_id)
