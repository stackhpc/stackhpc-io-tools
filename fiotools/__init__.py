# .config/matplotlib/matplotlibrc line backend : Agg
import matplotlib.pyplot as plt
from pathlib2 import Path
import pandas as pd
import numpy as np
import errno
import json
import math
import os
import time
import pdb

class ClatGrid:
    min_x = np.inf
    max_x = 0
    min_y = np.inf
    max_y = 0.
    grid_y = 0
    io_bs = {}
    io_density = {}
    iops_bs = {}
    timescale = 'us'
    logscale = False
    ts_dict = {
        'us': {'divider': 10**3, 'label':'\mu s'},
        'ms': {'divider': 10**6, 'label':'m s'},
    }
    percentiles = ['1%','5%','10%','20%','30%','40%','50%','60%','70%','80%','90%','95%','99%','99.5%','99.9%','99.95%','99.99%']
    
    def __init__(self, input_dirs, output_dir, granularity, force, mode, skip_bs=[], logscale=False, timescale='us', max_bs=65536, verbose=False, plot=True):
        self.grid_y = granularity
        self.logscale = logscale
        self.timescale = timescale
        self.max_bs = max_bs
        self.divider = self.ts_dict[timescale]['divider']
        self.label = self.ts_dict[timescale]['label']
        self.skip_bs = skip_bs
        self.input_dirs = input_dirs
        self.output_dir = output_dir
        self.mode = mode
        self.verbose = verbose
        ensure_output_dir(output_dir, force)
        self.populate(input_dirs, output_dir)
        self.aggregate_and_normalise()
        if plot:
            self.plot_cl()
            self.plot_il()
            self.plot_bw()
        
    # Each series is indexed by the IO size (and the test mode)
    # Multiple client series are stored independently at this stage
    # and will be gridded, aggregated and normalised later on.
    def add_series( self, bs, iops_total, clat_data ):

        # Paranoia: Check the iops_total matches the sum of all bins
        if sum(clat_data.values()) != iops_total:
            raise ValueError("I/O size %d: sum of histogram bins is %d, expected %d" % (bs, sum(clat_data.values()), iops_total))

        # Construct a dict of floating-point IO latencies
        bs_data = {}
        for y_str, z_str in clat_data.iteritems():
            y = float(y_str)
            y /= self.divider
            if self.logscale:
                y = math.log(y, 10)
            z = float(z_str)
            bs_data[y] = z
            self.min_y = min(self.min_y, y)
            self.max_y = max(self.max_y, y)

        # Update grid-boundary metrics
        x = int(math.log(bs, 2))
        self.min_x = min(self.min_x, x)
        self.max_x = max(self.max_x, x)

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
            if abs(io_density_check - 0.99) > 0.2 or abs(grid_check - 0.99) > 0.2:
                raise ValueError("CHECK FAILED: blocksize %d cumulative density %f cumulative grid %f" % (2**x, io_density_check, grid_check))

        return grid

    def plot_cl(self):
        fig, ax = plt.subplots(figsize=(10,8))
        legend = sorted(set(self.ildf.index))
        ax.set_prop_cycle('color', [plt.cm.jet(i) for i in np.linspace(0, 1, len(legend))])
        self.cldf.groupby(['log2_bs','clat'])['freq'].mean().reset_index().set_index('log2_bs').groupby('log2_bs').plot(x='clat',y='freq',ax=ax,loglog=True,linewidth=1)
        ax.legend(legend, title='block size ($2^n$)')
        ax.set_xlabel('commit latency - ($ns$)')
        ax.set_ylabel('mean frequency')
        plt.savefig(str(self.output_dir/'commit-latency-freq-dist.png'))
        return fig, ax

    def plot_bw(self):
        fig, ax = plt.subplots(figsize=(10,8))
        pd.concat([pd.Series(row, name=i) for i,row in self.bwdf['bw']
                   .groupby(self.bwdf.index).apply(list).iteritems()], axis=1).boxplot(ax = ax)
        ax.set_xlabel('block size - $2^n$')
        ax.set_ylabel('%s bandwidth ($KB/s$)' % self.mode)
        plt.savefig(str(self.output_dir/'blocksize-vs-bandwidth.png'))      
        return fig, ax
    
    def plot_il(self, percentiles=[50.0,95.0,99.0,99.99], xlim=None, ylim=None, cmap='gist_heat'):
        fig, ax = plt.subplots(figsize=(10,8))
        grid = self.fit_to_grid()
        # Find maximum value on Grid
        max_z = grid.max()
        nrow, ncol = grid.shape

        # Set empty bins to NaN to ensure they do not get plotted
        for row in range(nrow):
            for col in range(ncol):
                if grid[row, col] == 0.0:
                    grid[row, col] = np.nan

        if xlim == None:
            xlim = [self.min_x,self.max_x]
        if ylim == None:
            ylim = [self.min_y,self.max_y]
        extent = (self.min_x-0.5, self.max_x+0.5, self.min_y, self.max_y)
        plt.imshow(grid, extent=extent, cmap=cmap, origin='lower', vmin=0.0, vmax=max_z, aspect='auto', interpolation='none')
        self.ildf[percentiles].apply(lambda x: np.log10(x/self.divider)) \
            .groupby(self.ildf.index).mean() \
            .plot(figsize=(10,8), ax=ax, xlim=xlim, ylim=ylim, linewidth=2, style='-')
        ax.legend(title='percentiles')
        ax.set_xlabel('block size - $2^n$')
        if self.logscale:
            ax.set_ylabel('log(commit latency) - $%s$' % self.label)
        else:
            ax.set_ylabel('iops latency - $%s$' % self.label)
        plt.savefig(str(self.output_dir/'blocksize-vs-commit-latency.png'))        
        return fig, ax
    
    def populate(self, input_dirs, output_dir):
        # For each blocksize found, emit data from each listed job
        # FIXME: need to incorporate hostname and dataset name in the results
        # Emit bandwidth data points in column format

        bw = list()
        il = list()
        cl = list()

        for input_dir in input_dirs:
            print "Scanning for fio data in %s" % input_dir
            fio_file_list = get_fio_file_list(input_dir)
            fio_results = get_fio_results(fio_file_list)
            bs_list = sorted(fio_results.keys())
            for bs in bs_list:
                if bs not in self.skip_bs and bs <= self.max_bs:
                    for bs_job in fio_results[bs]['jobs']:

                        log2_bs = int(math.log(bs,2))

                        # Read and write bandwidth as a function of I/O size
                        bw.append({'log2_bs': log2_bs, 'bw': bs_job[self.mode]['bw']})

                        # IOPS and IO latency percentiles as a function of I/O size
                        row =  {'log2_bs': log2_bs, 'iops': bs_job[self.mode]['iops']}
                        row.update({float(k): v for k, v in bs_job[self.mode]['clat_ns']['percentile'].iteritems()})
                        il.append(row)

                        # Write I/O completion latencies as a datafile of x y z datapoints

                        # Need to transform string keys into integer to sort
                        for bin_ns in sorted([int(x) for x in bs_job[self.mode]['clat_ns']['bins'].keys()]):
                            bin_freq = bs_job[self.mode]['clat_ns']['bins'][str(bin_ns)]
                            cl.append({'log2_bs': log2_bs, 'clat': bin_ns, 'freq': bin_freq})

                        # Aggregate data from each dataset
                        self.add_series( bs, bs_job[self.mode]['total_ios'], bs_job[self.mode]['clat_ns']['bins'] ) 
                        
                        if self.verbose:
                            print "I/O size %8d, job %s: %d samples" % (bs, self.mode, bs_job[self.mode]['total_ios'])
                if self.verbose:
                    print "Aggregated data for %d I/Os, max latency %f %s" % (sum(self.iops_bs.values()), self.max_y if not self.logscale else 10**self.max_y, self.timescale)

        self.cldf = pd.DataFrame(cl).set_index('log2_bs')
        self.ildf = pd.DataFrame(il).set_index('log2_bs')
        self.bwdf = pd.DataFrame(bw).set_index('log2_bs')
        self.bwdf.to_csv(output_dir/(self.mode+'-bandwidth.csv'))
        self.ildf.to_csv(output_dir/(self.mode+'-iops-latency.csv'))
        self.cldf.to_csv(output_dir/(self.mode+'-commit-latency.csv'))
        
def get_fio_file_list(input_dir):
    # List JSON files in the fio input directory
    try:
        return list(input_dir.iterdir())
    except OSError as E:
        print "Could not access input directory %s" % (input_dir)
        raise E

def ensure_output_dir(output_dir, force):
    # Check the status of the output directory
    output_dir.mkdir(parents=True, exist_ok=force)
    for p in output_dir.iterdir():
        if force:
            print "Deleting existing output data %s in output directory" % (p)
            p.unlink()
        else:
            print "Output directory %s is not empty: use --force to overwrite it" % (output_dir)
            os.abort()

def get_fio_results(fio_file_list):
    # Read in and parse the data files
    fio_results = {}
    for fio_file in fio_file_list:
        with fio_file.open('r') as fio_fd:
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
