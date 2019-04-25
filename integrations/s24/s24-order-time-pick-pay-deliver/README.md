
# Pick, pay and deliver times predictions

These recipes use joined data from "order", "order_detail", "order_timestamps", "store" and "customer" which contains a few hundred thousand completed orders with: aggregate number of items, store info, customer info and labels for picking time at the store, time to pay at cashier and time to deliver.

The notebooks used to produce the training data can be found in `/notebooks`. This code will be moved into the ingestion pipelines and run automatically as soon as we confirm the models are working as needed and have all the data they need.

Three different recipies are built using a gradient boosting regressor and targeting the pick_time.min, pay_time.min and deliver_time.min labels.

All calls can be made by passing the authentication token in  
the https headers as "Bearer tok_s24_579E5hOWw7k8" or by passing  
the url parameter ?token=tok_s24_579E5hOWw7k8  

Examples:  
https://staging.analitico.ai/api/datasets/ds_s24_order_time_pick_pay_deliver?token=tok_s24_579E5hOWw7k8

Endpoint have been omitted in the following instructions. If you use Insomina (on Ubuntu) to make test calls to APIs you can find a working set in `insomnia-workspace.json`.

## Picking time

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

## Pay time

POST Request a prediction of time spent to pay for an order:    
`/api/endpoints/ep_s24_pay_time/predict`  
Same payload and response formats as picking time.

## Deliver time

POST Request a prediction of time spent to deliver an order:    
`/api/endpoints/ep_s24_deliver_time/predict`  
Same payload and response formats as picking time.

## More endpoints  

GET See dataset that was uploaded and its schema:  
`/api/datasets/ds_s24_order_time_pick_pay_deliver?token=tok_s24_579E5hOWw7k8`
```json
{
  "data": {
    "type": "dataset",
    "id": "ds_s24_order_time_pick_pay_deliver",
    "attributes": {
      "title": "",
      "description": "Orders joined with:  \r\n- order_detail for total of items and items of variable weight\r\n- order_timestamp for first and last picked detail, pay time, delivery time\r\n- store for location, etc\r\n- customer for location, etc",
      "created_at": "2019-02-11T12:33:49.616720+01:00",
      "updated_at": "2019-02-12T08:05:48.522603+01:00",
      "workspace": "ws_s24",
      "assets": [
        {
          "id": "data.csv",
          "created_at": "2019-02-12T06:49:35.772892+00:00",
          "filename": "100-order-time-pick-pay-deliver.csv",
          "path": "workspaces/ws_s24/datasets/ds_s24_order_time_pick_pay_deliver/assets/data.csv",
          "hash": "ac8cc768543401b48b5eea592c240635",
          "content_type": "text/csv",
          "size": 119645217,
          "url": "https://analitico.test:8000/api/datasets/ds_s24_order_time_pick_pay_deliver/assets/data.csv"
        }
      ],
      "plugin": {
        "type": "analitico/plugin",
        "name": "analitico.plugin.DataframePipelinePlugin",
        "plugins": [
          {
            "type": "analitico/plugin",
            "name": "analitico.plugin.CsvDataframeSourcePlugin",
            "source": {
              "content_type": "text/csv",
              "url": "workspaces/ws_s24/datasets/ds_s24_order_time_pick_pay_deliver/assets/data.csv",
              "schema": {
                "columns": [
                  {
                    "name": "order_amount",
                    "type": "float"
                  },
                  {
                    "name": "order_volume",
                    "type": "float"
                  },
                  {
                    "name": "order_deliver_at_start.dayofweek",
                    "type": "integer"
                  },
                  {
                    "name": "order_deliver_at_start.year",
                    "type": "integer"
                  },
                  {
                    "name": "order_deliver_at_start.month",
                    "type": "integer"
                  },
                  {
                    "name": "order_deliver_at_start.day",
                    "type": "integer"
                  },
                  {
                    "name": "order_deliver_at_start.hour",
                    "type": "integer"
                  },
                  {
                    "name": "order_deliver_at_start.minute",
                    "type": "integer"
                  },
                  {
                    "name": "order_deliver_at_end",
                    "type": "string"
                  },
                  {
                    "name": "order_fulfillment_type",
                    "type": "category"
                  },
                  {
                    "name": "items_total",
                    "type": "integer"
                  },
                  {
                    "name": "items_with_variable_weight",
                    "type": "integer"
                  },
                  {
                    "name": "store_name",
                    "type": "category"
                  },
                  {
                    "name": "store_province",
                    "type": "category"
                  },
                  {
                    "name": "store_lat",
                    "type": "float"
                  },
                  {
                    "name": "store_lng",
                    "type": "float"
                  },
                  {
                    "name": "store_area",
                    "type": "category"
                  },
                  {
                    "name": "store_ref_id",
                    "type": "category"
                  },
                  {
                    "name": "customer_province",
                    "type": "category"
                  },
                  {
                    "name": "customer_lat",
                    "type": "float"
                  },
                  {
                    "name": "customer_lng",
                    "type": "float"
                  },
                  {
                    "name": "customer_area",
                    "type": "category"
                  },
                  {
                    "name": "customer_ztl",
                    "type": "category"
                  },
                  {
                    "name": "customer_ref_id",
                    "type": "category"
                  },
                  {
                    "name": "customer_has_subscription",
                    "type": "category"
                  },
                  {
                    "name": "pick_time.min",
                    "type": "float"
                  },
                  {
                    "name": "pay_time.min",
                    "type": "float"
                  },
                  {
                    "name": "deliver_time.min",
                    "type": "float"
                  }
                ]
              }
            }
          }
        ]
      },
      "data": [
        {
          "id": "data.csv",
          "created_at": "2019-02-12T07:05:48.127092+00:00",
          "filename": "data.csv",
          "path": "workspaces/ws_s24/datasets/ds_s24_order_time_pick_pay_deliver/data/data.csv",
          "hash": "4f784b36fe67da7ae9efd7e558f228f6",
          "content_type": "text/csv",
          "size": 51287723,
          "url": "https://analitico.test:8000/api/datasets/ds_s24_order_time_pick_pay_deliver/data/data.csv",
          "schema": {
            "columns": [
            ]
            }
          }
        }
      ]
    },
    "links": {
      "self": "https://analitico.test:8000/api/datasets/ds_s24_order_time_pick_pay_deliver"
    }
  }
}
```

POST Train pay time model, retrieve training job:  
`/api/recipes/rx_s24_pay_time/jobs/train`  
```json
{
  "data": {
    "type": "job",
    "id": "jb_zyJLGbwzGkcH",
    "attributes": {
      "title": "",
      "description": "",
      "created_at": "2019-02-12T08:24:14.610234+01:00",
      "updated_at": "2019-02-12T08:24:39.306884+01:00",
      "status": "completed",
      "action": "recipe/train",
      "item_id": "rx_s24_pick_time",
      "workspace": "ws_s24",
      "recipe_id": "rx_s24_pick_time",
      "model_id": "ml_Six56CXnaies"
    },
    "links": {
      "self": "/api/jobs/jb_zyJLGbwzGkcH",
      "related": "/api/recipes/rx_s24_pick_time",
      "model": "/api/recipes/rx_s24_pick_time"
    }
  }
}
```

GET See trained model and scores:  
`/api/models/ml_Six56CXnaies`  
```json
{
  "data": {
    "type": "model",
    "id": "ml_Six56CXnaies",
    "attributes": {
      "title": "",
      "description": "",
      "created_at": "2019-02-12T08:19:54.041294+01:00",
      "updated_at": "2019-02-12T08:19:55.628541+01:00",
      "workspace": "ws_s24",
      "data": [
        {
          "id": "training.json",
          "created_at": "2019-02-12T07:19:54.417736+00:00",
          "filename": "training.json",
          "path": "workspaces/ws_s24/models/ml_Six56CXnaies/data/training.json",
          "hash": "e270c37983ea0bd4aff0b4c054b559c3",
          "content_type": "application/json",
          "size": 5306,
          "url": "https://analitico.test:8000/api/models/ml_Six56CXnaies/data/training.json"
        },
        {
          "id": "model.cbm",
          "created_at": "2019-02-12T07:19:55.106219+00:00",
          "filename": "model.cbm",
          "path": "workspaces/ws_s24/models/ml_Six56CXnaies/data/model.cbm",
          "hash": "934c662a178b5549f27f7c898e5f5663",
          "content_type": null,
          "size": 1087264,
          "url": "https://analitico.test:8000/api/models/ml_Six56CXnaies/data/model.cbm"
        },
        {
          "id": "test.csv",
          "created_at": "2019-02-12T07:19:55.368200+00:00",
          "filename": "test.csv",
          "path": "workspaces/ws_s24/models/ml_Six56CXnaies/data/test.csv",
          "hash": "0e1178445c730054013e5d1c3b50eeaf",
          "content_type": "text/csv",
          "size": 17308,
          "url": "https://analitico.test:8000/api/models/ml_Six56CXnaies/data/test.csv"
        }
      ],
      "recipe_id": "rx_s24_pay_time",
      "job_id": "jb_QPSj4CHxPl1R",
      "training": {
        "type": "analitico/training",
        "plugins": {
          "training": "analitico.plugin.CatBoostRegressorPlugin",
          "prediction": "analitico.plugin.CatBoostRegressorPlugin"
        },
        "data": {
          "label": "pay_time.min",
          "chronological": false,
          "schema": {
            "columns": [
              {
                "name": "order_amount",
                "type": "float"
              },
              {
                "name": "order_volume",
                "type": "float"
              },
              {
                "name": "order_deliver_at_start.dayofweek",
                "type": "integer"
              },
              {
                "name": "order_deliver_at_start.year",
                "type": "integer"
              },
              {
                "name": "order_deliver_at_start.month",
                "type": "integer"
              },
              {
                "name": "order_deliver_at_start.day",
                "type": "integer"
              },
              {
                "name": "order_deliver_at_start.hour",
                "type": "integer"
              },
              {
                "name": "order_deliver_at_start.minute",
                "type": "integer"
              },
              {
                "name": "order_fulfillment_type",
                "type": "category"
              },
              {
                "name": "items_total",
                "type": "integer"
              },
              {
                "name": "items_with_variable_weight",
                "type": "integer"
              },
              {
                "name": "store_name",
                "type": "category"
              },
              {
                "name": "store_province",
                "type": "category"
              },
              {
                "name": "store_lat",
                "type": "float"
              },
              {
                "name": "store_lng",
                "type": "float"
              },
              {
                "name": "store_area",
                "type": "category"
              },
              {
                "name": "store_ref_id",
                "type": "category"
              },
              {
                "name": "customer_province",
                "type": "category"
              },
              {
                "name": "customer_lat",
                "type": "float"
              },
              {
                "name": "customer_lng",
                "type": "float"
              },
              {
                "name": "customer_area",
                "type": "category"
              },
              {
                "name": "customer_ztl",
                "type": "category"
              },
              {
                "name": "customer_ref_id",
                "type": "category"
              },
              {
                "name": "customer_has_subscription",
                "type": "category"
              },
              {
                "name": "pay_time.min",
                "type": "float"
              }
            ]
          },
          "source_records": 280025,
          "training_records": 224020,
          "test_records": 56005,
          "dropped_records": 0
        },
        "parameters": {
          "test_size": 0.2,
          "iterations": 50,
          "learning_rate": 1,
          "depth": 8,
          "loss_function": "RMSE"
        },
        "scores": {
          "median_abs_error": 4.46809,
          "mean_abs_error": 6.41043,
          "sqrt_mean_squared_error": 10.14899,
          "best_iteration": 12,
          "best_score": {
            "learn": {
              "RMSE": 9.920182719026212
            },
            "validation_0": {
              "RMSE": 10.148989274910106
            }
          },
          "features_importance": {
            "store_name": 20.19772,
            "order_fulfillment_type": 14.38666,
            "customer_area": 10.53602,
            "order_amount": 10.19153,
            "store_area": 9.80745,
            "order_deliver_at_start.month": 7.43324,
            "store_ref_id": 5.29614,
            "order_deliver_at_start.hour": 5.21735,
            "store_lat": 4.98405,
            "order_deliver_at_start.year": 2.23323,
            "items_total": 1.42861,
            "customer_province": 1.34337,
            "customer_lng": 1.25326,
            "order_deliver_at_start.day": 1.16772,
            "store_lng": 1.16673,
            "order_deliver_at_start.dayofweek": 0.77782,
            "items_with_variable_weight": 0.69562,
            "customer_lat": 0.64289,
            "order_volume": 0.59351,
            "customer_ztl": 0.48185,
            "store_province": 0.16524,
            "order_deliver_at_start.minute": 0.0,
            "customer_ref_id": 0.0,
            "customer_has_subscription": 0.0
          },
          "model_size": 1087264
        },
        "performance": {
          "cpu_count": 12,
          "training_ms": 18630,
          "total_ms": 22159
        }
      }
    },
    "links": {
      "self": "https://analitico.test:8000/api/models/ml_Six56CXnaies"
    }
  }
}
```

## Retraining

The data right now is created by aJupyter notebook. As soon as we verify the model is working and has all the data we need, it will then be converted to a pipeline starting from the base data tables by moving the code in the Jupyter notebook into the dataset pipeline.  
`/notebooks/100-order-time-pick-pay-deliver.ipynb`

POST Upload new data to the dataset using multipart upload:  
`/api/datasets/ds_s24_order_time_pick_pay_deliver/assets/data.csv`

POST Reprocess the data throug processing pipeline:  
`/api/datasets/ds_s24_order_time_pick_pay_deliver/data/process`
