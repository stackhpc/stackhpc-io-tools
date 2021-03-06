# .config/matplotlib/matplotlibrc line backend : Agg
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from pathlib2 import Path
import pandas as pd
import numpy as np
import json
import math
import os


class ClatGrid:

    timescale = 'us'
    logscale = False
    tolerance = 0.1
    ts_dict = {
        'ns': {'divider': 1, 'label': 'n s'},
        'us': {'divider': 10**3, 'label': '\mu s'},
        'ms': {'divider': 10**6, 'label': 'm s'},
    }
    bs_dict = {
        'KB': {'divider': 1, 'label': 'KB/s'},
        'MB': {'divider': 1000, 'label': 'MB/s'},
    }

    def __init__(self, input_dirs, output_dir, granularity, scenario, mode,
                    force=False, skip_bs=[], logscale=False, timescale='us',
                    bytescale='MB', max_bs=65536, verbose=False, plot=True):
        ''' Initialisation function. '''

        # Read input arguments
        self.grid_y = granularity
        self.logscale = logscale
        self.timescale = timescale
        self.max_bs = max_bs
        self.skip_bs = skip_bs
        self.input_dirs = [Path(input_dir) for input_dir in input_dirs]
        self.output_dir = Path(output_dir)
        self.scenario = scenario
        self.rw = mode
        self.verbose = verbose

        # Infer these from input arguments
        self.num_clients = len(self.input_dirs)
        self.mode = "write" if "write" in mode else "read"
        self.ts_divider = self.ts_dict[timescale]['divider']
        self.ts_label = self.ts_dict[timescale]['label']
        self.bs_divider = self.bs_dict[bytescale]['divider']
        self.bs_label = self.bs_dict[bytescale]['label']

        # Initialise these
        self.min_x = np.inf
        self.max_x = 0
        self.min_y = np.inf
        self.max_y = 0.
        self.io_bs = {}
        self.io_density = {}
        self.iops_bs = {}

        # Function calls
        self.ensure_output_dir(force)
        self.populate()
        self.aggregate_and_normalise()
        if plot:
            self.plot_cl()
            self.plot_cf()
            self.plot_bw()

    def add_series(self, x, iops_total, clat_data):
        ''' Each series is indexed by the IO size (and the test mode)
            Multiple client series are stored independently at this stage
            and will be gridded, aggregated and normalised later on. '''

        # Paranoia: Check the iops_total matches the sum of all bins
        if sum(clat_data.values()) != iops_total:
            raise ValueError(
                "I/O size %d: sum of histogram bins is %d, expected %d" %
                (2**x, sum(clat_data.values()), iops_total))
        # Construct a dict of floating-point IO latencies
        bs_data = {}
        for y_str, z_str in clat_data.iteritems():
            y = float(y_str)/self.ts_divider
            z = float(z_str)
            bs_data[y] = z
            self.min_y = min(self.min_y, y)
            self.max_y = max(self.max_y, y)
        # Update grid-boundary metrics
        self.min_x = min(self.min_x, x)
        self.max_x = max(self.max_x, x)
        # Add the data to any existing data sets for this blocksize
        self.io_bs[x] = self.io_bs.get(x, []) + [bs_data]
        self.iops_bs[x] = self.iops_bs.get(x, 0) + iops_total

    def aggregate_and_normalise(self):
        ''' We may have sampled multiple results per blocksize.
            Generate a weighted normalisation across all readings.
            This must be done once all results have been added. '''

        # For each blocksize
        for log2_bs, bs_results in self.io_bs.iteritems():
            z_total = float(self.iops_bs[log2_bs])
            io_density = []
            # For each fio result in this blocksize
            for bs_data in bs_results:
                prev_y = 0
                # For each datapoint in the result
                for y in sorted(bs_data.keys()):
                    # Process the IOs in order to construct
                    # IO frequency densities
                    z_norm = bs_data[y] / z_total
                    delta_y = y - prev_y
                    io_density_y = z_norm / delta_y
                    io_density += [{'lower': prev_y,
                                    'upper': y,
                                    'density': io_density_y}]
                    prev_y = y
            # The generated list of I/O frequency density ranges
            # is suitable for resampling on a regularised grid
            self.io_density[log2_bs] = io_density
        # Now, reinterpolate the data to a regular grid spacing
        # to enable aggregation and plotting.
        # Make coordinate arrays.
        self.grid_x = self.max_x - self.min_x + 1
        self.grid_X = np.linspace(self.min_x - 0.5,
                                  self.max_x + 0.5,
                                  self.grid_x + 1)
        if self.logscale:
            self.grid_Y = np.logspace(np.log10(self.min_y),
                                      np.log10(self.max_y),
                                      self.grid_y)
        else:
            self.grid_Y = np.linspace(self.min_y, self.max_y, self.grid_y)
        self.grid = grid = np.zeros((self.grid_y, self.grid_x), dtype=np.dtype('double'))
        # Perform the gridding interpolation
        for log2_bs, io_density in self.io_density.iteritems():
            col = log2_bs - self.min_x
            io_density_check = 0.0          # Paranoia
            grid_check = 0.0                # Paranoia
            grid_y_lower = 0.0
            for D in io_density:
                # for row in range(int(math.floor(D['lower'] / bin_y)), nrow):
                for row, grid_y_lower in enumerate(self.grid_Y[:-1]):
                    grid_y_upper = self.grid_Y[row+1]
                    # Non-overlap: below or above?
                    if grid_y_upper < D['lower']:
                        continue
                    if grid_y_lower > D['upper']:
                        break
                    bin_y = grid_y_upper - grid_y_lower
                    # Determine the extent of overlap
                    overlap_lower = max(grid_y_lower, D['lower'])
                    overlap_upper = min(grid_y_upper, D['upper'])
                    overlap_range = overlap_upper - overlap_lower
                    grid[row, col] += D['density'] * overlap_range / bin_y
                    # Paranoia
                    grid_check += D['density'] * overlap_range
                # Paranoia
                io_density_check += D['density']*(D['upper'] - D['lower'])
            # Paranoia
            if self.verbose:
                print "blocksize: %s cumulative density %f cumulative grid %f" % (2**log2_bs, io_density_check,grid_check)
            if (abs(io_density_check - 1) > self.tolerance or
                    abs(grid_check - 1) > self.tolerance):
                raise ValueError(
                    "CHECK FAILED: blocksize %d cumulative density %f cumulative grid %f"
                    % (2**log2_bs, io_density_check, grid_check))
        # Normalize grid
        grid /= grid.max()
        # Set empty bins to NaN to ensure they do not get plotted
        self.grid[grid == 0.0] = np.nan
        self.cfdf = pd.DataFrame(self.grid, columns=sorted(set(self.cldf.index)), index=self.grid_Y)
        self.cfdf.to_csv(self.output_dir/(self.mode+'-commit-latency-freq-dist.csv'))

    def plot_bw(self, figsize=(10, 8), fig=None, ax=None, ylim=None, kind='stacked', unit=''):
        if fig == None or ax == None:
            fig, ax = plt.subplots(figsize=figsize)
        if kind == 'boxplot':
            self.bwdf.apply(lambda x: x/self.bs_divider).boxplot(ax=ax)
        elif kind == 'stacked':
            ax.set_prop_cycle('color', [plt.cm.jet(i) for i in np.linspace(0, 1, len(self.bwdf))])
            self.bwdf.apply(lambda x: x/self.bs_divider).T.plot(ax=ax, stacked=True, legend=False, grid=True, ylim=ylim, linewidth=1)
        ax.set_title('Block size vs %s bandwidth - %s - %s - %s client(s)' % (self.mode, self.scenario, self.rw, self.num_clients))
        ax.set_xticks(sorted(set(self.cldf.index)))
        ax.set_xlabel('Block size - $2^n$')
        ax.set_ylabel('%s bandwidth ($%s$)' % (self.mode.capitalize(), self.bs_label))
        fig.savefig(str(self.output_dir/('%s-blocksize-vs-bandwidth.png' % kind)))
        return fig, ax

    def plot_cl(self, figsize=(10,8), fig=None, ax=None, percentiles=[50.0,95.0,99.0,99.99], xlim=None, ylim=None, cmap='gist_heat'):
        if fig == None or ax == None:
            fig, ax = plt.subplots(figsize=figsize)
        if xlim == None:
            xlim = [self.min_x, self.max_x]
        if ylim == None:
            ylim = [max(1, self.min_y), self.max_y]
        ax.pcolor(self.grid_X, self.grid_Y, self.grid, cmap=cmap, vmin=0.0, vmax=1.0)
        self.cldf[percentiles] \
            .groupby(self.cldf.index).mean() \
            .plot(ax=ax, xlim=xlim, ylim=ylim, linewidth=1, style='-', logy=self.logscale)
        ax.legend(title='percentiles')
        ax.set_title('Block size vs %s commit latency - %s - %s - %s client(s)' % (self.mode, self.scenario, self.rw, self.num_clients))
        ax.set_xticks(sorted(set(self.cldf.index)))
        ax.set_xlabel('Block size - $2^n$')
        ax.set_ylabel('%s commit latency - $%s$' % (self.mode.capitalize(), self.ts_label))
        fig.savefig(str(self.output_dir/'blocksize-vs-commit-latency.png'))
        return fig, ax

    def plot_cf(self, figsize=(10,8), fig=None, ax=None, xlim=None, ylim=None):
        if fig == None or ax == None:
            fig, ax = plt.subplots(figsize=figsize)
        legend = sorted(set(self.cfdf.T.index))
        if ylim == None:
            ylim = [max(1, self.min_y), self.max_y]
        ax.set_prop_cycle('color', [plt.cm.jet(i) for i in np.linspace(0, 1, len(legend))])
        for label, group in self.cfdf.T.iterrows():
            group.reset_index().set_index(label).plot.line(ax=ax, xlim=None, ylim=ylim, logy=self.logscale, grid=True)
        ax.legend(legend, title='block size ($2^n$)')
        ax.set_title('Distribution of %s commit latency - %s - %s - %s client(s)' % (self.mode, self.scenario, self.rw, self.num_clients))
        ax.set_xlabel('Relative frequency')
        ax.set_ylabel('%s commit latency - ($%s$)' % (self.mode.capitalize(), self.ts_label))
        fig.savefig(str(self.output_dir/'commit-latency-freq-dist.png'))
        return fig, ax

    def populate(self):
        # For each blocksize found, emit data from each listed job
        # FIXME: need to incorporate hostname and dataset name in the results
        # Emit bandwidth data points in column format
        bw = list()
        cl = list()
        for input_dir in self.input_dirs:
            print "Scanning for fio data in %s" % input_dir
            fio_file_list = get_fio_file_list(input_dir)
            fio_results = get_fio_results(fio_file_list)
            bs_list = sorted(fio_results.keys())
            for bs in bs_list:
                if bs not in self.skip_bs and bs <= self.max_bs:
                    log2_bs = int(math.log(bs,2))
                    for bs_job in fio_results[bs]['jobs']:
                        # Read and write bandwidth as a function of I/O size
                        bw.append({'log2_bs': log2_bs, 'bw': bs_job[self.mode]['bw']})
                        # IOPS and IO latency percentiles as a function of I/O size
                        row = {'log2_bs': log2_bs, 'iops': bs_job[self.mode]['iops']}
                        row.update({float(percentile): clat_ns/self.ts_divider for percentile, clat_ns in bs_job[self.mode]['clat_ns']['percentile'].iteritems()})
                        cl.append(row)
                        # Aggregate data from each dataset
                        self.add_series(log2_bs, bs_job[self.mode]['total_ios'], bs_job[self.mode]['clat_ns']['bins'])
                        if self.verbose:
                            print "I/O size %8d, job %s: %d samples" % (bs, self.mode, bs_job[self.mode]['total_ios'])
                if self.verbose:
                    print "Aggregated data for %d I/Os, max latency %f %s" % (sum(self.iops_bs.values()), self.max_y, self.timescale)
        self.cldf = pd.DataFrame(cl).set_index('log2_bs')
        bwdf = pd.DataFrame(bw).set_index('log2_bs')
        self.bwdf = pd.concat([pd.Series(row, name=i) for i, row in bwdf['bw']
                       .groupby(bwdf.index).apply(list).iteritems()], axis=1)
        self.bwdf.to_csv(self.output_dir/(self.mode+'-bandwidth.csv'))
        self.cldf.to_csv(self.output_dir/(self.mode+'-commit-latency.csv'))

    def ensure_output_dir(self, force):
        # Check the status of the output directory
        self.output_dir.mkdir(parents=True, exist_ok=force)
        for p in self.output_dir.iterdir():
            if force:
                print "Deleting existing output data %s in output directory" % (p)
                p.unlink()
            else:
                print "Output directory %s is not empty: use --force to overwrite it" % (self.output_dir)
                os.abort()


def get_fio_file_list(input_dir):
    # List JSON files in the fio input directory
    try:
        return list(input_dir.iterdir())
    except OSError as E:
        print "Could not access input directory %s" % (input_dir)
        raise E


def get_fio_results(fio_file_list):
    # Read in and parse the data files
    fio_results = {}
    for fio_file in fio_file_list:
        with fio_file.open('r') as fio_fd:
            try:
                fio_run_data = json.load(fio_fd)
                test_bs = int(fio_run_data['global options']['bs'])
                fio_results[test_bs] = fio_run_data
            except ValueError:
                print "Skipping %s: could not be parsed as JSON" % (fio_file)
                pass
            except KeyError:
                print "Skipping %s: data structure could not be parsed" % (fio_file)
                pass
    return fio_results
