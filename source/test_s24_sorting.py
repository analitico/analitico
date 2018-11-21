import unittest
import json

from s24.sorting import s24_sort_order

FAMILA_ORDER_PATH = 'assets/s24/test/simple-order-famila.json'
MIGROSS_ORDER_PATH = 'assets/s24/test/simple-order-migross.json'
ESSELUNGA_ORDER_PATH = 'assets/s24/test/simple-order-esselunga.json'

class Test_S24_OrderSorting(unittest.TestCase):

    def test_sort_order(self):

        with open(FAMILA_ORDER_PATH) as order_file:
            order = json.load(order_file)
        order_details = order['details']

        self.assertIsNotNone(order)
        self.assertIsNotNone(order['store_ref_id'])
        self.assertIsNotNone(order['store_name'])
        self.assertIsNotNone(order_details)

        sorted, meta = s24_sort_order(order)
        sorted_details = sorted['details']

        self.assertEqual(len(order_details), len(sorted_details))
        self.assertEqual(meta['items'], len(sorted_details))
        
        self.assertGreaterEqual(meta['predictions_ms'], 10)        
        self.assertGreaterEqual(meta['routing_ms'], 10)        
        self.assertGreaterEqual(meta['total_ms'], 10)        

    def get_item_index(self, order_path, item_name):
        with open(order_path) as f:
            order = json.load(f)

        sorted, _ = s24_sort_order(order)
        details = sorted['details']
        item_index = next((index for (index, d) in enumerate(details) if d["item_name"] == item_name), None)
        return item_index

    def test_sort_zucchine(self):
        # famila superstore saval
        famila_index = self.get_item_index(FAMILA_ORDER_PATH, 'Zucchine')
        self.assertGreaterEqual(famila_index, 22) # verdure in ? 

        migross_index = self.get_item_index(MIGROSS_ORDER_PATH, 'Zucchine')
        self.assertLessEqual(migross_index, 5) # verdure in testa

        esselunga_index = self.get_item_index(ESSELUNGA_ORDER_PATH, 'Zucchine')
        self.assertLessEqual(esselunga_index, 5) # verdure in testa


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(Test_S24_OrderSorting)
    unittest.TextTestRunner(verbosity=2).run(suite)

    