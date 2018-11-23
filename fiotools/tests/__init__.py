import unittest
import fiotools
from pathlib2 import Path

class Test(unittest.TestCase):
    def setUp(self):
        self.input_dirs_read = list(Path('fiotools/tests/ceph-randread/2').iterdir())
        self.input_dirs_write = list(Path('fiotools/tests/beegfs-write/2').iterdir())
        self.kwargs = dict(
            output_dir = 'fiotools/tests/output',
            logscale=True,
            scenario = 'test',
            granularity=200,
            force=True,
            verbose=False,
        )

    def test_clatgrid_read(self):
        ''' Read mode should successfully process data from read mode. '''

        grid = fiotools.ClatGrid(
                    input_dirs=self.input_dirs_read,
                    mode='randread', **self.kwargs)

    def test_clatgrid_read_single(self):
        ''' Read mode should successfully process data from read mode, even
            when its a single input directory. '''

        grid = fiotools.ClatGrid(
                    input_dirs=self.input_dirs_read[:-1],
                    mode='randread', **self.kwargs)

    def test_clatgrid_write_when_read(self):
        ''' This should yield value error because the data is from yield mode
            and the values being attempted to access is from write mode. '''

        with self.assertRaises(ValueError):
            grid = fiotools.ClatGrid(
                        input_dirs=self.input_dirs_read,
                        mode='randwrite', **self.kwargs)

    def test_clatgrid_read_verbose(self):
        ''' Verbose mode should present more details about the processing. '''

        self.kwargs['verbose'] = True
        grid = fiotools.ClatGrid(
                    input_dirs=self.input_dirs_read,
                    mode='randread', **self.kwargs)

    def test_clatgrid_read_no_logscale(self):
        ''' Results should be processed properly when logscale is off. '''

        self.kwargs['logscale'] = False
        grid = fiotools.ClatGrid(
                    input_dirs=self.input_dirs_read,
                    mode='randread', **self.kwargs)

    def test_clatgrid_read_no_force(self):
        ''' This should raise OSError because there are files that could be
            overwritten in the results folder. '''

        self.kwargs['force'] = False
        with self.assertRaises(OSError):
            grid = fiotools.ClatGrid(
                        input_dirs=self.input_dirs_read,
                        mode='randread', **self.kwargs)

    def test_clatgrid_write_no_skip_bs(self):
        ''' This fails because block size of 128 and 256 contain invalid
            results typical of when fio run fails for small block sizes. '''

        with self.assertRaises(ValueError):
            grid = fiotools.ClatGrid(
                        input_dirs=self.input_dirs_write,
                        mode='write', **self.kwargs)

    def test_clatgrid_write_skip_bs(self):
        ''' This should pass because block size of 128 and 256 are being
            skipped. '''

        grid = fiotools.ClatGrid(
                    input_dirs=self.input_dirs_write,
                    skip_bs=[128, 256],
                    mode='write', **self.kwargs)

if __name__ == '__main__':
    unittest.main()
