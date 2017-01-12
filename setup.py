#!/usr/bin/env python3
from setuptools import setup, find_packages

from web import name, version


setup(
    name=name,
    version=version,
    description='a simple, threading, RESTful web server in Python',
    license='MIT',
    url='https://github.com/fkmclane/vbx',
    author='Foster McLane',
    author_email='fkmclane@gmail.com',
    setup_requires=['pytest-runner', 'pytest-cov'],
    tests_require=['pytest'],
    packages=find_packages(),
)
