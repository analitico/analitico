# Helper methods to retrieve information on s24 product categories.
# Copyright (C) 2018 by Analitco.ai. All rights reserved.

import unittest
import pandas as pd

from analitico.train import time_ms
from analitico.storage import storage_open

# csv file with category table from s24 database
CATEGORY_CSV_PATH = 'assets/s24/category.csv'

##
## PRIVATE METHODS
##

# mapping is lazy loaded if needed
_categories = None

def _get_category(df, category_id: int, depth=0) -> (int, str, str):
    """ Returns category_id, name and slug for the parent of the given category_id at the requested level (0/main, 1/sub or 2) """
    row = df[df['id'] == category_id]
    if not row.empty:
        if row['depth'].item() > depth:
            return _get_category(df, row['parent_id'].item(), depth)
        if row['depth'].item() == depth:
            return (int(category_id), str(row['name'].item()), str(row['slug'].item()))
    return None

def _prepare():
    """ Prepares full table of categories and their first and second level corresponding items """
    global _categories
    if _categories is None:
        started_on = time_ms()

        # load categories table and keep cached will read
        # categories.csv from local file system or google cloud storage
        with storage_open(CATEGORY_CSV_PATH) as categories_file:
            df = pd.read_csv(categories_file)
        df.set_index('id')

        _categories = { 
            id: [_get_category(df, id, 0), _get_category(df, id, 1), _get_category(df, id, 2)] for id in df['id']
            }
        print("s24.categories: loaded in %d ms" % time_ms(started_on))

##
## PUBLIC METHODS
##

def s24_get_category(id: int, depth=0) -> (id, str, str):
    """ Returns (id, name, slug) of the category at given depth (0-main, 1-sub, 2-category) """
    _prepare()
    try: return _categories[id][depth] 
    except: return None

def s24_get_category_id(id: int, depth=0) -> int:
    """ Returns the id of the category at given depth (0-main, 1-sub, 2-category) """
    _prepare()
    try: return _categories[id][depth][0] 
    except: return None

def s24_get_category_name(id: int, depth=0) -> str:
    """ Returns the name of the category at given depth (0-main, 1-sub, 2-category) """
    _prepare()
    try: return _categories[id][depth][1] 
    except: return None

def s24_get_category_slug(id: int, depth=0) -> str:
    """ Returns the url slug of the category at given depth (0-main, 1-sub, 2-category) """
    _prepare()
    try: return _categories[id][depth][2] 
    except: return None
