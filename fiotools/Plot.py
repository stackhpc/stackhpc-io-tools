# Copyright 2021 StackHPC Ltd
# Begun by Stig Telfer, StackHPC Ltd, March 2021

import copy
import math
import pandas as pd
import numpy as np

import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt 

class StackedLine:
    ''' Stacked Line plots '''
    def __init__(self, jobname, sub_data, metric, scale_factor=1.0):

        self.sub_data = sub_data

        # Extract data for each host in the series.
        # SeriesGroup - contains samples from many runs
        #   Sample - contains results from many hosts
        #     Result - contains data for one host, including hostname
        self.clients = self.sub_data.hostnames()
        self.client_index = set()
        client_sample_data = {}
        client_sample_len = {}
        for client in self.clients:
            # We get back a list of tuples - (hostname, jobname, num clients, io size, Result)
            client_data = self.sub_data.extract_results( lambda S: S.hostname == client and S.jobname == jobname )

            # Ordering of clients for plotting: sample length->[hostnames]
            print("Host %s Runs %d" % (client, len(client_data)))
            sample_len = len(client_data)
            if sample_len not in client_sample_len:
                client_sample_len[sample_len] = []
            client_sample_len[sample_len].append(client)

            # Pivoted data sample hostname->num_clients->bandwidth_value
            client_result = { x[2]: x[4].fio_data[metric]*scale_factor for x in client_data }
            client_sample_data[client] = pd.Series(data=client_result, name=client).sort_index()

            # Construct a set of populated client values
            self.client_index.update( [x[2] for x in client_data] )

        # Generate an ordering of clients for neater stacking
        client_sample_ordered = []
        for nsamples in sorted(client_sample_len.keys(), reverse=True):
            for client in client_sample_len[nsamples]:
                client_sample_ordered.append(client_sample_data[client])

        # Convert to pandas dataframes
        self.DF = pd.DataFrame(client_sample_ordered)

    def plot(self, title, ylabel, quantisation, outfile):

        # Find the maximum stacked value, rounded up to the nearest 1000 MB/s
        ymax = 0.0
        for i in self.DF.T.index:
            ymax = max(ymax, self.DF[i].sum())
        ymax = math.ceil(ymax / quantisation) * quantisation
        ylim = (0.0, ymax)

        figsize=(10, 8)
        fig, ax = plt.subplots(figsize=figsize)
        ax.set_prop_cycle('color', [plt.cm.jet(i) for i in np.linspace(0, 1, len(self.clients))])
        self.DF.T.plot(ax=ax, stacked=True, legend=False, grid=True, ylim=ylim, linewidth=1)
        ax.set_title(title)
        ax.set_xticks(sorted(self.client_index))
        ax.set_xlabel('Test clients')
        ax.set_ylabel(ylabel)
        fig.savefig(outfile)


####################################################################################################

class BandwidthClient(StackedLine):
    ''' Stacked Line plot of bandwidth against number of clients '''

    def __init__(self, jobname, io_size, run_data, output_dir='.'):
        ''' Constructor from a series of samples and refining parameters '''

        # Reduce to a subset selecting all samples matching required criteria
        # sub_data will contain only the samples we require
        sub_data = copy.copy( run_data )
        sub_data.select_samples( lambda S: S.io_size == io_size and S.jobname == jobname )

        # Extract the required data
        super(BandwidthClient, self).__init__( jobname, sub_data, 'bw', 0.001 )

class IOPSClient(StackedLine):
    ''' Stacked Line plot of IOPS againstknumber of clients '''

    def __init__(self, jobname, io_size, run_data, output_dir='.'):
        ''' Constructor from a series of samples and refining parameters '''

        # Reduce to a subset selecting all samples matching required criteria
        # sub_data will contain only the samples we require
        sub_data = copy.copy( run_data )
        sub_data.select_samples( lambda S: S.io_size == io_size and S.jobname == jobname )

        # Extract the required data
        super(IOPSClient, self).__init__( jobname, sub_data, 'iops', 0.001 )


class BandwidthBS(StackedLine):
    ''' Stacked Line plot of bandwidth against blocksize '''

    def __init__(self, jobname, io_size, run_data, output_dir='.'):
        ''' Constructor from a series of samples and refining parameters '''

        # Reduce to a subset selecting all samples matching required criteria
        # sub_data will contain only the samples we require
        sub_data = copy.copy( run_data )

        # STIG: Not just the one parent class constructor
        # One method for per-client plots, one for per BS

        # Extract the required data
        super(BandwidthBS, self).__init__( jobname, sub_data, 'bw', 0.001 )

#class IOPSBS(StackedLine):
#    ''' Stacked Line plot of IOPS againstknumber of clients '''
#
#    def __init__(self, jobname, io_size, run_data, output_dir='.'):
#        ''' Constructor from a series of samples and refining parameters '''
#
#        # Extract the required data
#        super(IOPSClient, self).__init__( jobname, io_size, run_data, 'iops', 0.001 )
