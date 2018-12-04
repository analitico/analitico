
# Predict if an item may be out of stock
# Copyright (C) 2018 by Analitco.ai
# All rights reserved.

import os
import sys
import json

import pandas as pd
import catboost

import analitico.models
import analitico.utilities
import analitico.storage

from analitico.utilities import timestamp_diff_secs, time_ms, get_dict_dot, logger

from rest_framework.exceptions import APIException

from s24.categories import s24_get_category_id, s24_get_category_name, s24_get_category_slug


class OutOfStockModel(analitico.models.TabularClassifierModel):
    """
    This project is split into two parts. The first creates a model which can predict
    the distance in seconds between items of different categories in a variety of supermarkets
    based on actual shopping times. The second part takes a shopping list and, using the
    model to predict distances between items, sorts the shopping list in the manner which 
    will be quicker to shop using a travelling salesman approach.
    """

    #
    # training
    #

    def _get_price(self, row):
        try:
            return float(row['odt_price']) if int(row['odt_variable_weight']) == 0 else float(row['odt_price_per_type'])
        except Exception as _:
            logger.error(str(row) + ' cannot calculate price')
            return None


    def _get_price_promo(self, row):
        return (row['dyn_price'] + row['odt_surcharge_fixed']) / row['dyn_price']


    def _train_preprocess_records(self, df):
        """ Remove outliers and sort dataset before it's used for training """
        df = super()._train_preprocess_records(df)

        df.set_index(keys='odt_id', inplace=True, verify_integrity=True)

        # remove rows without an item's category
        df = df.dropna(subset=['odt_category_id'])
        df = df.dropna(subset=['odt_touched_at'])

        # disable warning on chained assignments below...
        # https://stackoverflow.com/questions/20625582/how-to-deal-with-settingwithcopywarning-in-pandas
        pd.options.mode.chained_assignment = None

        # expand product categories to 3 levels: main, sub and category
        df['dyn_main_category_id'] = df.apply(lambda row: s24_get_category_id(int(row['odt_category_id']), 0), axis=1) 
        df['dyn_sub_category_id'] = df.apply(lambda row: s24_get_category_id(int(row['odt_category_id']), 1), axis=1) 
        df['dyn_category_id'] = df.apply(lambda row: s24_get_category_id(int(row['odt_category_id']), 2), axis=1) 

        if self.debug:
            df['dyn_category_slug'] = df.apply(lambda row: s24_get_category_slug(int(row['odt_category_id']), 0), axis=1) 
            df['dyn_sub_category_slug'] = df.apply(lambda row: s24_get_category_slug(int(row['odt_category_id']), 1), axis=1) 
            df['dyn_category_slug'] = df.apply(lambda row: s24_get_category_slug(int(row['odt_category_id']), 2), axis=1) 

	    # prezzo considerando price se variable_weight è zero oppure price_per_type se variable_weight è 1
	    # sql: ((price*(1-variable_weight))+(variable_weight*price_per_type)) item_price, 
        df['dyn_price'] = df.apply(lambda row: self._get_price(row), axis=1)

        # il prezzo corrente rispetto al prezzo pieno in percentuale (0-1) 
	    # sql: ((((price*(1-variable_weight))+(variable_weight*price_per_type)) + surcharge_fixed) / ((price*(1-variable_weight))+(variable_weight*price_per_type))) 'item_promo', 
        df['dyn_price_promo'] = df.apply(lambda row: self._get_price_promo(row), axis=1)

        # remove items that are outliers in terms of time elapsed        
        #df = df[df['elapsed_sec'] < 8 * 60]
        
        # for now we will treat this problem as a regression issue, later as a classification
        df['dyn_purchased'] = df.apply(lambda row: 1 if row['odt_status'] == 'PURCHASED' else 0, axis=1) 

        if self.debug:
            df.to_csv('~/out-of-stock-augmented.csv')

        # if we remove items where the courier had to replace item or
        # call the customer we get a higher score. however, if we leave
        # this field in we have more records. also, the system learns to
        # differentiate elapsed time based on status and we will only place
        # predictions for status == PURCHASED which are easier to predict
        #
        # df = df[df['status'] == 'PURCHASED']
        return df
