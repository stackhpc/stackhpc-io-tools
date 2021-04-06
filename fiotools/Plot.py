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

####################################################################################################

class BandwidthClient(StackedLine):
    ''' Stacked Line plot of bandwidth against number of clients '''

    def __init__(self, jobname, io_size, run_data, output_dir='.'):
        ''' Constructor from a series of samples and refining parameters '''

        # Reduce to a subset selecting all samples matching required criteria
        # sub_data will contain only the samples we require
        sub_data = copy.copy( run_data )
        sub_data.select_samples( lambda S: S.io_size == io_size and S.jobname == jobname )

        # Extract data for each host in the series.
        # SeriesGroup - contains samples from many runs
        #   Sample - contains results from many hosts
        #     Result - contains data for one host, including hostname
        clients = sub_data.hostnames()
        client_index = set()
        client_sample_data = {}
        client_sample_len = {}
        for client in clients:
            # We get back a list of tuples - (hostname, jobname, num clients, io size, Result)
            client_data = sub_data.extract_results( lambda S: S.hostname == client and S.jobname == jobname )

            # Ordering of clients for plotting: sample length->[hostnames]
            print("Host %s Runs %d" % (client, len(client_data)))
            sample_len = len(client_data)
            if sample_len not in client_sample_len:
                client_sample_len[sample_len] = []
            client_sample_len[sample_len].append(client)

            # Pivoted data sample hostname->num_clients->bandwidth_value
            client_bw = { x[2]: x[4].fio_data['bw']/1000.0 for x in client_data }
            client_sample_data[client] = pd.Series(data=client_bw, name=client).sort_index()

            # Construct a set of populated client values
            client_index.update( [x[2] for x in client_data] )

        # Generate an ordering of clients for neater stacking
        client_sample_ordered = []
        for nsamples in sorted(client_sample_len.keys(), reverse=True):
            for client in client_sample_len[nsamples]:
                client_sample_ordered.append(client_sample_data[client])

        # Convert to pandas dataframes
        DF = pd.DataFrame(client_sample_ordered)

        # Find the maximum stacked value, rounded up to the nearest 1000 MB/s
        ymax = 0.0
        for i in DF.T.index:
            ymax = max(ymax, DF[i].sum())
        ymax = math.ceil(ymax / 1000.0) * 1000.0
        ylim = (0.0, ymax)

        figsize=(10, 8)
        fig, ax = plt.subplots(figsize=figsize)
        ax.set_prop_cycle('color', [plt.cm.jet(i) for i in np.linspace(0, 1, len(clients))])
        DF.T.plot(ax=ax, stacked=True, legend=False, grid=True, ylim=ylim, linewidth=1)
        ax.set_title('Bandwidth vs clients - %s - %d' % (jobname, io_size))
        ax.set_xticks(sorted(client_index))
        ax.set_xlabel('Test clients')
        ax.set_ylabel('%s bandwidth ($%s$)' % (jobname.capitalize(), "MB/s"))
        fig.savefig(('%s/%s-test-clients-vs-bandwidth-%d.png' % (output_dir,jobname,io_size)))

