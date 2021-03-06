﻿#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2015:
#   Frederic Mohier, frederic.mohier@gmail.com
#
# This file is part of (alignak_counters).
#
# (alignak_counters) is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# (alignak_counters) is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with (alignak_counters).  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import re
del os.link
from importlib import import_module

try:
    from setuptools import setup, find_packages
except:
    sys.exit("Error: missing python-setuptools library")

try:
    python_version = sys.version_info
except:
    python_version = (1, 5)
if python_version < (2, 7):
    sys.exit("This application requires a minimum Python 2.7.x, sorry!")
elif python_version >= (3,):
    sys.exit("This application is not yet compatible with Python 3.x, sorry!")

from alignak_counters import __application__, __version__, __author__, __copyright__
from alignak_counters import __releasenotes__, __license__, __doc_url__
from alignak_counters import __name__ as __pkg_name__

package = import_module('alignak_counters')

install_requires = [
    'docopt', 'future'
]

# Define paths
if 'linux' in sys.platform or 'sunos5' in sys.platform:
    paths = {
        'bin':     "/usr/bin",
        'var':     "/var/lib/alignak_counters/",
        'share':   "/var/lib/alignak_counters/share",
        'etc':     "/etc/alignak_counters",
        'run':     "/var/run/alignak_counters",
        'log':     "/var/log/alignak_counters",
        'libexec': "/var/lib/alignak_counters/libexec",
    }
elif 'bsd' in sys.platform or 'dragonfly' in sys.platform:
    paths = {
        'bin':     "/usr/local/bin",
        'var':     "/usr/local/libexec/alignak_counters",
        'share':   "/usr/local/share/alignak_counters",
        'etc':     "/usr/local/etc/alignak_counters",
        'run':     "/var/run/alignak_counters",
        'log':     "/var/log/alignak_counters",
        'libexec': "/usr/local/libexec/alignak_counters/plugins",
    }
else:
    print "Unsupported platform, sorry!"
    exit(1)

setup(
    name=__pkg_name__,
    version=__version__,

    license=__license__,

    # metadata for upload to PyPI
    author="Frédéric MOHIER",
    author_email="frederic.mohier@gmail.com",
    keywords="alignak REST backend tool",
    url="https://github.com/Alignak-monitoring-contrib/alignak-webui",
    description=package.__doc__.strip(),
    long_description=open('README.rst').read(),

    zip_safe=False,

    packages=find_packages(),
    include_package_data=True,
    # package_data={
        # 'sample': ['package_data.dat'],
    # },
    # data_files = [(paths['etc'], ['etc/settings.cfg'])],

    install_requires=install_requires,

    entry_points={
        'console_scripts': [
            'alignak_counters = alignak_counters.cfg_to_backend:main',
        ],
    },

    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Topic :: System :: Monitoring',
        'Topic :: System :: Systems Administration'
    ]
)
