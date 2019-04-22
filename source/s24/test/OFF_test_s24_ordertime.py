import unittest
import json

from analitico.utilities import read_json
from s24.ordertime import OrderTimeModel

ORDER_S1_PATH = "data/s24/test/order-time-s1.json"
ORDER_S2_PATH = "data/s24/test/order-time-s2.json"


class Test_s24_OrderTime(unittest.TestCase):
    def test_train_model(self):
        """ Train order time model, check results """

        model = OrderTimeModel()
        scores = model.train()
        print(json.dumps(scores, indent=4))

        data = scores["data"]

        self.assertGreater(data["records"]["source"], 10000)
        self.assertGreater(data["records"]["filtered"], 10000)
        self.assertGreater(data["records"]["training"], 10000)
        self.assertGreater(data["records"]["test"], 100)

        self.assertLess(data["scores"]["median_abs_error"], 25)
        self.assertLess(data["scores"]["mean_abs_error"], 25)
        self.assertLess(data["scores"]["sqrt_mean_squared_error"], 25)

        self.assertGreater(data["features_importance"]["items_total"], 15)
        self.assertGreater(data["features_importance"]["order_fulfillment_type"], 10)
        self.assertGreater(data["features_importance"]["store_customer_duration"], 10)
        self.assertGreater(data["features_importance"]["store_name"], 5)

        meta = scores["meta"]

        self.assertGreater(meta["processing_ms"], 1000)
        self.assertGreater(meta["total_ms"], 1000)
        self.assertGreater(meta["total_iterations"], 20)
        self.assertGreater(meta["best_iteration"], 10)

    def test_request_prediction(self):
        """ Test running a prediction on predefined data """

        order_s1 = read_json(ORDER_S1_PATH)
        model = OrderTimeModel()
        results = model.predict(order_s1["data"])

        self.assertLess(results["data"]["predictions"][0], 50)
        self.assertEqual(results["meta"]["project_id"], "s24-order-time")
        # self.assertLess(results['meta']['total_ms'], 100)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(Test_s24_OrderTime)
    unittest.TextTestRunner(verbosity=2).run(suite)
