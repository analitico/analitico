import unittest
import json

from s24.ordersorting import s24_sort_order

FAMILA_ORDER_PATH = 'data/s24/test/simple-order-famila.json'
MIGROSS_ORDER_PATH = 'data/s24/test/simple-order-migross.json'
MARTINELLI_ORDER_PATH = 'data/s24/test/simple-order-martinelli.json'
ESSELUNGA_VR_ORDER_PATH = 'data/s24/test/simple-order-esselunga-vr.json'
ESSELUNGA_MI_ORDER_PATH = 'data/s24/test/simple-order-esselunga-mi.json'

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
        """ Sorts an order, returns the index of the given item_name """
        with open(order_path) as f:
            order = json.load(f)
        sorted, _ = s24_sort_order(order)
        details = sorted['details']
        item_index = next((index for (index, d) in enumerate(details) if d["item_name"] == item_name), None)
        return item_index

    def test_sort_zucchine_famila(self):
        print(FAMILA_ORDER_PATH)
        famila_index = self.get_item_index(FAMILA_ORDER_PATH, 'Zucchine')
        self.assertGreaterEqual(famila_index, 22) # zucchine in ? 

    def test_sort_zucchine_migross(self):
        print(MIGROSS_ORDER_PATH)
        migross_index = self.get_item_index(MIGROSS_ORDER_PATH, 'Zucchine')
        self.assertLessEqual(migross_index, 5) # verdure in testa

    def test_sort_zucchine_martinelli(self):
        # zucchine al 5. la verdura è abbastanza in testa, dopo latticini
        print(MARTINELLI_ORDER_PATH)
        martinelli_index = self.get_item_index(MARTINELLI_ORDER_PATH, 'Zucchine')
        self.assertLessEqual(martinelli_index, 5) # verdure in testa

    def test_sort_zucchine_esselunga_mi(self):
        print(ESSELUNGA_MI_ORDER_PATH)
        esselunga_mi_index = self.get_item_index(ESSELUNGA_MI_ORDER_PATH, 'Zucchine')
        self.assertLessEqual(esselunga_mi_index, 5) # verdure in testa

    def test_sort_zucchine_esselunga_vr(self):
        print(ESSELUNGA_VR_ORDER_PATH) # esselunga verona fiera
        esselunga_vr_index = self.get_item_index(ESSELUNGA_VR_ORDER_PATH, 'Zucchine')
        self.assertLessEqual(esselunga_vr_index, 20) # verdure in testa?
        # 15, cannato?



if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(Test_S24_OrderSorting)
    unittest.TextTestRunner(verbosity=2).run(suite)
