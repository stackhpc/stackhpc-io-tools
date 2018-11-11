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
    name='iotools',
    version=open(os.path.join('iotools', 'VERSION')).read().strip(),
    author='Stig Telfer',
    author_email='stig@stackhpc.com',
    packages=['iotools', 'iotools.tests'],
    package_data={'iotools': [os.path.join('tests', 'urls.txt'), 'VERSION']},
    scripts=['fio_parse'],
    url='https://github.com/stackhpc/stackhpc-io-tools',
    license='Apache (see LICENSE file)',
    description='IO json parser and plotter',
    long_description=long_description,
    python_requires=">=2.7",
    install_requires=[
        'matplotlib',
        'pandas',
        'numpy',
        ],
    test_suite='iotools.tests'
)