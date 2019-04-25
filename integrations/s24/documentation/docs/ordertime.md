
# Predictions

## Order Time

These recipes use joined data from "order", "order_detail", "order_timestamps", "store" and "customer" which contains a few hundred thousand completed orders with: aggregate number of items, store info, customer info and labels for picking time at the store, time to pay at cashier and time to deliver.

The notebooks used to produce the training data can be found in `/notebooks`. This code will be moved into the ingestion pipelines and run automatically as soon as we confirm the models are working as needed and have all the data they need.

Three different recipies are built using a gradient boosting regressor and targeting the pick_time.min, pay_time.min and deliver_time.min labels.

### Picking time

POST Request a picking time prediction and get a results:  
`/api/endpoints/ep_s24_pick_time/predict`

Payload example:
```json
{
    "data": [
        {
            "order_amount": 26.13,
            "order_volume": 77.32,
            "order_deliver_at_start": "2018-09-11 13:00:00",
            "order_fulfillment_type": "1",
            "items_total": 9,
            "items_with_variable_weight": 0,
            "store_name": "coop",
            "store_province": "MI",
            "store_lat": 45.470281,
            "store_lng": 9.109733,
            "store_area": "MI5",
            "store_ref_id": "5169",
            "customer_province": "MI",
            "customer_lat": 45.4511124,
            "customer_lng": 9.1558412,
            "customer_area": "MI5",
            "customer_ztl": "0",
            "customer_ref_id": "0000954909",
            "customer_has_subscription": "0"
        },
        {
            "order_amount": 27.05,
            "order_volume": 84.06,
            "order_deliver_at_start": "2018-09-04 09:00:00",
            "order_fulfillment_type": "1",
            "items_total": 8,
            "items_with_variable_weight": 4,
            "store_name": "coop",
            "store_province": "RM",
            "store_lat": 41.850817,
            "store_lng": 12.494866,
            "store_area": "RM5",
            "store_ref_id": "387",
            "customer_province": "RM",
            "customer_lat": 41.852604,
            "customer_lng": 12.4808448,
            "customer_area": "RM5",
            "customer_ztl": "0",
            "customer_ref_id": "0000686053",
            "customer_has_subscription": "0"
        }
    ]
}
```
Response example:  
```json
{
  "data": {
    "type": "analitico/prediction",  
    "records": [
      {
        "order_amount": 26.13,
        "order_volume": 77.32,
        "order_deliver_at_start": "2018-09-11 13:00:00",
        "order_fulfillment_type": "1",
        "items_total": 9,
        "items_with_variable_weight": 0,
        "store_name": "coop",
        "store_province": "MI",
        "store_lat": 45.470281,
        "store_lng": 9.109733,
        "store_area": "MI5",
        "store_ref_id": "5169",
        "customer_province": "MI",
        "customer_lat": 45.4511124,
        "customer_lng": 9.1558412,
        "customer_area": "MI5",
        "customer_ztl": "0",
        "customer_ref_id": "0000954909",
        "customer_has_subscription": "0"
      },
      {
        "order_amount": 27.05,
        "order_volume": 84.06,
        "order_deliver_at_start": "2018-09-04 09:00:00",
        "order_fulfillment_type": "1",
        "items_total": 8,
        "items_with_variable_weight": 4,
        "store_name": "coop",
        "store_province": "RM",
        "store_lat": 41.850817,
        "store_lng": 12.494866,
        "store_area": "RM5",
        "store_ref_id": "387",
        "customer_province": "RM",
        "customer_lat": 41.852604,
        "customer_lng": 12.4808448,
        "customer_area": "RM5",
        "customer_ztl": "0",
        "customer_ref_id": "0000686053",
        "customer_has_subscription": "0"
      }
    ],
    "predictions": [
      12.289,
      14.834
    ],
    "performance": {
      "cpu_count": 8,
      "loading_ms": 0,
      "total_ms": 20,
      "assets_ms": 0
    },
    "model_id": "ml_Sf8n6qx6iUbE",
    "endpoint_id": "ep_s24_pick_time",
    "job_id": "jb_RRXWTVuc8BQ8"
  }
}
```

### Pay time

POST Request a prediction of time spent to pay for an order:    
`/api/endpoints/ep_s24_pay_time/predict`  
Same payload and response formats as picking time.

### Deliver time

POST Request a prediction of time spent to deliver an order:    
`/api/endpoints/ep_s24_deliver_time/predict`  
Same payload and response formats as picking time.


### Picking Time with Courier Id

The payload here is the same as the call for picking time plus the courier information.

You can provide the following courier information fields:  

*courier_id*: internal id of courier doing the shopping  
*courier_area*: area where courier operates, eg: MI1  
*courier_orders_taken*: number of orders the courier has taken at the time of this order  
*courier_experience_days*: number of days passed since courier started  

As an alternative you can just provide the *courier_id* and the remaining information will be filled in automatically.

POST Request a prediction of time spent to pay for an order:    
`/api/endpoints/ep_s24_pay_time_with_courier/predict`  
Same payload and response formats as picking time.

Payload example:
```json
{
	"data": [
		{
			"order_fulfillment_type": 1,
			"order_deliver_at_start": "2019-08-27 19:00:00",
			"courier_id": 109135,
			"odt_items_total": 120,
			"odt_items_with_variable_weight": 0,
			"store_name": "esselunga",
			"store_area": "MI6",
			"store_province": "MI",
			"store_ref_id": 5042
		},
		{
			"order_fulfillment_type": 1,
			"order_deliver_at_start": "2019-09-28 20:00:00",
			"courier_id": 112148,
			"odt_items_total": 16,
			"odt_items_with_variable_weight": 1,
			"store_name": "ipercoop",
			"store_area": "MI4",
			"store_province": "MI",
			"store_ref_id": 4494
		}
	]
}
```

Response example:  
```json
{
  "data": {
    "type": "analitico/prediction",
    "performance": {
      "cpu_count": 12,
      "loading_ms": 3,
      "total_ms": 786
    },
    "records": [
      {
        "order_fulfillment_type": 1,
        "courier_id": 109135,
        "odt_items_total": 120,
        "odt_items_with_variable_weight": 0,
        "store_name": "esselunga",
        "store_area": "MI6",
        "store_province": "MI",
        "store_ref_id": 5042,
        "courier_area": "MI13",
        "courier_orders_taken": 249,
        "courier_experience_days": 671,
        "order_deliver_at_start.year": 2019,
        "order_deliver_at_start.month": 8,
        "order_deliver_at_start.day": 27,
        "order_deliver_at_start.hour": 19,
        "order_deliver_at_start.minute": 0,
        "order_deliver_at_start.dayofweek": 1
      },
      {
        "order_fulfillment_type": 1,
        "courier_id": 112148,
        "odt_items_total": 16,
        "odt_items_with_variable_weight": 1,
        "store_name": "ipercoop",
        "store_area": "MI4",
        "store_province": "MI",
        "store_ref_id": 4494,
        "courier_area": null,
        "courier_orders_taken": 0,
        "courier_experience_days": 183,
        "order_deliver_at_start.year": 2019,
        "order_deliver_at_start.month": 9,
        "order_deliver_at_start.day": 28,
        "order_deliver_at_start.hour": 20,
        "order_deliver_at_start.minute": 0,
        "order_deliver_at_start.dayofweek": 5
      }
    ],
    "predictions": [
      52.983,
      36.612
    ],
    "model_id": "ml_ATeElrXrJYpT",
    "endpoint_id": "ep_s24_pick_time_with_courier"
  }
}
```
