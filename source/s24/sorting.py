
# Sorting supermarket orders based on 
# machine learned market maps

# Copyright (C) 2018 by Analitco.ai
# All rights reserved.

import os
import sys
import json
import multiprocessing

import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, median_absolute_error
from catboost import Pool, CatBoostRegressor, CatBoostClassifier
from pandas.api.types import CategoricalDtype
from pathlib import Path
from joblib import Parallel, delayed

from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2

from analitico.api import ApiException, api_check_auth, api_get_parameter
from analitico.utilities import timestamp_to_time, timestamp_diff_secs, dataframe_to_catpool
from analitico.train import time_ms
from analitico.storage import storage_open, storage_path, storage_temp, storage_cache

from s24.categories import s24_get_category_id, s24_get_category_name, s24_get_category_slug

# used for directories, reporting, billing, auth, etc
PROJECT_ID = 's24-order-sorting'

# paths of training data and trained model
TRAINING_CSV_PATH = 'data/s24/training/order-details-joined.csv'
MODEL_PATH = 'data/s24/models/order-sorting/model.cbm'
SCORES_PATH = 'data/s24/models/order-sorting/scores.json'

# subset of rows used for quick training while developing
_training_sample = None # eg: 5000 for quick run


##
## PRIVATE
##

# features used for model training and prediction
_features = [ 
    'store_ref_id', 'store_name', 
    'from_main_category_id', 'from_sub_category_id', 'from_category_id', 
    'to_main_category_id', 'to_sub_category_id', 'to_category_id', 
    'status'
    ]

# training data is used to learn the distance in seconds between category of items in a supermarket
_label_feature = 'elapsed_sec'

# cached catboost model
_model = None


def _training_augment_chunk(df):
    """ Augment training data in a specific dataframe (can be called concurrently) """
    data = []

    for index, row in df.iterrows():
        hasPrev = row['order_id'] == row['prev_order_id']
        hasNext = row['order_id'] == row['next_order_id']

        if (index % 1000 == 0):
            sys.stdout.write('.')
            sys.stdout.flush()

        # first item in order (previous is entrance)
        if hasPrev is False: 
            data.append([
                # store_id, store_name, store_area
                row['store_ref_id'], row['store_name'], # row['store_area'],
                # from_category_id, from_sub_category_id for 'entrance'
                -1, -1, -1,
                # to_category_id, to_sub_category_id
                s24_get_category_id(int(row['category_id']), 0), 
                s24_get_category_id(int(row['category_id']), 1),
                s24_get_category_id(int(row['category_id']), 2),
                # status, elapsed_sec
                row['status'], 0
            ])

        # item has a previous item
        if row['order_id'] == row['prev_order_id']:
            data.append([
                # store_id, store_name, store_area
                row['store_ref_id'], row['store_name'], #row['store_area'],
                # from_category_id, from_sub_category_id
                s24_get_category_id(int(row['prev_category_id']), 0), 
                s24_get_category_id(int(row['prev_category_id']), 1),
                s24_get_category_id(int(row['prev_category_id']), 2),
                # to_category_id, to_sub_category_id
                s24_get_category_id(int(row['category_id']), 0), 
                s24_get_category_id(int(row['category_id']), 1),
                s24_get_category_id(int(row['category_id']), 2),
                # status, elapsed_sec
                row['status'], timestamp_diff_secs(row['touched_at'], row['prev_touched_at']),
            ])

        # last item in order (next is cashier)
        if hasNext is False:
            data.append([
                # store_id, store_name, store_area
                row['store_ref_id'], row['store_name'],# row['store_area'],
                # from_category_id, from_sub_category_id for 'entrance'
                s24_get_category_id(int(row['category_id']), 0), 
                s24_get_category_id(int(row['category_id']), 1),
                s24_get_category_id(int(row['category_id']), 2),
                # to_category_id, to_sub_category_id for 'checkout'
                -2, -2, -2,
                # status, elapsed_sec
                row['status'], 0
            ])
    return data


def _training_augment_df(df):
    """ Augments a given dataframe, returns augmented df """

    # add columns for previous and next order_detail
    df['prev_order_id'] = df['order_id'].shift(1)
    df['prev_category_id'] = df['category_id'].shift(1)
    df['prev_touched_at'] = df['touched_at'].shift(1)
    df['next_order_id'] = df['order_id'].shift(-1)
    df['next_category_id'] = df['category_id'].shift(-1)

    # it's a lot of rows so we split them in an array of chunks 
    # which are then processed in parallel on each of the cores
    # speeding up augmentation substantially (eg: laptop has 12 cores)
    # https://joblib.readthedocs.io/en/latest/parallel.html

    chunk_size = 5000
    chunk_dfs = [df[i:i+chunk_size] for i in range(0, df.shape[0], chunk_size)]

    results = Parallel(n_jobs=multiprocessing.cpu_count())(
        delayed(_training_augment_chunk)(chunk_df) for chunk_df in chunk_dfs)
    print('\n')

    augmented_data = []
    for result in results:
        for item in result:
            augmented_data.append(item)

    # for item in _training_augment_chunk(df):
    #    augmented_data.append(item)

    augmented_df = pd.DataFrame(augmented_data, columns=(_features + [_label_feature]))

    debug = False
    if debug:
        augmented_df['from_main_category_slug'] = augmented_df.apply(lambda row: s24_get_category_slug(row['from_main_category_id'], 0), axis=1) 
        augmented_df['from_sub_category_slug'] = augmented_df.apply(lambda row: s24_get_category_slug(row['from_sub_category_id'], 1), axis=1) 
        augmented_df['from_category_slug'] = augmented_df.apply(lambda row: s24_get_category_slug(row['from_category_id'], 2), axis=1) 
        augmented_df['to_main_category_slug'] = augmented_df.apply(lambda row: s24_get_category_slug(row['to_main_category_id'], 0), axis=1) 
        augmented_df['to_sub_category_slug'] = augmented_df.apply(lambda row: s24_get_category_slug(row['to_sub_category_id'], 1), axis=1) 
        augmented_df['to_category_slug'] = augmented_df.apply(lambda row: s24_get_category_slug(row['to_category_id'], 2), axis=1) 
        parts = os.path.splitext(TRAINING_CSV_PATH)
        augmented_path = parts[0] + '-augmented' + parts[1]
        augmented_df.to_csv(augmented_path)
        print('saved %d rows to %s' % (len(augmented_df), augmented_path))

    return augmented_df


def train():
    """ Runs training on the catboost model used for sorting, produces .cbm file and stats """

    started_on = time_ms()
    data, meta = { 'records': {}}, {}

    with storage_open(TRAINING_CSV_PATH) as training_csv:
        df = pd.read_csv(training_csv)
        data['records']['source'] = len(df) 
        meta['loading_ms'] = time_ms(started_on)

    # remove rows without an item's category
    df = df.dropna(subset=['category_id'])

    # if requested, subset rows for quick prototyping
    if (_training_sample is not None):
        df = df.tail(_training_sample)
        data['records']['sampled'] = len(df) 

    # augment data, create extended dataframe
    df = _training_augment_df(df)
    data['records']['augmented'] = len(df) 
    # remove items that are outliers in terms of time elapsed        
    df = df[df['elapsed_sec'] < 8 * 60]
    
    # if we remove items where the courier had to replace item or
    # call the customer we get a higher score. however, if we leave
    # this field in we have more records. also, the system learns to
    # differentiate elapsed time based on status and we will only place
    # predictions for status == PURCHASED which are easier to predict
    #
    # df = df[df['status'] == 'PURCHASED']
    
    data['records']['filtered'] = len(df) 
    meta['processing_ms'] = time_ms(started_on)

    # test set from a random assortment of rows
    train_df, test_df = train_test_split(df, test_size=0.15, random_state=42)
    data['records']['training'] = len(train_df)
    data['records']['test'] = len(test_df)

    train_pool, _ = dataframe_to_catpool(train_df, _features, _features, None, _label_feature)
    test_pool, test_labels = dataframe_to_catpool(test_df, _features, _features, None, _label_feature)

    # create, train and save catboost regression model 
    training_on = time_ms()
    total_iterations = 100
    model = CatBoostRegressor(task_type='GPU', iterations=total_iterations, loss_function='RMSE')
    model.fit(train_pool, eval_set=test_pool)
    model.save_model(MODEL_PATH)

    data['assets'] = {}
    data['assets']['model_path'] = MODEL_PATH
    data['assets']['scores_path'] = SCORES_PATH

    meta['total_iterations'] = total_iterations
    meta['best_iteration'] = model.get_best_iteration()
    meta['best_score'] = model.get_best_score()
    meta['training_ms'] = time_ms(training_on)

    # make the prediction using the resulting model
    test_predictions = model.predict(test_pool)

    # loss metrics on test set
    scores = data['scores'] = {}
    scores['median_abs_error'] = round(median_absolute_error(test_predictions, test_labels), 5)
    scores['mean_abs_error'] = round(mean_absolute_error(test_predictions, test_labels), 5)
    scores['sqrt_mean_squared_error'] = round(np.sqrt(mean_squared_error(test_predictions, test_labels)), 5)

    # catboost can tell which features weigh more heavily on the predictions
    data['features_importance'] = {}
    feature_importance = model.get_feature_importance(prettified=True)
    for label, importance in feature_importance:
        data['features_importance'][label] = round(importance, 5)

    meta['total_ms'] = time_ms(started_on)

    with open(SCORES_PATH, 'w') as f:
        f.write(json.dumps({ 'data': data, 'meta': meta }, indent=4))

    return data, meta

##
## UTILITIES
##

def _famila_orders_csv_to_json():
    df = pd.read_csv('data/s24/s24-orders-famila-saval.csv', dtype=str)
    #df = df[df.columns].astype(str)

    orders = []
    order = {}
    for _, row in df.iterrows():
        if order.get('order_id') != str(row['order_id']):
            order = {
                'order_id': str(row['order_id']),
                'store_ref_id': str(row['store_ref_id']),
                'store_name': row['store_name'],
                'store_area': row['store_area'],
                'store_province': row['store_province'],
                'details': []
            }
            orders.append(order)
        order['details'].append({
            'detail_id': str(row['detail_id']),
            'item_ean': str(row['item_ean']),
            'item_ref_id': str(row['item_ref_id']),
            'item_name': str(row['item_name']),
            'item_category_id': str(row['item_category_id']),
            'item_category_name': str(row['item_category_name'])
        })

    with open('../data/s24/s24-orders-famila-saval.json', 'w') as outfile:
        json.dump(orders, outfile, indent=4)

    return orders

##
## SORTING
##

def _create_distance_callback(store_ref_id, store_name, model, categories, meta):
    """ Creates a callback used to calculate the distance in seconds between product categories in a supermarket """
    _cache = {}  

    def _distance_callback(from_node, to_node):
        if (from_node, to_node) in _cache:
            return _cache[(from_node, to_node)]

        started_on = time_ms()
        test_df = pd.DataFrame([{
            'store_ref_id': store_ref_id, 
            'store_name': store_name,
            'from_main_category_id': categories[from_node]['main_category_id'],
            'from_sub_category_id': categories[from_node]['sub_category_id'],
            'from_category_id': categories[from_node]['category_id'],
            'to_main_category_id': categories[to_node]['main_category_id'],
            'to_sub_category_id': categories[to_node]['sub_category_id'],
            'to_category_id': categories[to_node]['category_id'],
            'status': 'PURCHASED'
        }])

        # use catboost model to guess distance between items in the supermarket
        test_preds = model.predict(test_df)
        test_distance = int(test_preds[0])
        _cache[(from_node, to_node)] = test_distance

        meta['predictions'] = meta['predictions'] + 1
        meta['predictions_ms'] = meta['predictions_ms'] + time_ms(started_on)
        # print('distance_callback(%d,%d): %d' % (from_node, to_node, test_distance)) 

        return test_distance
    return _distance_callback


def s24_sort_order(order) -> ({}, {}):
    """ Takes an order with item details and sorts them so it's quicker to shop """

    started_on = time_ms()
    store_ref_id = order['store_ref_id']
    store_name = order['store_name']
    details = order['details']
    meta = {
        'items': len(details),
        'predictions': 0,
        'predictions_ms': 0
    }

    # no point in sorting an order if it's only got one item in it
    if len(details) < 2:
        return order,  meta

    # extract all the categories used in the order (with main, sub and 3rd level category)
    # these will constitute the 'nodes' that the traveling salesman needs to visit to complete
    # the route. -1 is added as the start point and -2 is added as the end point (cashier)
    categories = [{ 'main_category_id': -1, 'sub_category_id': -1, 'category_id': -1 }] # entrance
    for detail in details:
        item_category_id = int(detail['item_category_id'])
        categories.append({
            'main_category_id': s24_get_category_id(item_category_id, 0), 
            'sub_category_id': s24_get_category_id(item_category_id, 1),
            'category_id': s24_get_category_id(item_category_id, 2),            
            'main_category_name': s24_get_category_name(item_category_id, 0), 
            'sub_category_name': s24_get_category_name(item_category_id, 1)
        })
    categories.append({ 'main_category_id': -2, 'sub_category_id': -2, 'category_id': -2 }) # cashier

    # Google OR-Tools Traveling Salesman Problem
    # https://developers.google.com/optimization/
    # https://developers.google.com/optimization/routing/tsp
    # https://developers.google.com/optimization/routing/vrp

    model_path = storage_cache(MODEL_PATH)

    # TODO cache model using weak pointer? check if model was updated?
    global _model
    if _model is None:
        # create model to predict run times between items
        loading_on = time_ms()
        _model = CatBoostRegressor()
        _model.load_model(model_path)
        meta['loading_ms'] = time_ms(loading_on)

    # traveling salesman goes from entrance to cashier's nodes
    # https://developers.google.com/optimization/routing/routing_tasks#arbitrary_start

    start_locations = [0] # entrance
    end_locations = [len(categories) - 1] # cashier

    # creat routing model with number of nodes (entrance + items + cashier), 
    # number of routes (1), starting and ending nodes (start at entrance, end at cashier)
    routing = pywrapcp.RoutingModel(len(categories), 1, start_locations, end_locations)

    # we are looking for the shortest route that includes all nodes with given start, end
    search_parameters = pywrapcp.RoutingModel.DefaultSearchParameters()
    search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

    # the distance callback will estimate the distance in seconds between items of certain
    # categories using the pretrained model that includes store info and pickig info
    dist_callback = _create_distance_callback(store_ref_id, store_name, _model, categories, meta)
    routing.SetArcCostEvaluatorOfAllVehicles(dist_callback)

    # solve the problem
    routing_on = time_ms()
    assignment = routing.SolveWithParameters(search_parameters)
    routing_ms = time_ms(routing_on) - meta['predictions_ms']

    if assignment is False:
        raise ApiException("Could not come up with an optimal route for this order", 417) # expectation failed

    # calculate how long we estimate it would have taken to shop this list without sorting
    unsorted_distance = 0
    for i in range(1, len(categories)):
        unsorted_distance += dist_callback(i-1,i)

    # process the solution
    sorted_details = []
    index = routing.Start(0) # single vehicle (courier)
    print('item, cat_id')
    while not routing.IsEnd(index):
        if index > 0: # skip entrance, exit
            # convert variable indices to node indices in the route
            node = routing.IndexToNode(index)
            category_id = categories[node]['category_id']
            sorted_details.append(details[node-1])
            # enrich record with top level and subcategory information
            details[node-1]['main_category_id'] = categories[node]['main_category_id']
            details[node-1]['main_category_name'] = categories[node]['main_category_name']
            details[node-1]['sub_category_id'] = categories[node]['sub_category_id']
            details[node-1]['sub_category_name'] = categories[node]['sub_category_name']
            print('%4d, %6d %s > %s > %s: %s' % (index, category_id, s24_get_category_slug(category_id, 0), s24_get_category_slug(category_id, 1), s24_get_category_slug(category_id, 2), details[node-1]['item_name']))
        index = assignment.Value(routing.NextVar(index))

    meta['routing_ms'] = routing_ms
    meta['total_ms'] = time_ms(started_on)

    # add original and sorted order picking time estimates
    meta['unsorted_time_sec'] = unsorted_distance
    meta['sorted_time_sec'] = assignment.ObjectiveValue()

    # returns order with sorted items, enhanched category info, metadata
    order['details'] = sorted_details
    return order, meta


def handle_sorting_request(request):
    """ Responds to an API call, returning a sorted order """
    api_check_auth(request, PROJECT_ID)

    # request must be for a single order sorting
    order = api_get_parameter(request, "data")
    if order is None:
        raise ApiException('Call to methods should include data with an order and order details, see documentation', 500)

    # return sorted order and metadata
    order, meta = s24_sort_order(order)
    return { "data": order, "meta": meta }
