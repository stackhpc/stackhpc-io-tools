import unittest
import iotools

class Test(unittest.TestCase):
    def setUp(self):
        self.kwargs = {
            input_dirs = [ 'input1', 'input2' ],
            output_dir = 'output',
            granularity = 200,
            force = True,
        }

    def test_clatgrid(self):
        grid = iotools.ClatGrid(**self.kwargs)

if __name__ == '__main__':
    unittest.main()
