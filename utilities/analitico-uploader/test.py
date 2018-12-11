import os
import unittest
import uploader

SMALL_SIZE = 1024 * 1024
BIG_SIZE = 1024 * 1024 * 512

# authorization token with analitico API
API_TOKEN = 'tok_0ee8CuwLRE6n_s24'


class UploaderTest(unittest.TestCase):
 
    def setUp(self):
        with open('data.rnd', 'wb') as f1:
            f1.write(os.urandom(SMALL_SIZE))
        with open('big-data.rnd', 'wb') as f2:
            f2.write(os.urandom(BIG_SIZE))
 
    def test_small_upload(self):
        result = uploader.upload_file_to_analitico('s24-order-sorting', 'data.rnd', API_TOKEN)
        self.assertEqual(result['name'], "uploads/s24-order-sorting/data.rnd")
        self.assertGreaterEqual(int(result['size']), SMALL_SIZE)
 
    def test_big_upload(self):
        result = uploader.upload_file_to_analitico('s24-order-sorting', 'big-data.rnd', API_TOKEN)
        self.assertEqual(result['name'], "uploads/s24-order-sorting/big-data.rnd")
        self.assertGreaterEqual(int(result['size']), BIG_SIZE)
 
    def test_bogus_token(self):
        try:
            uploader.upload_file_to_analitico('s24-order-sorting', 'big-data.rnd', 'tok_bogus')
            self.fail()
        except:
            pass


if __name__ == '__main__':
    unittest.main()