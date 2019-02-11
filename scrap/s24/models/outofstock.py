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

import numpy as np


from analitico.utilities import timestamp_diff_secs, time_ms, get_dict_dot, logger

from rest_framework.exceptions import APIException

from s24.categories import s24_get_category_id, s24_get_category_name, s24_get_category_slug


import multiprocessing
from joblib import Parallel, delayed


class OutOfStockModel(analitico.models.TabularClassifierModel):
    """
    This project is split into two parts. The first creates a model which can predict
    the distance in seconds between items of different categories in a variety of supermarkets
    based on actual shopping times. The second part takes a shopping list and, using the
    model to predict distances between items, sorts the shopping list in the manner which 
    will be quicker to shop using a travelling salesman approach.
    """

    def __init__(self, settings):
        super().__init__(settings)
        logger.info("OutOfStockModel - project_id: %s" % self.project_id)

    # experimental, call to callable didn't work for some reason
    def parallel_df(self, df: pd.DataFrame, call: callable):
        chunk_size = 5000
        chunk_dfs = [df[i : i + chunk_size].copy() for i in range(0, df.shape[0], chunk_size)]

        results = Parallel(n_jobs=multiprocessing.cpu_count())(delayed(call)(chunk_df) for chunk_df in chunk_dfs)

        df_joined = None
        for df_result in results:
            df_joined = df_joined.append(df_result) if df_joined else df_result

        return df_joined

    #
    # training
    #

    def _get_price(self, row):
        try:
            return float(row["odt_price"]) if int(row["odt_variable_weight"]) == 0 else float(row["odt_price_per_type"])
        except Exception as _:
            logger.error(str(row) + " cannot calculate price")
            return None

    def _get_price_promo(self, row):
        try:
            return (row["dyn_price"] + row["odt_surcharge_fixed"]) / row["dyn_price"]
        except ZeroDivisionError:
            return 1

    def _get_category_id(self, row, level):
        try:
            if not pd.isnull(row["odt_category_id"]):
                return s24_get_category_id(int(row["odt_category_id"]), level)
        except TypeError:
            pass
        return None

    def _get_category_slug(self, row, level):
        try:
            if not pd.isna(row["odt_category_id"]):
                return s24_get_category_slug(int(row["odt_category_id"]), level)
        except TypeError:
            pass
        return None

    def _aggregate_find_rate(self, group, min_count=5):
        f1 = {"dyn_purchased": ["sum", "count", "mean"]}
        group = group.agg(f1)
        # group = group.sort_values(('dyn_purchased', 'sum'), ascending=False)
        # group = group[group[('dyn_purchased', 'sum')] > min_count] # minimum number of purchased
        return pd.DataFrame(group)

    def preprocess_data(self, df, training=False, results=None):
        """ Remove outliers and sort dataset before it's used for training or just calculate dynamic fields before inference """
        logger.info("OutOfStock.preprocess_data - %d records (before)", len(df))
        df.set_index(keys="odt_id", inplace=True, verify_integrity=True)

        if training:
            # remove rows without odt_category_id
            if df["odt_category_id"].isnull().sum() > 0:
                logger.warning(
                    "OutOfStock.preprocess_data - %d records with null 'odt_category_id'",
                    df["odt_category_id"].isna().sum(),
                )
                df = df.dropna(subset=["odt_category_id"])
            # remove rows without odt_touched_at
            if df["odt_touched_at"].isnull().sum() > 0:
                logger.warning(
                    "OutOfStock.preprocess_data - %d records with null 'odt_touched_at'",
                    df["odt_touched_at"].isnull().sum(),
                )
                df = df.dropna(subset=["odt_touched_at"])
            # remove rows without odt_ean
            if df["odt_ean"].isnull().sum() > 0:
                logger.warning(
                    "OutOfStock.preprocess_data - %d records with null 'odt_ean'", df["odt_ean"].isnull().sum()
                )
                df = df.dropna(subset=["odt_ean"])

        # disable warning on chained assignments below...
        # https://stackoverflow.com/questions/20625582/how-to-deal-with-settingwithcopywarning-in-pandas
        pd.options.mode.chained_assignment = None

        # expand product categories to 3 levels: main, sub and category
        df["dyn_main_category_id"] = df.apply(lambda row: self._get_category_id(row, 0), axis=1)
        df["dyn_sub_category_id"] = df.apply(lambda row: self._get_category_id(row, 1), axis=1)
        df["dyn_category_id"] = df.apply(lambda row: self._get_category_id(row, 2), axis=1)

        # create time series
        if training:
            df["dyn_purchased"] = df.apply(lambda row: 1 if row["odt_status"] == "PURCHASED" else 0, axis=1)

            fr_by_ean = self._aggregate_find_rate(df.groupby(["odt_ean"]))
            fr_by_category_id = self._aggregate_find_rate(df.groupby(["dyn_category_id"]))
            fr_by_store_id = self._aggregate_find_rate(df.groupby(["store_id"]))

            df["dyn_findrate_by_ean"] = df.apply(
                lambda row: float(fr_by_ean.loc[[row["odt_ean"]], ("dyn_purchased", "mean")]), axis=1
            )
            df["dyn_findrate_by_category_id"] = df.apply(
                lambda row: float(fr_by_category_id.loc[[row["dyn_category_id"]], ("dyn_purchased", "mean")]), axis=1
            )
            df["dyn_findrate_by_store_id"] = df.apply(
                lambda row: float(fr_by_ean.loc[[row["store_id"]], ("dyn_purchased", "mean")]), axis=1
            )

        # df['dyn_category_slug'] = df.apply(lambda row: self._get_category_slug(row, 0), axis=1)
        # df['dyn_sub_category_slug'] = df.apply(lambda row: self._get_category_slug(row, 1), axis=1)
        # df['dyn_category_slug'] = df.apply(lambda row: self._get_category_slug(row, 2), axis=1)

        # prezzo considerando price se variable_weight è zero oppure price_per_type se variable_weight è 1
        # sql: ((price*(1-variable_weight))+(variable_weight*price_per_type)) item_price,
        df["dyn_price"] = df.apply(lambda row: self._get_price(row), axis=1)

        # il prezzo corrente rispetto al prezzo pieno in percentuale (0-1)
        # sql: ((((price*(1-variable_weight))+(variable_weight*price_per_type)) + surcharge_fixed) / ((price*(1-variable_weight))+(variable_weight*price_per_type))) 'item_promo',
        df["dyn_price_promo"] = df.apply(lambda row: self._get_price_promo(row), axis=1)

        if training:
            # there are four classes in the original status, turn them to just two bought or not
            df["dyn_purchased"] = df.apply(
                lambda row: "PURCHASED" if row["odt_status"] == "PURCHASED" else "NOT_PURCHASED", axis=1
            )

        logger.info("OutOfStock.preprocess_data - %d records (after)", len(df))
        # superclass will apply categorical types, augment timestamps, etc
        return super().preprocess_data(df, training, results)
