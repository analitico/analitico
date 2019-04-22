import pandas as pd
import numpy as np

import analitico.utilities
import analitico.schema
import analitico.plugin

import s24.categories
from s24.categories import s24_get_category_id, s24_get_category_slug
from analitico.plugin import IDataframePlugin, plugin
from analitico.utilities import time_ms

##
## AugmentCouriersPlugin - dataframe in, dataframe out with courier information added
##


@plugin
class AugmentCouriersPlugin(IDataframePlugin):
    """ A plugin that takes courier_id and augments it with courier information """

    class Meta(IDataframePlugin.Meta):
        name = "s24.plugin.AugmentCouriersPlugin"
        title = "AugmentCouriersPlugin"
        description = "A plugin that takes courier_id and augments it with courier information"

    def run(self, *args, action=None, **kwargs):
        try:
            df = args[0]

            if not isinstance(df, pd.DataFrame):
                self.factory.exception("AugmentCouriersPlugin: requires a pd.DataFrame as input", plugin=self)
                return args

            if "courier_id" not in df.columns:
                self.factory.warning("AugmentCouriersPlugin: requires 'courier_id' to augment", plugin=self)
                return args

            # check if all columns are there already, for example in prediction requests
            # where caller provides this information to skip this expensive augmentation
            columns = (
                "courier_soldo_enabled",
                "courier_area",
                "courier_orders_taken",
                "courier_orders_sent",
                "courier_created_at",
                "courier_experience_days",
            )
            if all(column in df.columns for column in columns):
                self.factory.warning("AugmentCouriersPlugin: data is already augmented", plugin=self)
                return df

            # remove any columns that may be there
            for column in columns:
                if column in df.columns:
                    df.drop(column, axis=1, inplace=True)

            # TODO if information is already there do not merge
            # eg: during inference caller may choose to populate courier
            # information instead of having this expensive join done at runtime

            # make sure courier_id is a categorical
            df["courier_id"] = df["courier_id"].astype("category")

            # retrieve courier table
            plugin = analitico.plugin.DatasetSourcePlugin(factory=self.factory, dataset_id="ds_s24_courier")
            couriers = plugin.run(action)

            # keep only the information we need to augment
            plugin = analitico.plugin.TransformDataframePlugin(
                factory=self.factory,
                schema={
                    "columns": [
                        {"name": "id", "rename": "courier_id", "index": True, "type": "category"},
                        {"name": "soldo_enabled", "rename": "courier_soldo_enabled", "type": "category"},
                        {"name": "area", "rename": "courier_area", "type": "category"},
                        {"name": "orders_taken", "rename": "courier_orders_taken"},
                        {"name": "orders_sent", "rename": "courier_orders_sent"},
                        {"name": "created_at", "rename": "courier_created_at", "type": "datetime"},
                    ]
                },
            )
            couriers = plugin.run(couriers, action=action)

            # merge with passed dataframe
            df = pd.merge(df, couriers, on="courier_id", how="left")

            # calculate courier experience at the time of the specific order,
            # not as of now. this way the proper experience level is applied to
            # older records instead of having them all seem handled by an experience courier
            if "order_deliver_at_start" in df.columns:
                timestamp = df["order_deliver_at_start"].astype("datetime64[ns]")
            else:
                self.factory.warning(
                    "AugmentCouriersPlugin: need 'order_deliver_at_start' to calculate 'courier_experience_days', using now() instead"
                )
                timestamp = pd.Timestamp.now()

            # couriers not found or with no starting date will be marked as if starting right now
            df["courier_soldo_enabled"].fillna(0, inplace=True)
            df["courier_orders_taken"].fillna(0, inplace=True)
            df["courier_orders_sent"].fillna(0, inplace=True)
            df["courier_created_at"].fillna(pd.Timestamp.now(), inplace=True)

            df["courier_experience_days"] = timestamp - df["courier_created_at"]
            df["courier_experience_days"] = df["courier_experience_days"].dt.total_seconds() / (60 * 60 * 24.0)
            df["courier_experience_days"] = df["courier_experience_days"].astype("int")

            # TODO enhancement place newly added columns next to "courier_id"
            if False:
                index = df.columns.get_loc("courier_id")
                columns = list(df.columns)
                print(columns)
                for i, column in enumerate(couriers.columns):
                    columns.pop(i)
                    columns.insert(index + i, column)
                print(columns)
                df = df[columns]

            return df

        except Exception:
            self.factory.exception("AugmentCouriersPlugin - an error occoured while augmenting couriers")
