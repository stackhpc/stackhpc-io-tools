#! /bin/env python
# Begun by Stig Telfer, StackHPC Ltd, 15th October 2018

# .config/matplotlib/matplotlibrc line backend : Agg
import matplotlib
matplotlib.use_backend('Agg')
import argparse
import errno
import json
import math
import matplotlib.pyplot as plt
import numpy as np
import os
import time

import pdb

class ClatGrid:
    min_x = 0
    max_x = 0
    min_y = 0.0
    max_y = 0.0
    grid_y = 0
    io_bs = {}
    io_density = {}
    iops_bs = {}
    timescale = 'us'
    logscale = False
    
    def __init__( self, grid_y, input_dirs, output_dir, force, logscale=False, timescale='us', max_bs=65536):
        self.grid_y = grid_y
        self.logscale = logscale
        self.timescale = timescale
        self.max_bs = max_bs
        ensure_output_dir(output_dir, force)
        for input_dir in input_dirs:
            print "Scanning for fio data in %s" % input_dir
            self.populate(input_dir, output_dir)
        self.plot_data(output_dir)

    # Each series is indexed by the IO size (and the test mode)
    # Multiple client series are stored independently at this stage
    # and will be gridded, aggregated and normalised later on.
    def add_series( self, bs, iops_total, clat_data ):

        # Paranoia: Check the iops_total matches the sum of all bins
        if sum(clat_data.values()) != iops_total:
            print "I/O size %d: sum of histogram bins is %d, expected %d" % (bs, sum(clat_data.values()), iops_total)
            raise ValueError

        # Construct a dict of floating-point IO latencies
        bs_data = {}
        for y_str, z_str in clat_data.iteritems():
            y = float(y_str)
            if self.timescale == 'us':
                y /= 1000.0
            elif self.timescale == 'ms':
                y /= 1000000.0
            if self.logscale:
                y = math.log(y, 10)
            z = float(z_str)
            bs_data[y] = z
            if self.min_y == 0 or self.min_y > y:
                self.min_y = y
            if self.max_y < y:
                self.max_y = y

        # Update grid-boundary metrics
        x = int(math.log(bs, 2))
        if self.min_x == 0 or self.min_x > x:
            self.min_x = x
        if self.max_x < x:
            self.max_x = x

        # Add the data to any existing data sets for this blocksize
        if x not in self.io_bs:
            self.io_bs[x] = []
            self.iops_bs[x] = 0
        self.io_bs[x] += [bs_data]
        self.iops_bs[x] += iops_total


    def aggregate_and_normalise( self ):
        ''' We may have sampled multiple results per blocksize.
            Generate a weighted normalisation across all readings.
            This must be done once all results have been added. '''

        # For each blocksize
        for bs, bs_results in self.io_bs.iteritems():
            z_total = float(self.iops_bs[bs])
            io_density = []

            # For each fio result in this blocksize
            for bs_data in bs_results:
                result_norm = {}
                prev_y = 0.0

                # For each datapoint in the result
                for y in sorted(bs_data.keys()):

                    # Process the IOs in order to construct IO frequency densities
                    z_norm = bs_data[y] / z_total
                    delta_y = y - prev_y
                    io_density_y = z_norm / delta_y
                    io_density += [dict(lower=prev_y, upper=y, density=io_density_y)]
                    prev_y = y

            # The generated list of I/O frequency density ranges
            # is suitable for resampling on a regularised grid
            self.io_density[bs] = io_density


    def fit_to_grid( self ):
        ''' Once all fio latency histograms have been submitted, 
            reinterpolate the data to a regular grid spacing
            to enable aggregation and plotting. '''

        bin_y = self.max_y / self.grid_y

        # Make coordinate arrays.
        #yi = np.logspace(0.0, np.log(self.max_y), bin_y)
        yi = np.arange(0.0, self.max_y, bin_y)
        nrow, ncol = (self.grid_y, self.max_x - self.min_x + 1)
        grid = np.zeros((nrow, ncol), dtype=np.dtype('double'))
        
        # Perform the gridding interpolation
        for x in sorted(self.io_bs.keys()):
            col = x - self.min_x
            io_density = self.io_density[x]
            io_density_check = 0.0          # Paranoia
            grid_check = 0.0                # Paranoia
            for D in io_density:
                for row in range(int(math.floor(D['lower'] / bin_y)), nrow):

                    grid_y_lower = yi[row]
                    grid_y_upper = grid_y_lower + bin_y

                    # Non-overlap: below or above?
                    if grid_y_upper < D['lower']:
                        continue
                    if grid_y_lower > D['upper']:
                        break

                    # Determine the extent of overlap
                    overlap_lower = max(grid_y_lower, D['lower'])
                    overlap_upper = min(grid_y_upper, D['upper'])
                    overlap_range = overlap_upper - overlap_lower

                    grid[row, col] += D['density'] * overlap_range / bin_y

                    # Paranoia
                    grid_check += D['density'] * overlap_range

                # Paranoia
                io_density_check += D['density']*(D['upper']-D['lower'])

            # Paranoia
            if io_density_check < 0.999 or io_density_check > 1.001 or grid_check < 0.999 or grid_check > 1.001:
                print "CHECK FAILED: blocksize %d cumulative density %f cumulative grid %f" % (2**x, io_density_check, grid_check)
                raise ValueError

        return grid


    # OK we have enough data, construct the grid and populate with interpolations
    def plot_data(self, output_dir, filename='blob.png'):

        self.aggregate_and_normalise()
        grid = self.fit_to_grid()

        # Find maximum value on Grid
        max_z = grid.max()
        nrow, ncol = grid.shape

        # Set empty bins to NaN to ensure they do not get plotted
        for row in range(nrow):
            for col in range(ncol):
                if grid[row, col] == 0.0:
                    grid[row, col] = np.nan

        # Select a colour palette
        palette = plt.matplotlib.colors.LinearSegmentedColormap('jet3', plt.cm.datad['jet'], 2048)
        palette.set_under(alpha=0.0) 

        extent = (self.min_x-0.5, self.max_x+0.5, self.min_y, self.max_y)
        plt.imshow(grid, extent=extent, cmap=palette, origin='lower', vmin=0.0, vmax=max_z, aspect='auto', interpolation='none')
        if self.logscale:
            #plt.ylim(10**5,10**7)
            plt.ylabel('Logarithmic commit latency - $%s$' % self.timescale)
        else:
            plt.ylim(10**5,10**7)
            plt.ylabel('commit latency - $%s$' % self.timescale)
        plt.xlabel(r'block size - $2^n$')
        plt.colorbar(label='relative frequency per blocksize')
        filename = "%s/%s" % (output_dir, filename)
        plt.savefig(filename, dpi=150, orientation='landscape', transparent=False)
        print 'Plotting to %s' % filename

    def populate(self, input_dir, output_dir):
        # For each blocksize found, emit data from each listed job
        # FIXME: need to incorporate hostname and dataset name in the results
        # Emit bandwidth data points in column format
        fio_file_list = get_fio_file_list(input_dir)
        fio_results = get_fio_results(fio_file_list)
        bs_list = sorted(fio_results.keys())
        for bs in bs_list:
            for bs_job in fio_results[bs]['jobs']:

                # Read and write bandwidth as a function of I/O size
                with open(output_dir + '/' + bs_job['jobname'] + '-bandwidth.dat', 'a+') as job_fd:
                    job_fd.write('{0:8} {1:8} {2:8}\n'
                        .format(bs, bs_job['read']['bw'], bs_job['write']['bw']))

                # IOPS and IO latency percentiles as a function of I/O size
                with open(output_dir + '/' + bs_job['jobname'] + '-read-iops-latency.dat', 'a+') as job_fd:
                    job_fd.write('{:8},{:8},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}\n'
                        .format(bs, bs_job['read']['iops'],
                            bs_job['read']['clat_ns']['percentile']["1.000000"],
                            bs_job['read']['clat_ns']['percentile']["5.000000"],
                            bs_job['read']['clat_ns']['percentile']["10.000000"],
                            bs_job['read']['clat_ns']['percentile']["20.000000"],
                            bs_job['read']['clat_ns']['percentile']["30.000000"],
                            bs_job['read']['clat_ns']['percentile']["40.000000"],
                            bs_job['read']['clat_ns']['percentile']["50.000000"],
                            bs_job['read']['clat_ns']['percentile']["60.000000"],
                            bs_job['read']['clat_ns']['percentile']["70.000000"],
                            bs_job['read']['clat_ns']['percentile']["80.000000"],
                            bs_job['read']['clat_ns']['percentile']["90.000000"],
                            bs_job['read']['clat_ns']['percentile']["95.000000"],
                            bs_job['read']['clat_ns']['percentile']["99.000000"],
                            bs_job['read']['clat_ns']['percentile']["99.500000"],
                            bs_job['read']['clat_ns']['percentile']["99.900000"],
                            bs_job['read']['clat_ns']['percentile']["99.950000"],
                            bs_job['read']['clat_ns']['percentile']["99.990000"]))

                # Write I/O completion latencies as a datafile of x y z datapoints
                with open(output_dir + '/' + bs_job['jobname'] + '-read-clat.dat', 'a+') as job_fd:
                    # Need to transform string keys into integer to sort
                    for bin_ns in sorted([int(x) for x in bs_job['read']['clat_ns']['bins'].keys()]):
                        bin_freq = bs_job['read']['clat_ns']['bins'][str(bin_ns)]
                        job_fd.write('{:8} {:10} {:8}\n'.format(math.log(bs,2), bin_ns, bin_freq))
                    job_fd.write('\n')

                # Aggregate data from each dataset
                if bs <= self.max_bs:
                    self.add_series( int(bs), bs_job['read']['total_ios'], bs_job['read']['clat_ns']['bins'] ) 

                print "I/O size %8d, job %s: %d samples" % (bs, bs_job['jobname'], bs_job['read']['total_ios'])
            
        print "Aggregated data for %d I/Os, max latency %f %s" % (sum(self.iops_bs.values()), self.max_y if not self.logscale else 10**self.max_y, self.timescale)

def get_fio_file_list(input_dir):
    # List JSON files in the fio input directory
    try:
        return [input_dir + '/' + f for f in os.listdir(input_dir)]
    except OSError as E:
        print "Could not access input directory %s: %s" % (input_dir, os.strerror(E.errno))
        os.abort()

def ensure_output_dir(output_dir, force):
    # Check the status of the output directory
    output_dir_present = True
    try:
        output_file_list = os.listdir(output_dir)
        if force:
            print "Overwriting output data in %s" % (output_dir)
        else:
            print "Output directory %s already exists: use --force to overwrite it" % (output_dir)
            os.abort()
    except OSError as E:
        if E.errno == errno.ENOENT:
            output_dir_present = False
            pass
        else:
            print "Output directory %s not accessible: %s" % (output_dir, os.strerror(E.errno))
            os.abort()
    # Generate the output directory if not already present
    try:
        if not output_dir_present:
            os.mkdir(output_dir, 0755)
    except OSError as E:
        print "Output directory %s could not be created: %s" % (args.output_dir, os.strerror(E.errno))
        os.abort()

def get_fio_results(fio_file_list):
    # Read in and parse the data files
    fio_results = {}
    for fio_file in fio_file_list:
        with open(fio_file, 'r') as fio_fd:
            try:
                fio_run_data = json.load(fio_fd)
                test_bs = int(fio_run_data['global options']['bs'])
                fio_results[test_bs] = fio_run_data
            except ValueError as E:
                print "Skipping %s: could not be parsed as JSON" % (fio_file)
                pass
            except KeyError as E:
                print "Skipping %s: data structure could not be parsed" % (fio_file)
                pass
    return fio_results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse fio output')
    parser.add_argument('-L', '--logscale',
        dest="logscale", action='store_const', const=True, required=False,
        help='Logarithmic axes for latency plots')
    parser.add_argument('-f', '--force',
        dest="force", action='store_const', const=True, required=False,
        help='Overwrite previous output data, if existing')
    parser.add_argument('-o','--output-dir', metavar='<path>',
        dest="output_dir", type=str, required=True,
        help='Directory for result data for plotting')
    parser.add_argument('-u', '--units', metavar='<ns|us|ms>',
        dest="units", type=str, required=False, choices=['ns', 'us', 'ms'], default="us",
        help='Latency time units')
    parser.add_argument('-M', '--max-lat-bs', metavar='<io-size>',
        dest="max_lat_bs", type=int, default=65536,
        help='Maximum I/O size to include in latency plots')
    parser.add_argument('-i', 'input_dirs', nargs='+',
        help='Directory of output files from fio in json+ format')

    args = parser.parse_args()

    # Logarithmic plots fare better with more granular bins
    if args.logscale:
        granularity=100
    else:
        grit_units=2000

    grid = ClatGrid(granularity, args.input_dirs, args.output_dir, args.force, args.logscale, args.units, args.max_lat_bs)
