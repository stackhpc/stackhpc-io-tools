# Copyright 2021 StackHPC Ltd
# Begun by Stig Telfer, StackHPC Ltd, March 2021

import json
import os

####################################################################################################

class Result:
    ''' A single fio result from a single host. '''

    def __init__(self, fio_data):
        ''' Constructor from fio JSON data '''

        # Validation
        if 'job options' not in fio_data:
            raise KeyError("FIO sample output missing job options data")
        if fio_data['job options']['rw'] not in ['read','write']:
            raise TypeError("Cannot process unexpected job type %s" % (fio_data['job options']['rw']))

        # Assign the JSON dict from either read or write case
        self.fio_data = fio_data[fio_data['job options']['rw']]
        self.hostname = fio_data['hostname']
        self.rw = fio_data['job options']['rw']
        self.io_size = self.fio_data['io_bytes'] / self.fio_data['total_ios']
        self.usr_cpu = fio_data['usr_cpu']
        self.sys_cpu = fio_data['sys_cpu']
        self.jobname = fio_data['jobname']

####################################################################################################

class Sample:
    ''' A Sample is a group of results from different clients that ran together.
        The results have constant I/O type and constant I/O size '''

    def __init__(self, sample_group):

        self.clients = len(sample_group)
        assert self.clients >= 1, "Constructed with empty sample data"
        self.jobname = sample_group[0].jobname
        self.io_size = sample_group[0].io_size

        # Paranoia
        for sample in sample_group:
            assert sample.jobname == self.jobname, "Mismatch of jobnames in sample"
            assert sample.io_size == self.io_size, "Mismatch of IO size in sample"

        self.sample_group = sample_group

    def extract_results(self, selector):
        ''' Might be better to extract rather than select
            Return a list of tuples of hostname, jobname, num_clients, io_size, Result '''
        result = []
        for S in self.sample_group:
            if selector(S):
                result.append( (S.hostname, self.jobname, self.clients, self.io_size, S) )
        return result

    def hostnames(self):
        H = set()
        for S in self.sample_group:
            # Slightly contorted syntax to ensure the hostname is added as a string
            H.update( (S.hostname,) )
        return H

class SampleGroup(Sample):
    ''' A SampleGroup is a Sample that was generated using fio's client-server model
        and group reporting. '''

    def __init__(self, path):
        with open(path) as f:
            S = json.load(f)

        # Validation of input format
        if 'global options' not in S or 'client_stats' not in S:
            raise KeyError("FIO sample output did not contain expected structure")
        if int(S['global options']['group_reporting']) != 1:
            raise TypeError("FIO Group reporting mode was not found in the sample output")
        if len(S['client_stats']) < 1:
            raise ValueError("FIO sample output did not contain any client result data")

        # We could potentially make use of the "All clients" aggregated sample,
        # although it will not be available in other formats
        sample_group = [ Result(C) for C in S['client_stats'] if C['jobname'] != "All clients"]
        super(SampleGroup,self).__init__( sample_group )

class SampleDir(Sample):
    ''' A SampleDir is a directory tree of fio results that executed independently,
        but at the same time as one another. '''
    # WRITEME

####################################################################################################

class SeriesGroup:
    ''' Construct a series of samples for plotting '''

    def __init__(self, input_dir=None):
        ''' Given a directory of results, iterate the results to create a collection of samples '''
        # A dict indexed by number of client and returning sample data
        self.samples = []
        if input_dir:
            for root, dirs, files in os.walk(input_dir):
                self.samples = [ SampleGroup(os.path.join(root, F)) for F in files if not F.startswith('.') ]
                print( "Found %d fio results in %s" % (len(self.samples), input_dir) )

    def select_samples(self, selector):
        ''' Constrain a series only to samples that match a given criteria '''
        self.samples[:] = [S for S in self.samples if selector(S)]

    def extract_results(self, selector):
        ''' Extract results in each sample that match the given criteria.
            The selector function is applied against each Result object for match.
            The data returned is a list of tuples of hostname, jobname, num clients, io_size, Result '''
        result = []
        for S in self.samples:
            result += S.extract_results(selector)
        return result

    def hostnames(self):
        ''' Find the set of unique hostnames within the series of samples '''
        H = set()
        for S in self.samples:
            H.update( S.hostnames() )
        return H

    def io_sizes(self):
        ''' Find the set of unique IO sizes within the series of samples '''
        return set(S.io_size for S in self.samples)
