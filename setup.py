#!/usr/bin/env python3
import sys

if sys.version_info < (3, 3):
	print('Only Python 3.3 or later is supported')
	sys.exit(1)

from distutils.core import setup

from web import name, version

setup(
	name=name,
	version=version,
	description='A simple, threading, RESTful web server in Python',
	license='MIT',
	author='Foster McLane',
	author_email='fkmclane@gmail.com',
	packages=['web'],
)
