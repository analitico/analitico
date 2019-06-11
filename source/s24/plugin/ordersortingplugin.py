import pandas as pd
import os.path
import os
import json
import collections
import copy

from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2
from analitico.utilities import time_ms

import analitico.plugin
import analitico.pandas
from analitico import AnaliticoException
from analitico.pandas import pd_drop_column
from analitico import AnaliticoException
from analitico.plugin import plugin
from analitico.utilities import save_json
import s24.categories

##
## OrderSortingPlugin
##


@plugin
class OrderSortingPlugin(analitico.plugin.CatBoostRegressorPlugin):
    """
    This project is split into two parts. The first creates a model which can predict
    the distance in seconds between items of different categories in a variety of supermarkets
    based on actual shopping times. The second part takes a shopping list and, using the
    model to predict distances between items, sorts the shopping list in the manner which 
    will be quicker to shop using a travelling salesman approach.
    """

    class Meta(analitico.plugin.CatBoostRegressorPlugin.Meta):
        name = "s24.plugin.OrderSortingPlugin"
        algorithm = "s24/ordersorting"  # custom algorithm

    def preprocess_training_data(self, df):
        """ Augments a given dataframe, returns augmented df """
        try:
            # disable warning on chained assignments below...
            # https://stackoverflow.com/questions/20625582/how-to-deal-with-settingwithcopywarning-in-pandas
            pd.options.mode.chained_assignment = None

            # if we remove items where the courier had to replace item or
            # call the customer we get a higher score. however, if we leave
            # this field in we have more records. also, the system learns to
            # differentiate elapsed time based on status and we will only place
            # predictions for status == PURCHASED which are easier to predict
            #
            # df = df[df['odt_status'] == 'PURCHASED']

            # remove rows without an item's category or touch time
            df = self.drop_na_rows(df, "odt_id")
            df = self.drop_na_rows(df, "odt_ean")
            df = self.drop_na_rows(df, "odt_category_id")
            df = self.drop_na_rows(df, "odt_category_id.level2")
            df = self.drop_na_rows(df, "odt_category_id.level3")
            df = self.drop_na_rows(df, "odt_touched_at")
            df = self.drop_na_rows(df, "sto_ref_id")
            df = self.drop_na_rows(df, "sto_name")

            # order id needs to be float so it can be compared to prev_ord_id and next_ord_id
            # which need to be float since the first and last rows have nan values and int64 does
            # not support nan values
            df = self.drop_na_rows(df, "ord_id")
            df["ord_id"] = df["ord_id"].astype("float64")

            # keep only useful columns, sort by order and time
            # we do not keep the odt_ean which is the specific product but rather
            # try to calculate distance between categories of products
            df = df[
                [
                    "odt_id",
                    "odt_ean",
                    "odt_name",
                    "odt_status",
                    "odt_category_id",
                    "odt_category_id.level2",
                    "odt_category_id.level3",
                    "odt_touched_at",
                    "odt_variable_weight",
                    "odt_replaceable",
                    "ord_id",
                    "sto_ref_id",
                    "sto_name",
                    "sto_area",
                    "sto_province",
                ]
            ]
            df["odt_touched_at"] = df["odt_touched_at"].astype("datetime64[ms]")
            df = df.sort_values(by=["ord_id", "odt_touched_at"], ascending=[True, True])

            # add columns for previous and next order_detail
            df["prev_odt_category_id"] = df["odt_category_id"].shift(1)
            df["prev_odt_category_id.level2"] = df["odt_category_id.level2"].shift(1)
            df["prev_odt_category_id.level3"] = df["odt_category_id.level3"].shift(1)
            df["prev_odt_touched_at"] = df["odt_touched_at"].shift(1)

            # order id is used to understand if item is in the same order
            df["prev_ord_id"] = df["ord_id"].shift(1)
            df["next_ord_id"] = df["ord_id"].shift(-1)

            # select set including only first item in the order
            df1 = df.loc[df["prev_ord_id"] != df["ord_id"]]
            df1["prev_odt_category_id"] = -1
            df1["prev_odt_category_id.level2"] = -1
            df1["prev_odt_category_id.level3"] = -1
            df1["dyn_elapsed_sec"] = 0
            self.info("first item: %d rows", len(df1))

            # select set with items in same order as previous and next
            df2 = df.loc[df["prev_ord_id"] == df["ord_id"]]
            df2["dyn_elapsed_sec"] = df2["odt_touched_at"] - df2["prev_odt_touched_at"]
            df2["dyn_elapsed_sec"] = df2["dyn_elapsed_sec"].dt.total_seconds()
            self.info("middle item: %d rows", len(df2))

            # select set including only last item in the order
            df3 = df.loc[df["ord_id"] != df["next_ord_id"]]
            df3["prev_odt_category_id"] = df3["odt_category_id"]
            df3["prev_odt_category_id.level2"] = df3["odt_category_id.level2"]
            df3["prev_odt_category_id.level3"] = df3["odt_category_id.level3"]
            df3["odt_category_id"] = -2
            df3["odt_category_id.level2"] = -2
            df3["odt_category_id.level3"] = -2
            df3["dyn_elapsed_sec"] = 0
            self.info("last item: %d rows", len(df3))

            # put orders back together
            df_joined = pd.concat([df1, df2, df3])
            df_joined = df_joined.sort_values(by=["ord_id", "odt_touched_at"], ascending=[True, True])

            if True:
                artifacts_path = self.factory.get_artifacts_directory()
                samples_path = os.path.join(artifacts_path, "training-data.csv")
                df_joined.tail(5000).to_csv(samples_path)
                self.info("saved: %s (%d bytes)", samples_path, os.path.getsize(samples_path))

            # create sample data file that can be used to verify prediction model
            samples = []
            sample = None
            for _, row in df_joined.tail(8000).iterrows():
                if int(row["prev_ord_id"]) != int(row["ord_id"]):
                    if sample and len(sample["details"]) > 6:
                        samples.append(sample)
                    sample = collections.OrderedDict(
                        {
                            "ord_id": row["ord_id"],
                            "sto_ref_id": row["sto_ref_id"],
                            "sto_name": row["sto_name"],
                            "sto_area": row["sto_area"],
                            "sto_province": row["sto_province"],
                            "details": [],
                        }
                    )
                if sample:
                    sample["details"].append(
                        {
                            "odt_id": row["odt_id"],
                            "odt_ean": row["odt_ean"],
                            "odt_name": row["odt_name"],
                            "odt_category_id": row["odt_category_id"],
                        }
                    )
            artifacts_path = self.factory.get_artifacts_directory()
            samples_path = os.path.join(artifacts_path, "prediction-samples.json")
            save_json(samples, samples_path)
            self.info("saved: %s (%d bytes)", samples_path, os.path.getsize(samples_path))

            # augment time of day when item is picked into multiple columns
            df_joined = analitico.pandas.augment_dates(df_joined, "odt_touched_at")

            # order numbers and timestamps are not used to develop model
            # df_joined = pd_drop_column(df_joined, "odt_touched_at") # should have been dropped already
            df_joined = pd_drop_column(df_joined, "prev_odt_touched_at")
            df_joined = pd_drop_column(df_joined, "ord_id")
            df_joined = pd_drop_column(df_joined, "prev_ord_id")
            df_joined = pd_drop_column(df_joined, "next_ord_id")

            # remove items that are outliers in terms of time elapsed
            # because most likely these are items where the picker is picking multiple things
            # and them marking them all at once. items were time elapsed is really long are also
            # an indicator that data may be bogus
            quantile = df_joined["dyn_elapsed_sec"].quantile(0.95)
            df_joined = df_joined[df_joined["dyn_elapsed_sec"] < quantile]
            df_joined = df_joined[df_joined["dyn_elapsed_sec"] > 10]  # 10 seconds min or this is bogus

            # mark categorical columns, remove columns that are not needed for training model, reorder columns
            df_joined["odt_status"] = df_joined["odt_status"].astype("category")
            df_joined["sto_ref_id"] = df_joined["sto_ref_id"].astype("category")
            df_joined["sto_name"] = df_joined["sto_name"].astype("category")
            df_joined["sto_area"] = df_joined["sto_area"].astype("category")
            df_joined["sto_province"] = df_joined["sto_province"].astype("category")
            df_joined = df_joined[
                [
                    "odt_status",
                    "sto_ref_id",
                    "sto_name",
                    "sto_area",
                    "sto_province",
                    "prev_odt_category_id",
                    "prev_odt_category_id.level2",
                    "prev_odt_category_id.level3",
                    "odt_category_id",
                    "odt_category_id.level2",
                    "odt_category_id.level3",
                    "odt_variable_weight",
                    "odt_replaceable",
                    "odt_touched_at.year",
                    "odt_touched_at.month",
                    "odt_touched_at.day",
                    "odt_touched_at.hour",
                    "odt_touched_at.dayofweek",
                    "dyn_elapsed_sec",
                ]
            ]
            return df_joined.copy()
        except Exception as exc:
            raise AnaliticoException(f"OrderSortingPlugin - error while training: {exc}") from exc

    def train(self, train, test, results, *args, **kwargs):
        """ Train with algorithm and given data to produce a trained model """
        train = self.preprocess_training_data(train)
        return super().train(train, test, results, *args, **kwargs)

    ##
    ## Predicting
    ##

    def create_distance_callback(self, sto_ref_id, sto_name, sto_area, sto_province, model, categories, meta):
        """ Creates a callback used to calculate the distance in seconds between product categories in a supermarket """
        _cache = {}

        def _distance_callback(from_node, to_node):
            if (from_node, to_node) in _cache:
                return _cache[(from_node, to_node)]

            started_on = time_ms()
            test_df = pd.DataFrame(
                [
                    collections.OrderedDict(
                        [
                            ("odt_status", "PURCHASED"),
                            ("sto_ref_id", sto_ref_id),
                            ("sto_name", sto_name),
                            ("sto_area", sto_area),
                            ("sto_province", sto_province),
                            # from
                            ("prev_odt_category_id", categories[from_node]["odt_category_id"]),
                            ("prev_odt_category_id.level2", categories[from_node]["odt_category_id.level2"]),
                            ("prev_odt_category_id.level3", categories[from_node]["odt_category_id.level3"]),
                            # to
                            ("odt_category_id", categories[to_node]["odt_category_id"]),
                            ("odt_category_id.level2", categories[to_node]["odt_category_id.level2"]),
                            ("odt_category_id.level3", categories[to_node]["odt_category_id.level3"]),
                            # fixed for all items
                            # TODO could use now date or order time date
                            ("odt_variable_weight", 0),  # categories[to_node]["odt_variable_weight"],
                            ("odt_replaceable", 0),
                            ("odt_touched_at.year", 2019),
                            ("odt_touched_at.month", 6),
                            ("odt_touched_at.day", 6),
                            ("odt_touched_at.hour", 12),
                            ("odt_touched_at.dayofweek", 1),
                        ]
                    )
                ]
            )

            # augment date information
            # test_df = analitico.pandas.augment_dates(test_df, "odt_touched_at")

            # use catboost model to guess distance between items in the supermarket
            test_preds = model.predict(test_df)
            test_distance = int(test_preds[0])
            _cache[(from_node, to_node)] = test_distance

            meta["predictions"] += 1
            meta["predictions_ms"] += time_ms(started_on)
            # print('distance_callback(%d,%d): %d' % (from_node, to_node, test_distance))
            return test_distance

        return _distance_callback

    def getdata(self, d, label1, label2=None):
        """ Read using current or older label for compatibility """
        if label1 in d:
            return d[label1]
        if label2 and label2 in d:
            return d[label2]
        return None

    def predict_single(self, data, model, meta):
        """ Sort a single order """
        sto_ref_id = self.getdata(data, "sto_ref_id", "store_ref_id")
        sto_name = self.getdata(data, "sto_name", "store_name")
        sto_area = self.getdata(data, "sto_area", "store_area")
        sto_province = self.getdata(data, "sto_province", "store_province")

        # items in the basket, no point in sorting an order if it's only got an item in it
        details = data["details"]
        if len(details) < 2:
            return data

        # extract all the categories used in the order (with main, sub and 3rd level category)
        # these will constitute the 'nodes' that the traveling salesman needs to visit to complete
        # the route. -1 is added as the start point and -2 is added as the end point (cashier)

        # entrance
        categories = [{"odt_category_id": -1, "odt_category_id.level2": -1, "odt_category_id.level3": -1}]
        for detail in details:
            # some items are entered manually and do not have an item_category_id or odt_category_id
            # this should not happen as items should be assign the category where the manual entry was
            # entered. however there is no good reason why the endpoint should choke, so assign category 0
            # https://github.com/analitico/analitico/issues/59
            item_category_id = self.getdata(detail, "odt_category_id", "item_category_id")
            try:
                item_category_id = int(item_category_id)
            except:
                item_category_id = 0
                self.warning(
                    "OutOfStockPlugin.predict - item does not have a valid odt_category_id field",
                    extra={"detail": detail},
                )

            categories.append(
                {
                    "odt_category_id": item_category_id,
                    "odt_category_id.level2": s24.categories.s24_get_category_id_level2(item_category_id),
                    "odt_category_id.level3": s24.categories.s24_get_category_id_level3(item_category_id),
                    "odt_category_id.slug": s24.categories.s24_get_category_slug_level1(item_category_id),
                    "odt_category_id.level2.slug": s24.categories.s24_get_category_slug_level2(item_category_id),
                    "odt_category_id.level3.slug": s24.categories.s24_get_category_slug_level3(item_category_id),
                }
            )
        # cashier
        categories.append({"odt_category_id": -2, "odt_category_id.level2": -2, "odt_category_id.level3": -2})

        # Google OR-Tools Traveling Salesman Problem
        # https://developers.google.com/optimization/
        # https://developers.google.com/optimization/routing/tsp
        # https://developers.google.com/optimization/routing/vrp
        # traveling salesman goes from entrance to cashier's nodes
        # https://developers.google.com/optimization/routing/routing_tasks#arbitrary_start

        start_locations = [0]  # entrance
        end_locations = [len(categories) - 1]  # cashier

        # creat routing model with number of nodes (entrance + items + cashier),
        # number of routes (1), starting and ending nodes (start at entrance, end at cashier)
        routing = pywrapcp.RoutingModel(len(categories), 1, start_locations, end_locations)

        # we are looking for the shortest route that includes all nodes with given start, end
        search_parameters = pywrapcp.RoutingModel.DefaultSearchParameters()
        # pylint: disable=no-member
        search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC

        # the distance callback will estimate the distance in seconds between items of certain
        # categories using the pretrained model that includes store info and pickig info
        dist_callback = self.create_distance_callback(
            sto_ref_id, sto_name, sto_area, sto_province, model, categories, meta
        )
        routing.SetArcCostEvaluatorOfAllVehicles(dist_callback)
        assignment = routing.SolveWithParameters(search_parameters)
        if assignment is False:
            raise AnaliticoException(
                "Could not come up with an optimal route for this order", status_code=417
            )  # expectation failed

        # calculate how long we estimate it would have taken to shop this list without sorting
        unsorted_distance = 0
        for i in range(1, len(categories)):
            unsorted_distance += dist_callback(i - 1, i)

        # process the solution
        sorted_details = []
        index = routing.Start(0)  # single vehicle (courier)
        print("item, cat_id")
        while not routing.IsEnd(index):
            if index > 0:  # skip entrance, exit
                # convert variable indices to node indices in the route
                node = routing.IndexToNode(index)
                category_id = categories[node]["odt_category_id"]
                sorted_details.append(details[node - 1])
                # enrich record with top level and subcategory information
                details[node - 1]["odt_category_id"] = categories[node]["odt_category_id"]
                details[node - 1]["odt_category_id.slug"] = categories[node]["odt_category_id.slug"]
                details[node - 1]["odt_category_id.level2"] = categories[node]["odt_category_id.level2"]
                details[node - 1]["odt_category_id.level2.slug"] = categories[node]["odt_category_id.level2.slug"]
                details[node - 1]["odt_category_id.level3"] = categories[node]["odt_category_id.level3"]
                details[node - 1]["odt_category_id.level3.slug"] = categories[node]["odt_category_id.level3.slug"]
                self.info(
                    "%4d, %6d %s > %s > %s: %s",
                    index,
                    category_id,
                    s24.categories.s24_get_category_slug_level1(category_id),
                    s24.categories.s24_get_category_slug_level2(category_id),
                    s24.categories.s24_get_category_slug_level3(category_id),
                    self.getdata(details[node - 1], "odt_name", "item_name"),
                )
            index = assignment.Value(routing.NextVar(index))

        # add original and sorted order picking time estimates
        data["unsorted_time_sec"] = unsorted_distance
        data["sorted_time_sec"] = assignment.ObjectiveValue()
        data["details"] = sorted_details
        return data

    def predict(self, data, training, results, *args, **kwargs):
        """ Takes an order with item details and sorts them so it's quicker to shop """
        try:
            # create model object from stored file
            meta = results["performance"]
            started_on = time_ms()

            model_path = os.path.join(self.factory.get_artifacts_directory(), "model.cbm")
            if not os.path.isfile(model_path):
                self.exception("CatBoostPlugin.predict - cannot find saved model in %s", model_path)

            loading_on = time_ms()
            model = self.create_model(training)
            model.load_model(model_path)
            meta["loading_ms"] = time_ms(loading_on)

            meta["items"] = 0
            meta["predictions"] = 0
            meta["predictions_ms"] = 0

            results["records"] = []
            results["predictions"] = []

            # handle a single record at a time
            for item in data:
                results["records"].append(item)
                meta["items"] += len(item["details"])
                item = self.predict_single(copy.deepcopy(item), model, meta)
                results["predictions"].append(item)

            meta["total_ms"] = time_ms(started_on)
            return results

        except Exception as exc:
            raise exc


##
## UTILITIES
##


def _famila_orders_csv_to_json():
    df = pd.read_csv("data/s24/s24-orders-famila-saval.csv", dtype=str)
    # df = df[df.columns].astype(str)

    orders = []
    order = {}
    for _, row in df.iterrows():
        if order.get("order_id") != str(row["order_id"]):
            order = {
                "order_id": str(row["order_id"]),
                "store_ref_id": str(row["store_ref_id"]),
                "store_name": row["store_name"],
                "store_area": row["store_area"],
                "store_province": row["store_province"],
                "details": [],
            }
            orders.append(order)
        order["details"].append(
            {
                "detail_id": str(row["detail_id"]),
                "item_ean": str(row["item_ean"]),
                "item_ref_id": str(row["item_ref_id"]),
                "item_name": str(row["item_name"]),
                "item_category_id": str(row["item_category_id"]),
                "item_category_name": str(row["item_category_name"]),
            }
        )

    with open("../data/s24/s24-orders-famila-saval.json", "w") as outfile:
        json.dump(orders, outfile, indent=4)

    return orders
