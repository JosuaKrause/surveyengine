# -*- coding: utf-8 -*-
"""
Created on 2017-07-18

@author: joschi <josua.krause@gmail.com>

This package provides a customizable survey user interface.
"""
from setuptools import setup

import sys
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

# NOTE! steps to distribute:
#$ python setup.py sdist bdist_wheel
#$ twine upload dist/... <- here be the new version!

with open(path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    req = f.readlines()
if sys.version_info < (2, 7):
    req.append('argparse')
setup(
    name='surveyengine',
    version='0.0.1',
    description='surveyengine is a customizable survey web user interface.',
    long_description=long_description,
    url='https://github.com/JosuaKrause/surveyengine',
    author='Josua Krause',
    author_email='josua.krause@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='survey web server',
    py_modules=['quick_cache'],
    extras_require={
        'dev': [],
        'test': [],
    },
    data_files=[],
    entry_points={
        'console_scripts': [ 'surveyengine = surveyengine' ],
    },
    install_requires=req,
    maintainer='Josua Krause',
    maintainer_email='josua.krause@gmail.com'
)
