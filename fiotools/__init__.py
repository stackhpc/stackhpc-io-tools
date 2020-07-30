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
import pdb


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
                    bytescale='MB', min_bs=1, max_bs=65536, clients=32, verbose=False, plot=True):
        ''' Initialisation function. '''

        # Read input arguments
        self.grid_y = granularity
        self.logscale = logscale
        self.timescale = timescale
        self.min_bs = min_bs
        self.max_bs = max_bs
        self.skip_bs = skip_bs
        self.input_dirs = [Path(input_dir) for input_dir in input_dirs]
        self.output_dir = Path(output_dir)
        self.scenario = scenario
        self.rw = mode
        self.verbose = verbose

        # Infer these from input arguments
        self.num_clients = clients
        self.mode = "write" if "write" in mode else "read"
        self.ts_divider = self.ts_dict[timescale]['divider']
        self.ts_label = self.ts_dict[timescale]['label']
        self.bs_divider = self.bs_dict[bytescale]['divider']
        self.bs_label = self.bs_dict[bytescale]['label']

        # Initialise these
        self.min_X = np.inf
        self.max_X = 0
        self.min_Y = np.inf
        self.max_Y = 0.
        self.io_data = {}       # Timing data as a function of controlled parameter
        self.io_density = {}
        self.iops_data = {}     # Total IOPS as a function of controlled parameter

        # Function calls
        self.ensure_output_dir(force)
        if self.populate_for_clients(1024):
            self.aggregate_and_normalise()
            if plot:
                self.plot_cl_for_clients(1024)
                self.plot_bw_for_clients(1024)
                self.plot_iops_for_clients(1024)
                #self.plot_cf()

        self.ensure_output_dir(force)
        if self.populate_for_clients(4096):
            self.aggregate_and_normalise()
            if plot:
                self.plot_cl_for_clients(4096)
                self.plot_bw_for_clients(4096)
                self.plot_iops_for_clients(4096)
                #self.plot_cf()

        if self.populate_for_clients(65536):
            self.aggregate_and_normalise()
            if plot:
                self.plot_cl_for_clients(65536)
                self.plot_bw_for_clients(65536)
                self.plot_iops_for_clients(65536)
                #self.plot_cf()

        if self.populate_for_clients(262144):
            self.aggregate_and_normalise()
            if plot:
                self.plot_cl_for_clients(262144)
                self.plot_bw_for_clients(262144)
                self.plot_iops_for_clients(262144)
                #self.plot_cf()

        if self.populate_for_clients(1048576):
            self.aggregate_and_normalise()
            if plot:
                self.plot_cl_for_clients(1048576)
                self.plot_bw_for_clients(1048576)
                self.plot_iops_for_clients(1048576)
                #self.plot_cf()

        if self.populate_for_clients(2097152):
            self.aggregate_and_normalise()
            if plot:
                self.plot_cl_for_clients(2097152)
                self.plot_bw_for_clients(2097152)
                self.plot_iops_for_clients(2097152)
                #self.plot_cf()

    def add_series(self, x, iops_total, clat_data):
        ''' Each series is indexed by the controlled parameter x (I/O size or test clients)
            and the test mode.
            The y value is a histogram bin for I/O completion latency.
            The z value is the number of samples in this histogram bin.
            Multiple client series are stored independently at this stage
            and will be gridded, aggregated and normalised later on. '''

        # Paranoia: Check the iops_total matches the sum of all bins
        if sum(clat_data.values()) != iops_total:
            import pdb; pdb.set_trace()
            raise ValueError(
                "I/O size %d: sum of histogram bins is %d, expected %d" %
                (2**x, sum(clat_data.values()), iops_total))
        # Construct a dict of floating-point IO latencies
        io_data = {}
        for y_str, z_str in clat_data.iteritems():
            y = float(y_str)/self.ts_divider
            z = float(z_str)
            io_data[y] = z
            self.min_Y = min(self.min_Y, y)
            self.max_Y = max(self.max_Y, y)
        # Update grid-boundary metrics
        self.min_X = min(self.min_X, x)
        self.max_X = max(self.max_X, x)
        # Add the data to any existing data sets for this blocksize
        # Each entry for X is a dict of { Y: Z }
        self.io_data[x] = self.io_data.get(x, []) + [io_data]
        print "Column %d - IOPS total %d+%d" % (x, self.iops_data.get(x, 0), iops_total)
        self.iops_data[x] = self.iops_data.get(x, 0) + iops_total


    def aggregate_and_normalise(self):
        ''' We may have sampled multiple results per blocksize.
            These are stored in io_data[X] as lists of {Y:Z} dicts
            Generate a weighted normalisation across all readings.
            This must be done once all results have been added. '''

        # For each blocksize
        for X, X_results in self.io_data.iteritems():
            max_X_Z = 0.0
            Z_total = float(self.iops_data[X])
            io_density = []
            # For each fio result in this blocksize
            for YZ_data in X_results:
                prev_Y = 0
                # For each datapoint in the result
                for Y in sorted(YZ_data.keys()):
                    # Process the IOs in order to construct
                    # IO frequency densities
                    Z_norm = YZ_data[Y] / Z_total
                    delta_Y = Y - prev_Y
                    io_density_Y = Z_norm / delta_Y
                    io_density += [{'lower': prev_Y,
                                    'upper': Y,
                                    'density': io_density_Y}]
                    prev_Y = Y
                    max_X_Z = max(Z_norm, max_X_Z)

            # The generated list of I/O frequency density ranges
            # is suitable for resampling on a regularised grid
            self.io_density[X] = io_density
            print "Column %d normalised max %f" % (X, max_X_Z)

        # Now, reinterpolate the data to a regular grid spacing
        # to enable aggregation and plotting.
        # Make coordinate arrays.
        self.grid_x = self.max_X - self.min_X + 1
        self.grid_X = np.linspace(self.min_X - 0.5,
                                  self.max_X + 0.5,
                                  self.grid_x + 1)
        if self.logscale:
            self.grid_Y = np.logspace(np.log10(self.min_Y),
                                      np.log10(self.max_Y),
                                      self.grid_y)
        else:
            self.grid_Y = np.linspace(self.min_Y, self.max_Y, self.grid_y)
        self.grid = grid = np.zeros((self.grid_y, self.grid_x), dtype=np.dtype('double'))

        # Perform the gridding interpolation
        for X, io_density in self.io_density.iteritems():
            col = X - self.min_X
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
                print "blocksize: %s cumulative density %f cumulative grid %f" % (2**X, io_density_check,grid_check)
            if (abs(io_density_check - 1) > self.tolerance or
                    abs(grid_check - 1) > self.tolerance):
                raise ValueError(
                    "CHECK FAILED: blocksize %d cumulative density %f cumulative grid %f"
                    % (2**X, io_density_check, grid_check))

        # Normalize grid
        grid /= grid.max()
        # Set empty bins to NaN to ensure they do not get plotted
        self.grid[grid == 0.0] = np.nan
        #self.cfdf = pd.DataFrame(self.grid, columns=sorted(set(self.cldf.index)), index=self.grid_Y)
        #self.cfdf.to_csv(self.output_dir/(self.mode+'-commit-latency-freq-dist.csv'))

    def plot_bw(self, figsize=(10, 8), fig=None, ax=None, ylim=None, kind='stacked', unit=''):
        if fig == None or ax == None:
            fig, ax = plt.subplots(figsize=figsize)
        if kind == 'boxplot':
            self.bwdf.apply(lambda x: x/self.bs_divider).boxplot(ax=ax)
        elif kind == 'stacked':
            ax.set_prop_cycle('color', [plt.cm.jet(i) for i in np.linspace(0, 1, len(self.bwdf))])
            self.bwdf.apply(lambda x: x/self.bs_divider).T.plot(ax=ax, stacked=True, legend=False, grid=True, ylim=ylim, linewidth=1)
        ax.set_title('Block size vs %s bandwidth - %s - %s - %s client(s)' % (self.mode, self.scenario, self.rw, self.num_clients))
        ax.set_xticks(sorted(set(self.bwdf.index)))
        ax.set_xlabel('Block size - $2^n$')
        ax.set_ylabel('%s bandwidth ($%s$)' % (self.mode.capitalize(), self.bs_label))
        fig.savefig(str(self.output_dir/('%s-blocksize-vs-bandwidth.png' % kind)))
        return fig, ax

    def plot_bw_for_clients(self, bs, figsize=(10, 8), fig=None, ax=None, ylim=None, kind='stacked', unit=''):
        if fig == None or ax == None:
            fig, ax = plt.subplots(figsize=figsize)
        if kind == 'boxplot':
            self.bwdf.apply(lambda x: x/self.bs_divider).boxplot(ax=ax)
        elif kind == 'stacked':
            ax.set_prop_cycle('color', [plt.cm.jet(i) for i in np.linspace(0, 1, len(self.bwdf))])
            self.bwdf.apply(lambda x: x/self.bs_divider).T.plot(ax=ax, stacked=True, legend=False, grid=True, ylim=ylim, linewidth=1)
        ax.set_title('Number of clients vs %s bandwidth - %s - %d %s' % (self.mode, self.scenario, bs, self.rw))
        ax.set_xticks(sorted(set(self.bwdf.index)))
        ax.set_xlabel('Test clients')
        ax.set_ylabel('%s bandwidth ($%s$)' % (self.mode.capitalize(), self.bs_label))
        fig.savefig(str(self.output_dir/('%s-test-clients-vs-bandwidth-%d.png' % (kind,bs))))
        return fig, ax

    def plot_iops_for_clients(self, bs, figsize=(10, 8), fig=None, ax=None, ylim=None, kind='stacked', unit=''):
        if fig == None or ax == None:
            fig, ax = plt.subplots(figsize=figsize)
        if kind == 'boxplot':
            self.iopsdf.boxplot(ax=ax)
        elif kind == 'stacked':
            ax.set_prop_cycle('color', [plt.cm.jet(i) for i in np.linspace(0, 1, len(self.iopsdf))])
            self.iopsdf.T.plot(ax=ax, stacked=True, legend=False, grid=True, ylim=ylim, linewidth=1)
        ax.set_title('Number of clients vs %s IOPS - %s - %d %s' % (self.mode, self.scenario, bs, self.rw))
        ax.set_xticks(sorted(set(self.iopsdf.index)))
        ax.set_xlabel('Test clients')
        ax.set_ylabel('%s IOPS' % self.mode.capitalize())
        fig.savefig(str(self.output_dir/('%s-test-clients-vs-iops-%d.png' % (kind,bs))))
        return fig, ax


    def plot_cl(self, figsize=(10,8), fig=None, ax=None, percentiles=[50.0,95.0,99.0,99.99], xlim=None, ylim=None, cmap='gist_heat'):
        if fig == None or ax == None:
            fig, ax = plt.subplots(figsize=figsize)
        if xlim == None:
            xlim = [self.min_X, self.max_X]
        if ylim == None:
            ylim = [max(1, self.min_Y), self.max_Y]
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

    def plot_cl_for_clients(self, bs, figsize=(10,8), fig=None, ax=None, percentiles=[50.0,95.0,99.0,99.99], xlim=None, ylim=None, cmap='gist_heat'):
        if fig == None or ax == None:
            fig, ax = plt.subplots(figsize=figsize)
        if xlim == None:
            xlim = [self.min_X - 0.5, self.max_X + 0.5]
        if ylim == None:
            ylim = [max(1, self.min_Y), self.max_Y]
        ax.pcolor(self.grid_X, self.grid_Y, self.grid, cmap=cmap, vmin=0.0, vmax=1.0)
        self.cldf[percentiles] \
            .groupby(self.cldf.index).mean() \
            .plot(ax=ax, xlim=xlim, ylim=ylim, linewidth=1, style='-', logy=self.logscale)
        ax.legend(title='percentiles')
        ax.set_title('Number of clients vs %s commit latency - %s - %d %s' % (self.mode, self.scenario, bs, self.rw))
        ax.set_xticks(sorted(set(self.cldf.index)))
        ax.set_xlabel('Test clients')
        ax.set_ylabel('%s commit latency - $%s$' % (self.mode.capitalize(), self.ts_label))
        fig.savefig(str(self.output_dir/('test-clients-vs-commit-latency-%d.png' % bs)))
        return fig, ax

    def plot_cf(self, figsize=(10,8), fig=None, ax=None, xlim=None, ylim=None):
        if fig == None or ax == None:
            fig, ax = plt.subplots(figsize=figsize)
        legend = sorted(set(self.cfdf.T.index))
        if ylim == None:
            ylim = [max(1, self.min_Y), self.max_Y]
        ax.set_prop_cycle('color', [plt.cm.jet(i) for i in np.linspace(0, 1, len(legend))])
        for label, group in self.cfdf.T.iterrows():
            group.reset_index().set_index(label).plot.line(ax=ax, xlim=None, ylim=ylim, logy=self.logscale, grid=True)
        ax.legend(legend, title='block size ($2^n$)')
        ax.set_title('Distribution of %s commit latency - %s - %s - %s client(s)' % (self.mode, self.scenario, self.rw, self.num_clients))
        ax.set_xlabel('Relative frequency')
        ax.set_ylabel('%s commit latency - ($%s$)' % (self.mode.capitalize(), self.ts_label))
        fig.savefig(str(self.output_dir/'commit-latency-freq-dist.png'))
        return fig, ax

    def populate_for_bs(self):
        # For each blocksize found, emit data from each listed job
        # FIXME: need to incorporate hostname and dataset name in the results
        # Emit bandwidth data points in column format
        bw = list()
        cl = list()
        for input_dir in self.input_dirs:
            print "Scanning for fio data in %s" % input_dir
            fio_file_list = get_fio_file_list(input_dir)
            fio_results = get_fio_results(fio_file_list)
            if self.num_clients not in fio_results:
                print "No data for %d-client config found in %s" % (self.num_clients, input_dir)
                continue
            bs_list = sorted(fio_results[self.num_clients].keys())
            for bs in bs_list:
                if bs not in self.skip_bs and bs >= self.min_bs and bs <= self.max_bs:
                    log2_bs = int(math.log(bs,2))
                    for bs_job in fio_results[self.num_clients][bs]['jobs']:
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
                    print "%d-client config: Aggregated data for %d I/Os, max latency %f %s" % (self.num_clients, sum([x['iops'] for x in cl]), self.max_Y, self.timescale)

        if not bw:
            print "No data found for %d-client configuration in %s" % (self.num_clients, [str(x) for x in self.input_dirs])
            return False

        self.cldf = pd.DataFrame(cl).set_index('log2_bs')
        bwdf = pd.DataFrame(bw).set_index('log2_bs')
        self.bwdf = pd.concat([pd.Series(row, name=i) for i, row in bwdf['bw']
                       .groupby(bwdf.index).apply(list).iteritems()], axis=1)
        self.bwdf.to_csv(self.output_dir/(self.mode+'-bandwidth.csv'))
        self.cldf.to_csv(self.output_dir/(self.mode+'-commit-latency.csv'))

        return True

    def populate_for_clients(self, bs):
        # For a constant blocksize, generate data using the test clients as variable parameter.
        # Emit data from each listed job
        bw = list()
        iops = list()
        cl = list()
        for input_dir in self.input_dirs:
            print "Scanning for fio data in %s" % input_dir
            fio_file_list = get_fio_file_list(input_dir)
            fio_results = get_fio_results(fio_file_list)
            for num_clients in sorted(fio_results.keys()):
                if bs not in fio_results[num_clients]:
                    continue

                for bs_client in fio_results[num_clients][bs]:
                    bs_job = bs_client['jobs'][0]               # FIXME: Assume one job per client
                    # Read and write bandwidth as a function of I/O size
                    bw.append({'test_clients': num_clients, 'bw': bs_job[self.mode]['bw']})
                    iops.append({'test_clients': num_clients, 'iops': bs_job[self.mode]['iops']})
                    # IOPS and IO latency percentiles as a function of I/O size
                    row = {'test_clients': num_clients, 'iops': bs_job[self.mode]['iops']}
                    row.update({float(percentile): clat_ns/self.ts_divider for percentile, clat_ns in bs_job[self.mode]['clat_ns']['percentile'].iteritems()})
                    cl.append(row)
                    # Aggregate data from each dataset
                    # A curiosity with fio: in some cranky cases the total_ios is not the sum of the histograms.
                    # However it appears the io_kbytes / bs is more reliable.
                    total_ios = bs_job[self.mode]['total_ios']
                    check_ios = bs_job[self.mode]['io_kbytes'] * 1000 / bs
                    sum_ios = sum(bs_job[self.mode]['clat_ns']['bins'].values())
                    if check_ios != total_ios or sum_ios != total_ios:
                        print "%d-client config, I/O size %d, job %s: differing total IOs total_ios %d io_kbytes %d clat sum %d" % (num_clients, bs, self.mode, total_ios, check_ios, sum_ios)
                        total_ios = sum_ios
                    self.add_series(num_clients, total_ios, bs_job[self.mode]['clat_ns']['bins'])
                    if self.verbose:
                        print "%d-client config, I/O size %d, job %s: %d samples" % (num_clients, bs, self.mode, total_ios)
            if self.verbose:
                print "%d-client config: Aggregated data for %d I/Os, max latency %f %s" % (self.num_clients, sum([x['iops'] for x in cl]), self.max_Y, self.timescale)

        if not bw:
            print "No data found for %d-client configuration in %s" % (self.num_clients, [str(x) for x in self.input_dirs])
            return False

        self.cldf = pd.DataFrame(cl).set_index('test_clients')
        bwdf = pd.DataFrame(bw).set_index('test_clients')
        self.bwdf = pd.concat([pd.Series(row, name=i) for i, row in bwdf['bw']
                       .groupby(bwdf.index).apply(list).iteritems()], axis=1)
        iopsdf = pd.DataFrame(iops).set_index('test_clients')
        self.iopsdf = pd.concat([pd.Series(row, name=i) for i, row in iopsdf['iops']
                       .groupby(iopsdf.index).apply(list).iteritems()], axis=1)

        self.cldf.to_csv(self.output_dir/(self.mode+'-commit-latency-by-client.csv'))
        self.bwdf.to_csv(self.output_dir/(self.mode+'-bandwidth-by-client.csv'))
        self.iopsdf.to_csv(self.output_dir/(self.mode+'-iops-by-client.csv'))

        return True


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
    results = []

    try:
        # Recursive directory traversal
        for root, dirs, files in os.walk(str(input_dir)):
            results += [ os.path.join(root, x) for x in files ]
            #for subdir in dirs:
                #results += get_fio_file_list( os.path.join(root,subdir) )
    except OSError as E:
        print "Could not access input directory %s" % (input_dir)
        raise E

    return results


def get_fio_results(fio_file_list):
    # Read in and parse the data files
    fio_results = {}
    for fio_file in fio_file_list:
        with open(fio_file, 'r') as fio_fd:
            try:
                fio_run_data = json.load(fio_fd)
                test_bs = int(fio_run_data['global options']['bs'])
                test_clients = int(fio_run_data['meta']['total_clients'])
                if test_clients not in fio_results:
                    fio_results[test_clients] = {}
                if test_bs not in fio_results[test_clients]:
                    fio_results[test_clients][test_bs] = []
                fio_results[test_clients][test_bs] += [fio_run_data]
            except ValueError:
                print "Skipping %s: could not be parsed as JSON" % (fio_file)
                pass
            except KeyError as E:
                print "Skipping %s: data structure could not be parsed: %s" % (fio_file, str(E))
                pass
    return fio_results
