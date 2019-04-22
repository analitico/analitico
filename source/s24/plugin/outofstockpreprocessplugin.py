import pandas as pd
import numpy as np
import os.path

import analitico.pandas
from analitico.constants import ACTION_TRAIN
from analitico.utilities import time_ms
from analitico.plugin import IDataframePlugin, plugin

##
## OutOfStockPreprocessPlugin
##


@plugin
class OutOfStockPreprocessPlugin(IDataframePlugin):
    """ Cleanup rows that are not useful for outofstock model training """

    class Meta(IDataframePlugin.Meta):
        name = "s24.plugin.OutOfStockPreprocessPlugin"

    #
    # training
    #

    def aggregate_find_rate(self, group, min_count=10):
        f1 = {"dyn_purchased": ["sum", "count", "mean"]}
        group = group.agg(f1)
        # group = group.sort_values(('dyn_purchased', 'sum'), ascending=False)
        # group = group[group[('dyn_purchased', 'sum')] > min_count] # minimum number of purchased
        return pd.DataFrame(group)

    def run(self, *args, action=None, **kwargs) -> pd.DataFrame:
        try:
            df = args[0]
            if not isinstance(df, pd.DataFrame):
                self.exception("Input must be a DataFrame")
            if len(df.index) < 1:
                self.warning("Input dataframe is empty, why?")
                return df

            # debug
            # df.to_csv(os.path.expanduser("~/Downloads/outofstock-before.csv"))

            # are we training or predicting?
            training = ACTION_TRAIN in action

            # should already be index
            # df.set_index(keys="odt_id", inplace=True, verify_integrity=True)

            # disable warning on chained assignments below...
            # https://stackoverflow.com/questions/20625582/how-to-deal-with-settingwithcopywarning-in-pandas
            pd.options.mode.chained_assignment = None

            if training:
                # odt_status == NEW is a manual entry row and should be dropped
                self.drop_selected_rows(df, df[df.odt_status == "NEW"], "odt_status == NEW")

                # remove rows with null values
                self.drop_na_rows(df, "odt_category_id")
                self.drop_na_rows(df, "odt_touched_at.day")
                self.drop_na_rows(df, "odt_ean")
                self.drop_na_rows(df, "sto_name")

                if False:  # add these later
                    # create time series
                    df["dyn_purchased"] = df["odt_status"].map(lambda status: 1 if status == "PURCHASED" else 0)
                    self.info("Added 'dyn_purchased' as classification label")

                    fr_by_ean = self.aggregate_find_rate(df.groupby(["odt_ean"]))
                    fr_by_category_id = self.aggregate_find_rate(df.groupby(["odt_category_id.level2"]))
                    fr_by_store_id = self.aggregate_find_rate(df.groupby(["sto_ref_id"]))

                    df["dyn_findrate_by_ean"] = df.apply(
                        lambda row: float(fr_by_ean.loc[[row["odt_ean"]], ("dyn_purchased", "mean")]), axis=1
                    )
                    self.info("Added 'dyn_findrate_by_ean'")
                    df["dyn_findrate_by_category_id"] = df.apply(
                        lambda row: float(
                            fr_by_category_id.loc[[row["odt_category_id.level2"]], ("dyn_purchased", "mean")]
                        ),
                        axis=1,
                    )
                    self.info("Added 'dyn_findrate_by_category_id'")
                    df["dyn_findrate_by_store_id"] = df.apply(
                        lambda row: float(fr_by_store_id.loc[[row["sto_ref_id"]], ("dyn_purchased", "mean")]), axis=1
                    )
                    self.info("Added 'dyn_findrate_by_store_id'")

            # prezzo considerando price se variable_weight è zero oppure price_per_type se variable_weight è 1
            # sql: ((price*(1-variable_weight))+(variable_weight*price_per_type)) item_price,
            # the performance difference betweem adding two vectors as its done below
            # and doing a pandas.apply that calls a method (as we were doing before) is 5000x in performance
            price_on = time_ms()
            df["dyn_price"] = np.nan
            df.loc[df["odt_variable_weight"] == 0, "dyn_price"] = df.loc[df["odt_variable_weight"] == 0, "odt_price"]
            df.loc[df["odt_variable_weight"] != 0, "dyn_price"] = df.loc[
                df["odt_variable_weight"] != 0, "odt_price_per_type"
            ]
            self.info("Added 'dyn_price2' with calculated price in %d ms", time_ms(price_on))

            # il prezzo corrente rispetto al prezzo pieno in percentuale (0-1)
            # sql: ((((price*(1-variable_weight))+(variable_weight*price_per_type)) + surcharge_fixed) / ((price*(1-variable_weight))+(variable_weight*price_per_type))) 'item_promo',
            price_on = time_ms()
            df["dyn_price_promo"] = np.nan
            df["dyn_price_promo"] = (df["dyn_price"] + df["odt_surcharge_fixed"]) / df["dyn_price"]
            self.info("Added 'dyn_price_promo2' with calculated price in %d ms", time_ms(price_on))

            # mark categoricals
            df["odt_ean"] = df["odt_ean"].astype("str", copy=False).astype("category", copy=False)

            df["odt_replaceable"].replace(np.nan, 0, regex=True, inplace=True)
            df["odt_replaceable"] = df["odt_replaceable"].astype("int", copy=False).astype("category", copy=False)
            df["odt_variable_weight"].replace(np.nan, 0, regex=True, inplace=True)
            df["odt_variable_weight"] = (
                df["odt_variable_weight"].astype("int", copy=False).astype("category", copy=False)
            )

            df["sto_name"] = df["sto_name"].astype("category", copy=False)
            df["sto_area"] = df["sto_area"].astype("category", copy=False)
            df["sto_province"] = df["sto_province"].astype("category", copy=False)

            df["sto_ref_id"].replace(np.nan, 0, regex=True, inplace=True)
            df["sto_ref_id"] = df["sto_ref_id"].astype("int", copy=False).astype("category", copy=False)

            self.info("Marked categoricals")

            if training:
                # there are four classes in the original status, turn them to just two bought or not
                df["dyn_purchased"] = "PURCHASED"
                df.loc[df["odt_status"] != "PURCHASED", "dyn_purchased"] = "NOT_PURCHASED"
                df["dyn_purchased"] = df["dyn_purchased"].astype("category")

                # move y to last
                # df = df[[list(df.columns.values).pop("dyn_purchased") + "dyn_purchased"]]
                # self.info("Moved label column to end")

                # remove order id and store id (not store reference id which is the real index)
                analitico.pandas.pd_drop_column(df, "ord_id", inplace=True)
                analitico.pandas.pd_drop_column(df, "sto_id", inplace=True)

                # debug
                # df.sample(n=1000).to_csv(os.path.expanduser("~/Downloads/outofstock-after.csv"))

            return df

        except Exception as exc:
            self.exception("Error while processing", exception=exc)
