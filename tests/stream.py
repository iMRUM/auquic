import unittest


from .. import stream

# expected : actual
class MyTestCase(unittest.TestCase):
    def test_set_state(self):
        self.stream = stream.Stream(0)
        self.assertEqual(True, self.stream.set_state_rec(5))  # add assertion here
        with self.assertRaises(ValueError):  # Expecting an exception if the value is invalid
            self.stream.set_state_rec("bjbnj")

if __name__ == '__main__':
    unittest.main()
