
# Predictions

## Out Of Stock

This recipe combines "order_detail", "order" and "store" information to determine the likelyhood that an item specified by its "odt_ean" will not be found in a specific store at a specific time in the future. The training dataset has around 5 million lines.

POST Request an outofstock prediction:  
`/api/endpoints/ep_s24_outofstock/predict`

Payload example:
```json
{
	"data": [
		{
			"sto_name": "pam",
			"sto_area": "BO1",
			"sto_province": "BO",
			"sto_ref_id": 3742,
			"odt_ean": "8033737490006",
			"odt_category_id": 261,
			"odt_replaceable": 3,
			"odt_variable_weight": 0,
			"odt_price": 1.5,
			"odt_price_per_type": 0.01,
			"odt_surcharge_fixed": -0.55,
			"odt_touched_at": "2019-03-01 08:05:04"
		},
		{
			"odt_ean": "8003170059580",
			"odt_category_id": 258,
			"odt_replaceable": 3,
			"odt_variable_weight": 0,
			"odt_price": 1.19,
			"odt_price_per_type": 4.0,
			"odt_surcharge_fixed": -0.2,
			"odt_touched_at": "2019-03-01 14:34:00",
			"sto_name": "conad superstore",
			"sto_area": "RN1",
			"sto_province": "RN",
			"sto_ref_id": 4075
		}
	]
}
```

Response example:  
```json
{
  "data": {
    "type": "analitico/prediction",
    "endpoint_id": "ep_s24_outofstock",
    "model_id": "ml_VLMv2G7ErqDB",
    "job_id": "jb_2qTrWMf4IPKI",
    "records": [
      {
        "odt_category_id": 261,
        "odt_ean": "8033737490006",
        "odt_price": 1.5,
        "odt_price_per_type": 0.01,
        "odt_replaceable": 3,
        "odt_surcharge_fixed": -0.55,
        "odt_touched_at": "2019-03-01 08:05:04",
        "odt_variable_weight": 0,
        "sto_area": "BO1",
        "sto_name": "pam",
        "sto_province": "BO",
        "sto_ref_id": 3742
      },
      {
        "odt_category_id": 258,
        "odt_ean": "8003170059580",
        "odt_price": 1.19,
        "odt_price_per_type": 4.0,
        "odt_replaceable": 3,
        "odt_surcharge_fixed": -0.2,
        "odt_touched_at": "2019-03-01 14:34:00",
        "odt_variable_weight": 0,
        "sto_area": "RN1",
        "sto_name": "conad superstore",
        "sto_province": "RN",
        "sto_ref_id": 4075
      }
    ],
    "processed": [
      {
        "odt_category_id": 261,
        "odt_category_id.level2": 100113,
        "odt_category_id.level3": 3,
        "odt_ean": "8033737490006",
        "odt_price": 1.5,
        "odt_price_per_type": 0.01,
        "odt_replaceable": 3,
        "odt_surcharge_fixed": -0.55,
        "odt_touched_at": "2019-03-01T08:05:04Z",
        "odt_variable_weight": 0,
        "odt_touched_at.year": 2019,
        "odt_touched_at.month": 3,
        "odt_touched_at.day": 1,
        "odt_touched_at.hour": 8,
        "odt_touched_at.minute": 5,
        "odt_touched_at.dayofweek": 4,
        "sto_area": "BO1",
        "sto_name": "pam",
        "sto_province": "BO",
        "sto_ref_id": 3742,
        "dyn_price": 1.5,
        "dyn_price_promo": 0.633333,
        "dyn_purchased": 0
      },
      {
        "odt_category_id": 258,
        "odt_category_id.level2": 100113,
        "odt_category_id.level3": 3,
        "odt_ean": "8003170059580",
        "odt_price": 1.19,
        "odt_price_per_type": 4.0,
        "odt_replaceable": 3,
        "odt_surcharge_fixed": -0.2,
        "odt_touched_at": "2019-03-01T14:34:00Z",
        "odt_variable_weight": 0,
        "odt_touched_at.year": 2019,
        "odt_touched_at.month": 3,
        "odt_touched_at.day": 1,
        "odt_touched_at.hour": 14,
        "odt_touched_at.minute": 34,
        "odt_touched_at.dayofweek": 4,
        "sto_area": "RN1",
        "sto_name": "conad superstore",
        "sto_province": "RN",
        "sto_ref_id": 4075,
        "dyn_price": 1.19,
        "dyn_price_promo": 0.831933,
        "dyn_purchased": 0
      }
    ],
    "predictions": [
      "PURCHASED",
      "PURCHASED"
    ],
    "probabilities": [
      {
        "NOT_PURCHASED": 0.2033760004023878,
        "PURCHASED": 0.7966239995976122
      },
      {
        "NOT_PURCHASED": 0.06607462645278162,
        "PURCHASED": 0.9339253735472184
      }
    ],
    "performance": {
      "cpu_count": 12,
      "loading_ms": 1,
      "total_ms": 1293
    }
  }
}
```

#### Related Links

**ds_s24_order_detail**: dataset with order details  
https://s24.analitico.ai/api/datasets/ds_s24_order_detail

**ds_s24_order**: dataset with orders  
https://s24.analitico.ai/api/datasets/ds_s24_order

**ds_s24_store**: dataset with stores  
https://s24.analitico.ai/api/datasets/ds_s24_store

**ds_s24_outofstock**: combined dataset with merged details, orders, stores    
https://s24.analitico.ai/api/datasets/ds_s24_outofstock

**rx_s24_outofstock**: recipe used to train outofstock model      
https://s24.analitico.ai/api/recipes/rx_s24_outofstock

**ml_VLMv2G7ErqDB**: trained model (may be out of date or not the latest)      
https://s24.analitico.ai/api/models/ml_VLMv2G7ErqDB

**ep_s24_outofstock**: prediction endpoint with link to current trained model      
https://s24.analitico.ai/api/endpoints/ep_s24_outofstock




