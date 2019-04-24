#!/usr/bin/env python
import os.path

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

long_description = ""
with open('README.md') as f:
    long_description = f.read()

setup(
    name='fiotools',
    version=open(os.path.join('fiotools', 'VERSION')).read().strip(),
    author='Stig Telfer',
    author_email='stig@stackhpc.com',
    packages=['fiotools', 'fiotools.tests'],
    package_data={'fiotools': [os.path.join('tests', 'urls.txt'), 'VERSION']},
    scripts=['bin/fio_parse', 'bin/templater'],
    url='https://github.com/stackhpc/stackhpc-io-tools',
    license='Apache (see LICENSE file)',
    description='IO json parser and plotter',
    long_description=long_description,
    python_requires=">=2.7",
    install_requires=[
        'matplotlib',
        'pandas',
        'numpy',
        'pathlib2',
        'unittest2',
        ],
    test_suite='fiotools.tests'
)
