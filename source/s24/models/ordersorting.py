# Sorting supermarket orders based on
# machine learned market maps

# Copyright (C) 2018 by Analitco.ai
# All rights reserved.

import os
import sys
import json
import multiprocessing

import pandas as pd
import catboost

import analitico.models
import analitico.utilities
import analitico.storage

from joblib import Parallel, delayed

from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2

from analitico.utilities import timestamp_diff_secs, time_ms, get_dict_dot, logger

from rest_framework.exceptions import APIException

from s24.categories import s24_get_category_id, s24_get_category_name, s24_get_category_slug

# used for directories, reporting, billing, auth, etc
PROJECT_ID = "s24-order-sorting"

# paths of training data and trained model
TRAINING_CSV_PATH = "data/s24/training/order-details-joined.csv"
MODEL_PATH = "data/s24/models/order-sorting/model.cbm"
SCORES_PATH = "data/s24/models/order-sorting/scores.json"


class OrderSortingModel(analitico.models.TabularRegressorModel):
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

    def _training_augment_chunk(self, df):
        """ Augment training data in a specific dataframe (can be called concurrently) """
        data = []

        for index, row in df.iterrows():
            hasPrev = row["order_id"] == row["prev_order_id"]
            hasNext = row["order_id"] == row["next_order_id"]

            if index % 1000 == 0:
                sys.stdout.write(".")
                sys.stdout.flush()

            # first item in order (previous is entrance)
            if hasPrev is False:
                data.append(
                    [
                        # store_id, store_name, store_area
                        row["store_ref_id"],
                        row["store_name"],  # row['store_area'],
                        # from_category_id, from_sub_category_id for 'entrance'
                        -1,
                        -1,
                        -1,
                        # to_category_id, to_sub_category_id
                        s24_get_category_id(int(row["category_id"]), 0),
                        s24_get_category_id(int(row["category_id"]), 1),
                        s24_get_category_id(int(row["category_id"]), 2),
                        # status, elapsed_sec
                        row["status"],
                        0,
                    ]
                )

            # item has a previous item
            if row["order_id"] == row["prev_order_id"]:
                data.append(
                    [
                        # store_id, store_name, store_area
                        row["store_ref_id"],
                        row["store_name"],  # row['store_area'],
                        # from_category_id, from_sub_category_id
                        s24_get_category_id(int(row["prev_category_id"]), 0),
                        s24_get_category_id(int(row["prev_category_id"]), 1),
                        s24_get_category_id(int(row["prev_category_id"]), 2),
                        # to_category_id, to_sub_category_id
                        s24_get_category_id(int(row["category_id"]), 0),
                        s24_get_category_id(int(row["category_id"]), 1),
                        s24_get_category_id(int(row["category_id"]), 2),
                        # status, elapsed_sec
                        row["status"],
                        timestamp_diff_secs(row["touched_at"], row["prev_touched_at"]),
                    ]
                )

            # last item in order (next is cashier)
            if hasNext is False:
                data.append(
                    [
                        # store_id, store_name, store_area
                        row["store_ref_id"],
                        row["store_name"],  # row['store_area'],
                        # from_category_id, from_sub_category_id for 'entrance'
                        s24_get_category_id(int(row["category_id"]), 0),
                        s24_get_category_id(int(row["category_id"]), 1),
                        s24_get_category_id(int(row["category_id"]), 2),
                        # to_category_id, to_sub_category_id for 'checkout'
                        -2,
                        -2,
                        -2,
                        # status, elapsed_sec
                        row["status"],
                        0,
                    ]
                )
        return data

    def _train_augment_records(self, df):
        """ Augments a given dataframe, returns augmented df """

        # disable warning on chained assignments below...
        # https://stackoverflow.com/questions/20625582/how-to-deal-with-settingwithcopywarning-in-pandas
        pd.options.mode.chained_assignment = None

        # add columns for previous and next order_detail
        df["prev_order_id"] = df["order_id"].shift(1)
        df["prev_category_id"] = df["category_id"].shift(1)
        df["prev_touched_at"] = df["touched_at"].shift(1)
        df["next_order_id"] = df["order_id"].shift(-1)
        df["next_category_id"] = df["category_id"].shift(-1)

        # it's a lot of rows so we split them in an array of chunks
        # which are then processed in parallel on each of the cores
        # speeding up augmentation substantially (eg: laptop has 12 cores)
        # https://joblib.readthedocs.io/en/latest/parallel.html

        parallel = False

        if not parallel:
            # process all records at once (mostly single-thread)
            augmented_data = self._training_augment_chunk(df)
        else:
            chunk_size = 5000
            chunk_dfs = [df[i : i + chunk_size] for i in range(0, df.shape[0], chunk_size)]

            results = Parallel(n_jobs=multiprocessing.cpu_count())(
                delayed(self._training_augment_chunk)(chunk_df) for chunk_df in chunk_dfs
            )
            print("\n")

            augmented_data = []
            for result in results:
                for item in result:
                    augmented_data.append(item)

        # for item in _training_augment_chunk(df):
        #    augmented_data.append(item)

        augmented_df = pd.DataFrame(augmented_data, columns=(self.features + [self.label]))

        debug = False
        if debug:
            augmented_df["from_main_category_slug"] = augmented_df.apply(
                lambda row: s24_get_category_slug(row["from_main_category_id"], 0), axis=1
            )
            augmented_df["from_sub_category_slug"] = augmented_df.apply(
                lambda row: s24_get_category_slug(row["from_sub_category_id"], 1), axis=1
            )
            augmented_df["from_category_slug"] = augmented_df.apply(
                lambda row: s24_get_category_slug(row["from_category_id"], 2), axis=1
            )
            augmented_df["to_main_category_slug"] = augmented_df.apply(
                lambda row: s24_get_category_slug(row["to_main_category_id"], 0), axis=1
            )
            augmented_df["to_sub_category_slug"] = augmented_df.apply(
                lambda row: s24_get_category_slug(row["to_sub_category_id"], 1), axis=1
            )
            augmented_df["to_category_slug"] = augmented_df.apply(
                lambda row: s24_get_category_slug(row["to_category_id"], 2), axis=1
            )
            parts = os.path.splitext(TRAINING_CSV_PATH)
            augmented_path = parts[0] + "-augmented" + parts[1]
            augmented_df.to_csv(augmented_path)
            print("saved %d rows to %s" % (len(augmented_df), augmented_path))

        return augmented_df

    def preprocess_data(self, df, training=False, results=None):
        """ Remove outliers and sort dataset before it's used for training """
        if training:
            # remove rows without an item's category
            df = df.dropna(subset=["category_id"])

        # augment data, create extended dataframe
        df = self._train_augment_records(df)

        if training:
            # remove items that are outliers in terms of time elapsed
            df = df[df["elapsed_sec"] < 8 * 60]

        # if we remove items where the courier had to replace item or
        # call the customer we get a higher score. however, if we leave
        # this field in we have more records. also, the system learns to
        # differentiate elapsed time based on status and we will only place
        # predictions for status == PURCHASED which are easier to predict
        #
        # df = df[df['status'] == 'PURCHASED']
        return super().preprocess_data(df, training, results)

    #
    # predicting
    #

    def _create_distance_callback(self, store_ref_id, store_name, model, categories, meta):
        """ Creates a callback used to calculate the distance in seconds between product categories in a supermarket """
        _cache = {}

        def _distance_callback(from_node, to_node):
            if (from_node, to_node) in _cache:
                return _cache[(from_node, to_node)]

            started_on = time_ms()
            test_df = pd.DataFrame(
                [
                    {
                        "store_ref_id": store_ref_id,
                        "store_name": store_name,
                        "from_main_category_id": categories[from_node]["main_category_id"],
                        "from_sub_category_id": categories[from_node]["sub_category_id"],
                        "from_category_id": categories[from_node]["category_id"],
                        "to_main_category_id": categories[to_node]["main_category_id"],
                        "to_sub_category_id": categories[to_node]["sub_category_id"],
                        "to_category_id": categories[to_node]["category_id"],
                        "status": "PURCHASED",
                    }
                ]
            )

            # use catboost model to guess distance between items in the supermarket
            test_preds = model.predict(test_df)
            test_distance = int(test_preds[0])
            _cache[(from_node, to_node)] = test_distance

            meta["predictions"] = meta["predictions"] + 1
            meta["predictions_ms"] = meta["predictions_ms"] + time_ms(started_on)
            # print('distance_callback(%d,%d): %d' % (from_node, to_node, test_distance))

            return test_distance

        return _distance_callback

    def predict(self, data):
        """ Takes an order with item details and sorts them so it's quicker to shop """

        started_on = time_ms()
        store_ref_id = data["store_ref_id"]
        store_name = data["store_name"]
        details = data["details"]
        meta = {"items": len(details), "predictions": 0, "predictions_ms": 0}

        # no point in sorting an order if it's only got one item in it
        if len(details) < 2:
            return {"data": data, "meta": meta}

        # extract all the categories used in the order (with main, sub and 3rd level category)
        # these will constitute the 'nodes' that the traveling salesman needs to visit to complete
        # the route. -1 is added as the start point and -2 is added as the end point (cashier)
        categories = [{"main_category_id": -1, "sub_category_id": -1, "category_id": -1}]  # entrance
        for detail in details:
            item_category_id = int(detail["item_category_id"])
            categories.append(
                {
                    "main_category_id": s24_get_category_id(item_category_id, 0),
                    "sub_category_id": s24_get_category_id(item_category_id, 1),
                    "category_id": s24_get_category_id(item_category_id, 2),
                    "main_category_name": s24_get_category_name(item_category_id, 0),
                    "sub_category_name": s24_get_category_name(item_category_id, 1),
                }
            )
        categories.append({"main_category_id": -2, "sub_category_id": -2, "category_id": -2})  # cashier

        # Google OR-Tools Traveling Salesman Problem
        # https://developers.google.com/optimization/
        # https://developers.google.com/optimization/routing/tsp
        # https://developers.google.com/optimization/routing/vrp

        # create model to predict run times between items
        loading_on = time_ms()
        model = catboost.CatBoostRegressor()
        model_url = get_dict_dot(self.training, "data.assets.model_url")
        model_filename = analitico.storage.download_file(model_url)
        model.load_model(model_filename)
        meta["loading_ms"] = time_ms(loading_on)

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
        dist_callback = self._create_distance_callback(store_ref_id, store_name, model, categories, meta)
        routing.SetArcCostEvaluatorOfAllVehicles(dist_callback)

        # solve the problem
        routing_on = time_ms()
        assignment = routing.SolveWithParameters(search_parameters)
        routing_ms = time_ms(routing_on) - meta["predictions_ms"]

        if assignment is False:
            raise APIException("Could not come up with an optimal route for this order", 417)  # expectation failed

        # calculate how long we estimate it would have taken to shop this list without sorting
        unsorted_distance = 0
        for i in range(1, len(categories)):
            unsorted_distance += dist_callback(i - 1, i)

        # process the solution
        sorted_details = []
        index = routing.Start(0)  # single vehicle (courier)

        while not routing.IsEnd(index):
            if index > 0:  # skip entrance, exit
                # convert variable indices to node indices in the route
                node = routing.IndexToNode(index)
                category_id = categories[node]["category_id"]
                sorted_details.append(details[node - 1])
                # enrich record with top level and subcategory information
                details[node - 1]["main_category_id"] = categories[node]["main_category_id"]
                details[node - 1]["main_category_name"] = categories[node]["main_category_name"]
                details[node - 1]["sub_category_id"] = categories[node]["sub_category_id"]
                details[node - 1]["sub_category_name"] = categories[node]["sub_category_name"]
                logger.info(
                    "%4d, %6d %s > %s > %s: %s",
                    index,
                    category_id,
                    s24_get_category_slug(category_id, 0),
                    s24_get_category_slug(category_id, 1),
                    s24_get_category_slug(category_id, 2),
                    details[node - 1]["item_name"],
                )
            index = assignment.Value(routing.NextVar(index))

        meta["routing_ms"] = routing_ms
        meta["total_ms"] = time_ms(started_on)

        # add original and sorted order picking time estimates
        meta["unsorted_time_sec"] = unsorted_distance
        meta["sorted_time_sec"] = assignment.ObjectiveValue()

        # returns order with sorted items, enhanched category info, metadata
        data["details"] = sorted_details
        return {"data": data, "meta": meta}


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
