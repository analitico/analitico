# Helper methods to retrieve information on s24 product categories.
# Copyright (C) 2018 by Analitco.ai. All rights reserved.

import unittest
import pandas as pd

from analitico.storage import download_file
from analitico.utilities import save_json, time_ms, logger

# csv file with category table from s24 database
CATEGORY_CSV_URL = "https://storage.googleapis.com/data.analitico.ai/data/s24/training/category.csv"

##
## PRIVATE METHODS
##

# mapping is lazy loaded if needed
_categories = None


def _prepare():
    """ Prepares full table of categories and their first and second level corresponding items """
    started_on = time_ms()
    global _categories
    if _categories is None:
        # load categories table and keep cached will read
        # categories.csv from local file system or google cloud storage
        categories_filename = download_file(CATEGORY_CSV_URL)
        df = pd.read_csv(categories_filename)
        df.set_index("id")

        _categories = {}

        df_0 = df[df["depth"] == 0]
        for row in df_0[["id", "name", "slug"]].values:
            _categories[row[0]] = [row.tolist(), None, None]

        df_1 = df[df["depth"] == 1]
        for row in df_1[["id", "name", "slug", "parent_id"]].values:
            l0_row = _categories[row[3]][0] if row[3] in _categories else None
            _categories[row[0]] = [l0_row, row.tolist(), None]

        df_2 = df[df["depth"] == 2]
        for row in df_2[["id", "name", "slug", "parent_id"]].values:
            l1_row = _categories[row[3]][1] if row[3] in _categories else None
            l0_row = _categories[l1_row[3]][0] if l1_row is not None and (l1_row[3] in _categories) else None
            _categories[row[0]] = [l0_row, l1_row, row.tolist()]

        # save results as json for debugging
        if time_ms(started_on) > 500:
            logger.warning("s24.categories - loaded in %d ms", time_ms(started_on))


##
## PUBLIC METHODS
##


def s24_get_category(id: int, depth=0) -> (id, str, str):
    """ Returns (id, name, slug) of the category at given depth (0-main, 1-sub, 2-category) """
    _prepare()
    try:
        if id and (id in _categories):
            cat = _categories[id][depth]
            if cat:
                return cat[:3]
    except TypeError:
        pass
    return None


def s24_get_category_id(id: int, depth=0) -> int:
    """ Returns the id of the category at given depth (0-main, 1-sub, 2-category) """
    try:
        cat = s24_get_category(id, depth)
        return cat[0] if cat else None
    except TypeError:
        pass
    return None


def s24_get_category_name(id: int, depth=0) -> str:
    """ Returns the name of the category at given depth (0-main, 1-sub, 2-category) """
    try:
        cat = s24_get_category(id, depth)
        return cat[1] if cat else None
    except TypeError:
        pass
    return None


def s24_get_category_slug(id: int, depth=0) -> str:
    """ Returns the url slug of the category at given depth (0-main, 1-sub, 2-category) """
    try:
        cat = s24_get_category(id, depth)
        return cat[2] if cat else None
    except TypeError:
        pass
    return None
