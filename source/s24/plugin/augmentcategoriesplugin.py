import pandas as pd
import numpy as np

import analitico.utilities
import analitico.schema

import s24.categories
from s24.categories import s24_get_category_id, s24_get_category_slug
from analitico.plugin import IDataframePlugin, plugin
from analitico.utilities import time_ms

##
## AugmentCategoriesPlugin - dataframe in, dataframe out with product category in 3 levels
##


@plugin
class AugmentCategoriesPlugin(IDataframePlugin):
    """ A plugin that takes category_id and augments it to level 1, 2 and 3 categories """

    class Meta(IDataframePlugin.Meta):
        name = "s24.plugin.AugmentCategoriesPlugin"
        title = "AugmentCategoriesPlugin"
        description = "A plugin that takes category_id and augments it to level 1, 2 and 3 categories"
        configurations = [
            {
                "name": "schema",
                "type": "analitico/schema",
                "optional": True,
                "description": "A schema can be passed to indicate which columns should be augmented. If no schema is passed, the plugin will augment the category_id or odt_category_id columns.",
            }
        ]

    def as_category(self, df):
        df.replace(np.nan, 0, regex=True, inplace=True)
        df = df.astype("int", copy=False)
        df = df.astype("category", copy=False)
        return df

    def run(self, *args, action=None, **kwargs):
        try:
            df = args[0]
            if not isinstance(df, pd.DataFrame):
                self.factory.exception("AugmentCategoriesPlugin requires a pd.DataFrame as input", plugin=self)

            columns = self.get_attribute("schema.columns", None)
            category_id_col = columns[0]["name"] if columns and len(columns) > 0 else None
            if not category_id_col:
                if "category_id" in df.columns:
                    category_id_col = "category_id"
                if "odt_category_id" in df.columns:
                    category_id_col = "odt_category_id"

            # disable warning on chained assignments below...
            # https://stackoverflow.com/questions/20625582/how-to-deal-with-settingwithcopywarning-in-pandas
            # pd.options.mode.chained_assignment = None

            if not category_id_col:
                self.warning("A 'category_id' column was not specified, plugin will not augment categories.")
                return df
            if category_id_col not in df.columns:
                self.warning("A '%s' column was not found in the input dataset, plugin will not augment categories.")
                return df

            # warn of rows w/o category
            na_records = df[category_id_col].isnull().sum()
            if na_records > 0:
                self.warning("%d records with null '%s' (out of %d)", na_records, category_id_col, len(df))

            # add columns right after the column being augmented
            loc = df.columns.get_loc(category_id_col)

            # make column categorical
            df_level1 = df[category_id_col]
            df[category_id_col] = self.as_category(df[category_id_col])

            # expand product categories to 3 levels: main, sub and category
            started_on = time_ms()
            df_level2 = self.as_category(df_level1.map(s24.categories.s24_get_category_id_level2))
            df.insert(loc + 1, category_id_col + ".level2", df_level2)
            df_level3 = self.as_category(df_level1.map(s24.categories.s24_get_category_id_level3))
            df.insert(loc + 2, category_id_col + ".level3", df_level3)
            self.info("Augmented '%s' with levels in %d ms", category_id_col, time_ms(started_on))

            if False:
                # expand product category slugs (humn readable) to 3 levels: main, sub and category
                started_on = time_ms()
                df_slug1 = df_level1.map(s24.categories.s24_get_category_slug_level1).astype("category")
                df.insert(loc + 4, category_id_col + ".slug", df_slug1)
                df_slug2 = df_level1.map(s24.categories.s24_get_category_slug_level2).astype("category")
                df.insert(loc + 5, category_id_col + ".slug.level2", df_slug2)
                df_slug3 = df_level1.map(s24.categories.s24_get_category_slug_level3).astype("category")
                df.insert(loc + 6, category_id_col + ".slug.level3", df_slug3)
                self.info("Augmented '%s' with slugs in %d ms", category_id_col, time_ms(started_on))

            return df

        except Exception as exc:
            self.error("AugmentCategoriesPlugin - an error occoured while augmenting columns", exc)
            raise exc
