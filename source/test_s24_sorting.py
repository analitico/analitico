import unittest
import json

from s24.sorting import s24_sort_order

SIMPLE_ORDER_PATH = 's24/assets/s24-simple-order.json'

class Test_S24_OrderSorting(unittest.TestCase):

    def test_sort_order(self):

        with open(SIMPLE_ORDER_PATH) as order_file:
            order = json.load(order_file)
        order_details = order['details']

        self.assertIsNotNone(order)
        self.assertIsNotNone(order['store_ref_id'])
        self.assertIsNotNone(order['store_name'])
        self.assertIsNotNone(order_details)

        sorted, meta = s24_sort_order(order)
        sorted_details = sorted['details']

        self.assertEquals(len(order_details), len(sorted_details))
        self.assertEquals(meta['items'], len(sorted_details))
        self.assertGreaterEqual(meta['routing_ms'], 0)        
        self.assertGreaterEqual(meta['sorting_ms'], 0)        


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(Test_S24_OrderSorting)
    unittest.TextTestRunner(verbosity=2).run(suite)

    