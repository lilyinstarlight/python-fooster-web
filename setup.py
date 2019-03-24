#!/usr/bin/env python3
import os
import re
import sys

from setuptools import setup, find_packages


name = None
version = None


def find(haystack, *needles):
    regexes = [(index, re.compile("^{}\s*=\s*'([^']*)'$".format(needle))) for index, needle in enumerate(needles)]
    values = ['' for needle in needles]

    for line in haystack:
        if len(regexes) == 0:
            break

        for rindex, (vindex, regex) in enumerate(regexes):
            match = regex.match(line)
            if match:
                values[vindex] = match.groups()[0]
                del regexes[rindex]
                break

    return values


with open(os.path.join(os.path.dirname(__file__), 'fooster', 'web', 'web.py'), 'r') as web:
    name, version = find(web, 'name', 'version')


setup(
    name=name,
    version=version,
    description='a simple, multiprocessing, RESTful web server in Python',
    license='MIT',
    url='https://github.com/fkmclane/python-fooster-web',
    author='Foster McLane',
    author_email='fkmclane@gmail.com',
    setup_requires=(['pytest-runner'] if len(sys.argv) > 1 and sys.argv[1] == 'test' else []),
    tests_require=['pytest', 'pytest-cov', 'coverage>=4.2'],
    packages=find_packages(),
    namespace_packages=['fooster'],
)
