
## tutti pick_time.min non nulli

228808 orders

 'features_importance': {
     'courier_orders_taken': 42.63525,
    'order_deliver_at_start.hour': 27.45238,
    'odt_items_with_variable_weight': 21.14369,
    'courier_area': 4.3827,
    'store_area': 4.38121,
    'order_deliver_at_start.month': 0.00303,
    'courier_created_days': 0.00174,
    'odt_items_total': 0.0,
'median_abs_error': 10.86677,
'mean_abs_error': 20.17119,
'sqrt_mean_squared_error': 127.54155,

REMARKS: completely off, need to chop head/tail

## remove pick_time.min with z-score >= 2 (2 standard deviations)

228807 orders (just one order removed!!!)

 'features_importance': {
    'odt_items_total': 39.28432,
    'order_fulfillment_type': 16.48704,
    'order_deliver_at_start.month': 13.29491,
    'store_name': 11.87044,
    'courier_id': 6.73784,
    'courier_orders_taken': 6.23567,
    'store_province': 3.08157,
    'odt_items_with_variable_weight': 1.54864,
    'courier_created_days': 1.45958,

'median_abs_error': 8.00085,
'mean_abs_error': 14.03921,
'sqrt_mean_squared_error': 47.92036,
'model_size': 56752}),
    
'best_iteration': 2,
'best_score': {'training': {'RMSE': 15.281928939740574},
'validation': {'RMSE': 47.92036359589174}},

REMARKS: not converging on test set, something is wrong

## remove pick_time.min with z-score >= 1.5 (1.5 standard deviations)

same as above

## remove pick_time.min less than 2 minutes

216009 orders

'features_importance': 
    'order_deliver_at_start.hour': 50.34921,
    'store_area': 21.31853,
    'courier_created_days': 10.89942,
    'courier_id': 9.11112,
    'order_deliver_at_start.dayofweek': 8.32173,

'best_iteration': 0,
'best_score': {'training': {'RMSE': 4876.175374383757},
'validation': {'RMSE': 235.10137517218428}},

REMARKS: not converging, huge error due to order with loooong pick time

## remove pick_time.min over 90 minutes

212229 orders

'features_importance': {
    'odt_items_total': 35.05036,
    'store_name': 22.45794,
    'courier_orders_taken': 14.65156,
    'courier_id': 10.39369,
    'odt_items_with_variable_weight': 6.01244,
    'store_province': 2.99057,
    'courier_created_days': 2.78168,
    'order_fulfillment_type': 2.12213,
    'order_deliver_at_start.month': 1.62598,
    'store_ref_id': 0.94108,
    'order_deliver_at_start.year': 0.38552,
    'store_area': 0.21678,
    'courier_area': 0.14255,
    'order_deliver_at_start.day': 0.10569,
    'order_deliver_at_start.hour': 0.08748,
    'order_deliver_at_start.dayofweek': 0.03453},
'median_abs_error': 6.91759,
'mean_abs_error': 9.11758,
'sqrt_mean_squared_error': 12.4951,
'model_size': 3275084}),

('scores', {
    'best_iteration': 17,
    'best_score': {'training': {'RMSE': 9.931089582315956},
    'validation': {'RMSE': 12.495102877128403}},

REMARKS: starts looking right

## remove pick_time.min z-score > 1 (1 standard deviation)

154976 orders

'features_importance': {
    'odt_items_total': 28.40002,
    'store_province': 17.2445,
    'courier_id': 12.8093,
    'courier_orders_taken': 11.248,
    'store_name': 10.22019,
    'odt_items_with_variable_weight': 6.58946,
    'courier_created_days': 3.57096,
    'courier_area': 2.55936,
    'store_ref_id': 2.45728,
    'order_deliver_at_start.month': 1.49471,
    'store_area': 0.82574,
    'order_fulfillment_type': 0.74455,
    'order_deliver_at_start.year': 0.56824,
    'order_deliver_at_start.hour': 0.50457,
    'order_deliver_at_start.dayofweek': 0.41034,
    'order_deliver_at_start.day': 0.35279},
'median_abs_error': 4.92078,
'mean_abs_error': 5.68205,
'sqrt_mean_squared_error': 7.09819,
'model_size': 2111540}),

('scores',
    'best_iteration': 31,
    'best_score': {'training': {'RMSE': 6.094774363674216},
    'validation': {'RMSE': 7.098193809715621}},

REMARKS: filtered too much

## remove pick_time.min z-score > 2 (2 standard devs)

201118 orders

'odt_items_total': 29.58483,
'store_name': 20.57271,
'courier_id': 13.34292,
'courier_orders_taken': 12.08287,
'odt_items_with_variable_weight': 6.57526,
'courier_created_days': 3.63356,
'store_province': 3.21658,
'order_fulfillment_type': 3.11119,
'store_area': 2.63937,
'order_deliver_at_start.month': 2.16531,
'courier_area': 1.34399,
'store_ref_id': 0.66952,
'order_deliver_at_start.hour': 0.40683,
'order_deliver_at_start.year': 0.29515,
'order_deliver_at_start.dayofweek': 0.21147,
'order_deliver_at_start.day': 0.14845}

('scores',
    'best_iteration': 40,
    'best_score': {'training': {'RMSE': 7.899196730808206},
    'validation': {'RMSE': 9.347241332491311}},

'median_abs_error': 5.5851,
'mean_abs_error': 7.06564,
'sqrt_mean_squared_error': 9.34724,
'model_size': 4895920}),

# pick_time.min between 2 and 90 minutes

212229 orders

'odt_items_total': 35.05036,
'store_name': 22.45794,
'courier_orders_taken': 14.65156,
'courier_id': 10.39369,
'odt_items_with_variable_weight': 6.01244,
'store_province': 2.99057,
'courier_created_days': 2.78168,
'order_fulfillment_type': 2.12213,
'order_deliver_at_start.month': 1.62598,
'store_ref_id': 0.94108,
'order_deliver_at_start.year': 0.38552,
'store_area': 0.21678,
'courier_area': 0.14255,
'order_deliver_at_start.day': 0.10569,
'order_deliver_at_start.hour': 0.08748,
'order_deliver_at_start.dayofweek': 0.03453

('scores',
    'best_iteration': 17,
    'best_score': {'training': {'RMSE': 9.931089582315956},
    'validation': {'RMSE': 12.495102877128403}},

'median_abs_error': 6.91759,
'mean_abs_error': 9.11758,
'sqrt_mean_squared_error': 12.4951,
'model_size': 3275084}),

# pick_time.min between 2 and 90 minutes + remove 2 std devs

201118 orders

'odt_items_total': 29.58483,
'store_name': 20.57271,
'courier_id': 13.34292,
'courier_orders_taken': 12.08287,
'odt_items_with_variable_weight': 6.57526,
'courier_created_days': 3.63356,
'store_province': 3.21658,
'order_fulfillment_type': 3.11119,
'store_area': 2.63937,
'order_deliver_at_start.month': 2.16531,
'courier_area': 1.34399,
'store_ref_id': 0.66952,
'order_deliver_at_start.hour': 0.40683,
'order_deliver_at_start.year': 0.29515,
'order_deliver_at_start.dayofweek': 0.21147,
'order_deliver_at_start.day': 0.14845

'scores',
    'best_iteration': 40,
    'best_score': {'training': {'RMSE': 7.899196730808206},
    'validation': {'RMSE': 9.347241332491311}},

'median_abs_error': 5.5851,
'mean_abs_error': 7.06564,
'sqrt_mean_squared_error': 9.34724,
'model_size': 4895920}),

# pick_time.min between 2 and 90 minutes
# pick_time.min 3 standard devs
# odt_items_total 4 standard devs (cuts order with > 79 items)

Filtered orders: 209584

'odt_items_total': 26.28875,
'store_province': 17.1903,
'courier_orders_taken': 14.67496,
'courier_id': 12.14154,
'store_name': 9.58368,
'odt_items_with_variable_weight': 5.81459,
'order_deliver_at_start.month': 3.27118,
'courier_created_days': 3.22207,
'order_fulfillment_type': 2.03827,
'store_area': 1.69513,
'courier_area': 1.58365,
'order_deliver_at_start.year': 0.57667,
'order_deliver_at_start.hour': 0.51224,
'store_ref_id': 0.4798,
'order_deliver_at_start.minute': 0.4282,
'order_deliver_at_start.day': 0.25141,
'order_deliver_at_start.dayofweek': 0.24756

'median_abs_error': 5.32896,
'mean_abs_error': 7.19731,
'sqrt_mean_squared_error': 10.12843,
'model_size': 6559016

'scores',
    'best_iteration': 50,
    'best_score': {'training': {'RMSE': 9.572413519739023},
    'validation': {'RMSE': 10.12843408941726}},


# pick_time.min between 2 and 90 minutes
# pick_time.min 3 standard devs
# odt_items_total 3 standard devs (cuts order with > 65 items)

Filtered orders: 207593

'odt_items_total': 31.59184,
'courier_id': 12.69186,
'courier_orders_taken': 11.78631,
'store_province': 10.84889,
'store_name': 9.93686,
'odt_items_with_variable_weight': 5.69991,
'courier_created_days': 3.42232,
'order_deliver_at_start.month': 3.2041,
'courier_area': 2.8976,
'order_fulfillment_type': 2.48266,
'order_deliver_at_start.year': 1.54361,
'store_area': 1.23723,
'store_ref_id': 1.23588,
'order_deliver_at_start.hour': 0.77335,
'order_deliver_at_start.day': 0.39115,
'order_deliver_at_start.dayofweek': 0.18644,
'order_deliver_at_start.minute': 0.06999

'median_abs_error': 5.30632,
'mean_abs_error': 7.14319,
'sqrt_mean_squared_error': 10.05169,
'model_size': 57613446

'scores',
    'best_iteration': 67,
    'best_score': {'training': {'RMSE': 9.518770359690187},
    'validation': {'RMSE': 10.051686844002946}},