
# Predictions

## Order Sorting

This recipe combines "order_detail", "order" and "store" information to estimate the distance in seconds between tomatoes and milk or cookies and water in a store. We then use this model to analyze a shopping basket. By predicting the likely distance in seconds between each couple of items in the basket we can calculate the optimal route that will make us pick up all items in the shortest time.

It is possible to sort one or more baskets at once by passing one or more orders in the "data" parameter when posting to the prediction endpoint.

POST Request reordering of an order:  
`/api/endpoints/ep_s24_ordersorting/predict`

Payload example:
```json
{
	"data": [
		{
			"ord_id": 980188.0,
			"sto_ref_id": 326.0,
			"sto_name": "carrefour market",
			"sto_area": "RM8",
			"sto_province": "RM",
			"details": [
				{
					"odt_id": 19415192,
					"odt_ean": 8024666500072.0,
					"odt_name": "Carrefour Bio Limoni bio",
					"odt_category_id": 251
				},
				{
					"odt_id": 19415196,
					"odt_ean": 2002146130003.0,
					"odt_name": "Ananas ",
					"odt_category_id": 254
				},
				{
					"odt_id": 19415194,
					"odt_ean": 2002054130003.0,
					"odt_name": "Peperoni Rossi ",
					"odt_category_id": 261
				},
				{
					"odt_id": 19415198,
					"odt_ean": 2002322130001.0,
					"odt_name": "Peperoni Gialli ",
					"odt_category_id": 261
				},
				{
					"odt_id": 19415180,
					"odt_ean": 8004381107008.0,
					"odt_name": "Mele Alto Adige Igp Golden Delicious Italia Cal. i 80-85 Mm 0,900 Kg",
					"odt_category_id": 252
				},
				{
					"odt_id": 19415200,
					"odt_ean": 2002135130007.0,
					"odt_name": "Arance Navelinas ",
					"odt_category_id": 251
				},
				{
					"odt_id": 19415188,
					"odt_ean": 8032603412043.0,
					"odt_name": "Carrefour Pomodoro Datterino 250 Gr.",
					"odt_category_id": 260
				},
				{
					"odt_id": 19415176,
					"odt_ean": 8013165060057.0,
					"odt_name": "Zorbas Light Formaggio Greco Magro",
					"odt_category_id": 286
				},
				{
					"odt_id": 19415190,
					"odt_ean": 3245414229228.0,
					"odt_name": "Carrefour Formaggio Fresco di Capra",
					"odt_category_id": 298
				},
				{
					"odt_id": 19415184,
					"odt_ean": 8010292009874.0,
					"odt_name": "Insalata belga  ",
					"odt_category_id": 264
				},
				{
					"odt_id": 19415178,
					"odt_ean": 8033661091003.0,
					"odt_name": "Amaltea Formaggio Bocconcino di Capra",
					"odt_category_id": 298
				},
				{
					"odt_id": 19415182,
					"odt_ean": 8001350020627.0,
					"odt_name": "Carrefour Bio Pomodori Pelati",
					"odt_category_id": 450
				},
				{
					"odt_id": 19415172,
					"odt_ean": 9001475062341.0,
					"odt_name": "Pompadour Zenzero Limone per Infuso",
					"odt_category_id": 422
				},
				{
					"odt_id": 19415170,
					"odt_ean": 8007185002722.0,
					"odt_name": "Everton Karkadè, Infuso Bio",
					"odt_category_id": 422
				},
				{
					"odt_id": 19415186,
					"odt_ean": 8012666041916.0,
					"odt_name": "Carrefour Bio Polpa di Pomodoro in Succo di Pomodoro",
					"odt_category_id": 451
				},
				{
					"odt_id": 19415168,
					"odt_ean": 8002280003506.0,
					"odt_name": "Gemma di Mare Gli Integrali Sale Marino del Mediterraneo Grosso",
					"odt_category_id": 6009
				},
				{
					"odt_id": 19415174,
					"odt_ean": 8020141810001.0,
					"odt_name": "Sant'Anna Naturale Sorgente Rebruant ",
					"odt_category_id": 691
				},
				{
					"odt_id": 19415174,
					"odt_ean": 8020141810001.0,
					"odt_name": "Sant'Anna Naturale Sorgente Rebruant ",
					"odt_category_id": -2
				}
			]
		}
	]
}
```

Response example:  
```json
{
  "data": {
    "type": "analitico/prediction",
    "endpoint_id": "ep_s24_ordersorting",
    "model_id": "ml_ZRC1tZSG7x1R",
    "job_id": "jb_W90KuY3yPbP3",
    "records": [
      {
        "ord_id": 980188.0,
        "sto_ref_id": 326.0,
        "sto_name": "carrefour market",
        "sto_area": "RM8",
        "sto_province": "RM",
        "details": [
          {
            "odt_id": 19415192,
            "odt_ean": 8024666500072.0,
            "odt_name": "Carrefour Bio Limoni bio",
            "odt_category_id": 251
          },
          {
            "odt_id": 19415196,
            "odt_ean": 2002146130003.0,
            "odt_name": "Ananas ",
            "odt_category_id": 254
          },
          {
            "odt_id": 19415194,
            "odt_ean": 2002054130003.0,
            "odt_name": "Peperoni Rossi ",
            "odt_category_id": 261
          },
          {
            "odt_id": 19415198,
            "odt_ean": 2002322130001.0,
            "odt_name": "Peperoni Gialli ",
            "odt_category_id": 261
          },
          {
            "odt_id": 19415180,
            "odt_ean": 8004381107008.0,
            "odt_name": "Mele Alto Adige Igp Golden Delicious Italia Cal. i 80-85 Mm 0,900 Kg",
            "odt_category_id": 252
          },
          {
            "odt_id": 19415200,
            "odt_ean": 2002135130007.0,
            "odt_name": "Arance Navelinas ",
            "odt_category_id": 251
          },
          {
            "odt_id": 19415188,
            "odt_ean": 8032603412043.0,
            "odt_name": "Carrefour Pomodoro Datterino 250 Gr.",
            "odt_category_id": 260
          },
          {
            "odt_id": 19415176,
            "odt_ean": 8013165060057.0,
            "odt_name": "Zorbas Light Formaggio Greco Magro",
            "odt_category_id": 286
          },
          {
            "odt_id": 19415190,
            "odt_ean": 3245414229228.0,
            "odt_name": "Carrefour Formaggio Fresco di Capra",
            "odt_category_id": 298
          },
          {
            "odt_id": 19415184,
            "odt_ean": 8010292009874.0,
            "odt_name": "Insalata belga  ",
            "odt_category_id": 264
          },
          {
            "odt_id": 19415178,
            "odt_ean": 8033661091003.0,
            "odt_name": "Amaltea Formaggio Bocconcino di Capra",
            "odt_category_id": 298
          },
          {
            "odt_id": 19415182,
            "odt_ean": 8001350020627.0,
            "odt_name": "Carrefour Bio Pomodori Pelati",
            "odt_category_id": 450
          },
          {
            "odt_id": 19415172,
            "odt_ean": 9001475062341.0,
            "odt_name": "Pompadour Zenzero Limone per Infuso",
            "odt_category_id": 422
          },
          {
            "odt_id": 19415170,
            "odt_ean": 8007185002722.0,
            "odt_name": "Everton Karkadè, Infuso Bio",
            "odt_category_id": 422
          },
          {
            "odt_id": 19415186,
            "odt_ean": 8012666041916.0,
            "odt_name": "Carrefour Bio Polpa di Pomodoro in Succo di Pomodoro",
            "odt_category_id": 451
          },
          {
            "odt_id": 19415168,
            "odt_ean": 8002280003506.0,
            "odt_name": "Gemma di Mare Gli Integrali Sale Marino del Mediterraneo Grosso",
            "odt_category_id": 6009
          },
          {
            "odt_id": 19415174,
            "odt_ean": 8020141810001.0,
            "odt_name": "Sant'Anna Naturale Sorgente Rebruant ",
            "odt_category_id": 691
          },
          {
            "odt_id": 19415174,
            "odt_ean": 8020141810001.0,
            "odt_name": "Sant'Anna Naturale Sorgente Rebruant ",
            "odt_category_id": -2
          }
        ]
      }
    ],
    "predictions": [
      {
        "ord_id": 980188.0,
        "sto_ref_id": 326.0,
        "sto_name": "carrefour market",
        "sto_area": "RM8",
        "sto_province": "RM",
        "details": [
          {
            "odt_id": 19415198,
            "odt_ean": 2002322130001.0,
            "odt_name": "Peperoni Gialli ",
            "odt_category_id": 261,
            "odt_category_id.slug": "altre-verdure",
            "odt_category_id.level2": 100113,
            "odt_category_id.level2.slug": "verdura-fresca",
            "odt_category_id.level3": 3,
            "odt_category_id.level3.slug": "frutta-verdura"
          },
          {
            "odt_id": 19415188,
            "odt_ean": 8032603412043.0,
            "odt_name": "Carrefour Pomodoro Datterino 250 Gr.",
            "odt_category_id": 260,
            "odt_category_id.slug": "pomodori",
            "odt_category_id.level2": 100113,
            "odt_category_id.level2.slug": "verdura-fresca",
            "odt_category_id.level3": 3,
            "odt_category_id.level3.slug": "frutta-verdura"
          },
          {
            "odt_id": 19415184,
            "odt_ean": 8010292009874.0,
            "odt_name": "Insalata belga  ",
            "odt_category_id": 264,
            "odt_category_id.slug": "insalate-insalata-radicchi",
            "odt_category_id.level2": 100113,
            "odt_category_id.level2.slug": "verdura-fresca",
            "odt_category_id.level3": 3,
            "odt_category_id.level3.slug": "frutta-verdura"
          },
          {
            "odt_id": 19415194,
            "odt_ean": 2002054130003.0,
            "odt_name": "Peperoni Rossi ",
            "odt_category_id": 261,
            "odt_category_id.slug": "altre-verdure",
            "odt_category_id.level2": 100113,
            "odt_category_id.level2.slug": "verdura-fresca",
            "odt_category_id.level3": 3,
            "odt_category_id.level3.slug": "frutta-verdura"
          },
          {
            "odt_id": 19415200,
            "odt_ean": 2002135130007.0,
            "odt_name": "Arance Navelinas ",
            "odt_category_id": 251,
            "odt_category_id.slug": "agrumi",
            "odt_category_id.level2": 100112,
            "odt_category_id.level2.slug": "frutta-fresca",
            "odt_category_id.level3": 3,
            "odt_category_id.level3.slug": "frutta-verdura"
          },
          {
            "odt_id": 19415180,
            "odt_ean": 8004381107008.0,
            "odt_name": "Mele Alto Adige Igp Golden Delicious Italia Cal. i 80-85 Mm 0,900 Kg",
            "odt_category_id": 252,
            "odt_category_id.slug": "mele-pere",
            "odt_category_id.level2": 100112,
            "odt_category_id.level2.slug": "frutta-fresca",
            "odt_category_id.level3": 3,
            "odt_category_id.level3.slug": "frutta-verdura"
          },
          {
            "odt_id": 19415196,
            "odt_ean": 2002146130003.0,
            "odt_name": "Ananas ",
            "odt_category_id": 254,
            "odt_category_id.slug": "altra-frutta",
            "odt_category_id.level2": 100112,
            "odt_category_id.level2.slug": "frutta-fresca",
            "odt_category_id.level3": 3,
            "odt_category_id.level3.slug": "frutta-verdura"
          },
          {
            "odt_id": 19415192,
            "odt_ean": 8024666500072.0,
            "odt_name": "Carrefour Bio Limoni bio",
            "odt_category_id": 251,
            "odt_category_id.slug": "agrumi",
            "odt_category_id.level2": 100112,
            "odt_category_id.level2.slug": "frutta-fresca",
            "odt_category_id.level3": 3,
            "odt_category_id.level3.slug": "frutta-verdura"
          },
          {
            "odt_id": 19415178,
            "odt_ean": 8033661091003.0,
            "odt_name": "Amaltea Formaggio Bocconcino di Capra",
            "odt_category_id": 298,
            "odt_category_id.slug": "robiole-tomini-caprini",
            "odt_category_id.level2": 100290,
            "odt_category_id.level2.slug": "formaggi-confezionati",
            "odt_category_id.level3": 4,
            "odt_category_id.level3.slug": "formaggi-salumi"
          },
          {
            "odt_id": 19415176,
            "odt_ean": 8013165060057.0,
            "odt_name": "Zorbas Light Formaggio Greco Magro",
            "odt_category_id": 286,
            "odt_category_id.slug": "specialita-formaggi",
            "odt_category_id.level2": 100290,
            "odt_category_id.level2.slug": "formaggi-confezionati",
            "odt_category_id.level3": 4,
            "odt_category_id.level3.slug": "formaggi-salumi"
          },
          {
            "odt_id": 19415190,
            "odt_ean": 3245414229228.0,
            "odt_name": "Carrefour Formaggio Fresco di Capra",
            "odt_category_id": 298,
            "odt_category_id.slug": "robiole-tomini-caprini",
            "odt_category_id.level2": 100290,
            "odt_category_id.level2.slug": "formaggi-confezionati",
            "odt_category_id.level3": 4,
            "odt_category_id.level3.slug": "formaggi-salumi"
          },
          {
            "odt_id": 19415170,
            "odt_ean": 8007185002722.0,
            "odt_name": "Everton Karkadè, Infuso Bio",
            "odt_category_id": 422,
            "odt_category_id.slug": "infusi-e-tisane",
            "odt_category_id.level2": 100330,
            "odt_category_id.level2.slug": "tisane",
            "odt_category_id.level3": 10,
            "odt_category_id.level3.slug": "caffe-te-zucchero"
          },
          {
            "odt_id": 19415172,
            "odt_ean": 9001475062341.0,
            "odt_name": "Pompadour Zenzero Limone per Infuso",
            "odt_category_id": 422,
            "odt_category_id.slug": "infusi-e-tisane",
            "odt_category_id.level2": 100330,
            "odt_category_id.level2.slug": "tisane",
            "odt_category_id.level3": 10,
            "odt_category_id.level3.slug": "caffe-te-zucchero"
          },
          {
            "odt_id": 19415186,
            "odt_ean": 8012666041916.0,
            "odt_name": "Carrefour Bio Polpa di Pomodoro in Succo di Pomodoro",
            "odt_category_id": 451,
            "odt_category_id.slug": "polpa-di-pomodoro",
            "odt_category_id.level2": 100160,
            "odt_category_id.level2.slug": "pelati-passate",
            "odt_category_id.level3": 27,
            "odt_category_id.level3.slug": "sughi-scatolame-condimenti"
          },
          {
            "odt_id": 19415182,
            "odt_ean": 8001350020627.0,
            "odt_name": "Carrefour Bio Pomodori Pelati",
            "odt_category_id": 450,
            "odt_category_id.slug": "pomodori-pelati",
            "odt_category_id.level2": 100160,
            "odt_category_id.level2.slug": "pelati-passate",
            "odt_category_id.level3": 27,
            "odt_category_id.level3.slug": "sughi-scatolame-condimenti"
          },
          {
            "odt_id": 19415168,
            "odt_ean": 8002280003506.0,
            "odt_name": "Gemma di Mare Gli Integrali Sale Marino del Mediterraneo Grosso",
            "odt_category_id": 6009,
            "odt_category_id.slug": "sale-grosso",
            "odt_category_id.level2": 100165,
            "odt_category_id.level2.slug": "olio-aceto-sale",
            "odt_category_id.level3": 27,
            "odt_category_id.level3.slug": "sughi-scatolame-condimenti"
          },
          {
            "odt_id": 19415174,
            "odt_ean": 8020141810001.0,
            "odt_name": "Sant'Anna Naturale Sorgente Rebruant ",
            "odt_category_id": 691,
            "odt_category_id.slug": "acqua-naturale",
            "odt_category_id.level2": 100191,
            "odt_category_id.level2.slug": "acqua",
            "odt_category_id.level3": 16,
            "odt_category_id.level3.slug": "acqua-bibite-alcolici"
          },
          {
            "odt_id": 19415174,
            "odt_ean": 8020141810001.0,
            "odt_name": "Sant'Anna Naturale Sorgente Rebruant ",
            "odt_category_id": -2,
            "odt_category_id.slug": null,
            "odt_category_id.level2": 0,
            "odt_category_id.level2.slug": null,
            "odt_category_id.level3": 0,
            "odt_category_id.level3.slug": null
          }
        ],
        "unsorted_time_sec": 1652,
        "sorted_time_sec": 1549
      }
    ],
    "performance": {
      "cpu_count": 12,
      "loading_ms": 4067,
      "items": 18,
      "predictions": 342,
      "predictions_ms": 1276,
      "total_ms": 1465
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

**rx_s24_ordersorting**: recipe used to train ordersorting model      
https://s24.analitico.ai/api/recipes/rx_s24_ordersorting

**ml_NTqcTMTEzNVz**: trained model (may be out of date or not the latest)      
https://s24.analitico.ai/api/models/ml_NTqcTMTEzNVz

**ep_s24_ordersorting**: prediction endpoint with link to current trained model      
https://s24.analitico.ai/api/endpoints/ep_s24_ordersorting




