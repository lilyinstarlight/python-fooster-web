#!/usr/bin/env python3
import os
import re
import sys

from setuptools import setup, find_packages


name = None
version = None


def find(haystack, *needles):
    regexes = [(index, re.compile(r'^{}\s*=\s*[\'"]([^\'"]*)[\'"]$'.format(needle))) for index, needle in enumerate(needles)]
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


with open(os.path.join(os.path.dirname(__file__), 'README.md'), 'r') as rfile:
    readme = rfile.read()


setup(
    name=name,
    version=version,
    description='a small, process-pooled web server utilizing the built-in Python socketserver',
    long_description=readme,
    long_description_content_type='text/markdown',
    license='MIT',
    url='https://github.com/fkmclane/python-fooster-web',
    author='Foster McLane',
    author_email='fkmclane@gmail.com',
    python_requires='>=3.4',
    setup_requires=(['pytest-runner'] if len(sys.argv) > 1 and sys.argv[1] == 'test' else []),
    tests_require=['pytest', 'pytest-cov', 'coverage>=4.2'],
    packages=find_packages(),
    namespace_packages=['fooster'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: Freely Distributable',
        'Operating System :: POSIX',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS :: MacOS X',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Internet :: WWW/HTTP :: HTTP Servers',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
    ],
)
