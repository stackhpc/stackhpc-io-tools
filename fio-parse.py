#
# Begun by Stig Telfer, StackHPC Ltd, 15th October 2018

import argparse
import errno
import json
import math
import matplotlib.pyplot as plt
import numpy as np
import os
import time

import pdb

class clat_grid:
    min_x = 0
    max_x = 0
    max_y = 0.0
    grid_y = 0
    io_bs = {}
    io_density = {}
    
    def __init__( self, grid_y ):
        self.grid_y = grid_y
        
    def add_series( self, bs, iops_total, clat_data ):
        # Construct a unit-scaled dict of floating-point IO latencies
        bs_data = {}
        iops_sf = float(iops_total)
        for y_str, z_str in clat_data.iteritems():
            y = float(y_str)
            z = float(z_str)
            bs_data[y] = z/iops_sf
            if self.max_y < y:
                self.max_y = y

        # Process the IOs in order to construct IO frequency densities
        prev_y = 0.0
        prev_z = 0.0
        io_density = []
        for y in sorted(bs_data.keys()):
            if prev_y != 0.0:
                z = bs_data[y]
                delta_y = y - prev_y
                io_density_y = z / delta_y
                io_density += [dict(lower=prev_y, upper=y, density=io_density_y)]
            prev_y = y
            prev_z = z

        # Update grid-forming metrics
        x = int(math.log(bs, 2))
        if self.min_x == 0 or self.min_x > x:
            self.min_x = x
        if self.max_x < x:
            self.max_x = x
        self.io_bs[x] = bs_data
        self.io_density[x] = io_density

    # OK we have enough data, construct the grid and populate with interpolations
    def plot_data( self ):
        bin_y = self.max_y / self.grid_y

        # Make coordinate arrays.
        yi = np.arange(0.0, self.max_y, bin_y)
        nrow, ncol = (self.grid_y, self.max_x - self.min_x + 1)
        grid = np.zeros((nrow, ncol), dtype=np.dtype('double'))
        
        # Perform the gridding interpolation
        for x in sorted(self.io_density.keys()):
            col = x - self.min_x
            io_density = self.io_density[x]
            col_check = 0.0
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

        # Find maximum value on Grid
        max_z = grid.max()

        # Set empty bins to NaN to ensure they do not get plotted
        for row in range(nrow):
            for col in range(ncol):
                if grid[row, col] == 0.0:
                    grid[row, col] = np.nan

        # Select a colour palette
        palette = plt.matplotlib.colors.LinearSegmentedColormap('jet3', plt.cm.datad['jet'], 2048)
        palette.set_under(alpha=0.0) 

        extent = (self.min_x, self.max_x, 1.0, self.max_y)
        plt.imshow(grid, extent=extent, cmap=palette, origin='lower', vmin=0.0, vmax=max_z, aspect='auto', interpolation='none')
        plt.savefig('blob.png', dpi=150, orientation='landscape', format='png', transparent=True)


parser = argparse.ArgumentParser(description='Parse fio output')
parser.add_argument('--input-dir', metavar='<path>',
    dest='input_dir', type=str, required=True,
    help='Directory of output files from fio in json+ format')
parser.add_argument('--output-dir', metavar='<path>',
    dest="output_dir", type=str, required=True,
    help='Directory for result data for plotting')
parser.add_argument('--force',
    dest="force", action='store_const', const=True, required=False,
    help='Overwrite previous output data, if existing')

args = parser.parse_args()

# List JSON files in the fio input directory
try:
    fio_file_list = os.listdir(args.input_dir)
except OSError as E:
    print "Could not access input directory %s: %s" % (args.input_dir, os.strerror(E.errno))
    os.abort()

# Check the status of the output directory
output_dir_present = True
try:
    output_file_list = os.listdir(args.output_dir)
    if args.force:
        print "Overwriting output data in %s" % (args.output_dir)
    else:
        print "Output directory %s already exists: use --force to overwrite it" % (args.output_dir)
        os.abort()
except OSError as E:
    if E.errno == errno.ENOENT:
        output_dir_present = False
        pass
    else:
        print "Output directory %s not accessible: %s" % (args.output_dir, os.strerror(E.errno))
        os.abort()

# Generate the output directory if not already present
try:
    if not output_dir_present:
        os.mkdir(args.output_dir, 0755)
except OSError as E:
    print "Output directory %s could not be created: %s" % (args.output_dir, os.strerror(E.errno))
    os.abort()

# Read in and parse the data files
fio_results = {}
for fio_file in fio_file_list:
    with open(args.input_dir + '/' + fio_file, 'r') as fio_fd:
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

# For each blocksize found, emit data from each listed job

# FIXME: if we forced the creation of the result dir, zap the contents here.

# FIXME: need to incorporate hostname

# Emit bandwidth data points in column format
bs_list = sorted(fio_results.keys())
grid = clat_grid(2000)
for bs in bs_list:
    for bs_job in fio_results[bs]['jobs']:
        print "I/O size %d job %s" % (bs, bs_job['jobname'])

        # Read and write bandwidth as a function of I/O size
        with open(args.output_dir + '/' + bs_job['jobname'] + '-bandwidth.dat', 'a+') as job_fd:
            job_fd.write('{0:8} {1:8} {2:8}\n'
                .format(bs, bs_job['read']['bw'], bs_job['write']['bw']))

        # IOPS and IO latency percentiles as a function of I/O size
        with open(args.output_dir + '/' + bs_job['jobname'] + '-read-iops-latency.dat', 'a+') as job_fd:
            job_fd.write('{:8} {:8} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {}\n'
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

        # IOPS and IO latency percentiles as a function of I/O size
        with open(args.output_dir + '/' + bs_job['jobname'] + '-read-iops-latency.dat', 'a+') as job_fd:
            job_fd.write('{:8} {:8} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {}\n'
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
        with open(args.output_dir + '/' + bs_job['jobname'] + '-read-clat.dat', 'a+') as job_fd:
            # Need to transform string keys into integer to sort
            for bin_ns in sorted([int(x) for x in bs_job['read']['clat_ns']['bins'].keys()]):
                bin_freq = bs_job['read']['clat_ns']['bins'][str(bin_ns)]
                job_fd.write('{:8} {:10} {:8}\n'.format(math.log(bs,2), bin_ns, bin_freq))
            job_fd.write('\n')

        # Aggregate data from each dataset
        if bs <= 65536:
            grid.add_series( int(bs), bs_job['read']['total_ios'], bs_job['read']['clat_ns']['bins'] ) 
        
grid.plot_data()

print "Parsed data for I/O sizes %s" % (bs_list)

