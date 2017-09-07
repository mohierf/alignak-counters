#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2015-2016: Alignak team, see AUTHORS.txt file for contributors
#
# This file is part of Alignak Backend Import.
#
# Alignak Backend Import is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Alignak Backend Import is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Alignak Backend Import.  If not, see <http://www.gnu.org/licenses/>.

"""
alignak_backend_counters command line interface::

    Usage:
        {command} [-h]
        {command} [-v] [-q]
                  [-b=url] [-u=username] [-p=password]
                  [-H=hostnames] [-S=services] [-M=metrics]

    Options:
        -h, --help                      Show this screen.
        -V, --version                   Show application version.
        -b, --backend url               Specify backend URL [default: http://127.0.0.1:5000]
        -u, --username username         Backend login username [default: admin]
        -p, --password password         Backend login password [default: admin]
        -v, --verbose                   Run in verbose mode (more info to display)
        -q, --quiet                     Run in quiet mode (display nothing)
        -H, --hostnames hosts           Extract data for a list of hosts [default: all]
        -S, --services services         Extract data for a list of services [default: all]
        -M, --metrics metrics           Extract data for a list of counters [default: all]

    Use cases:
        Display help message:
            {command} -h

        Display current version:
            {command} -v

        Get data in the backend (all hosts and services):
            {command} [-b=backend] [-u=username] [-p=password]

        Get data in the default backend for the services S& and S2 of an host named 'localhost':
            {command} -v -H localhost -S "S1,S2"

        Exit code:
            0 if required operation succeeded
            1 if some missing modules are not installed on your system
            2 if backend access is denied (run the backend and/or check provided username/password)
            3 if required configuration cannot be loaded by Alignak
            4 if some problems were encountered during backend importation
            5 if an exception occured when creating/updating data in the Alignak backend

            64 if command line parameters are not used correctly
"""
from __future__ import print_function

import traceback
import json
import logging

import time
from calendar import timegm
from datetime import datetime
from dateutil import tz

from docopt import docopt
from docopt import DocoptExit

from alignak_backend_client.client import Backend, BackendException

from alignak_counters import __version__
from alignak_counters.perfdata import PerfDatas

# Configure logger
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)8s - %(message)s')
# Name the logger to get the backend client logs
logger = logging.getLogger('alignak-backend-counters')
logger.setLevel('INFO')


def get_ts_date(param_date, date_format):
    """
        Get date as a timestamp
    """
    if isinstance(param_date, (int, long, float)):
        # Date is received as a float or integer, store as a timestamp ...
        # ... and assume it is UTC
        # ----------------------------------------------------------------
        return param_date
    elif isinstance(param_date, basestring):
        try:
            # Date is supposed to be received as string formatted date
            timestamp = timegm(time.strptime(param_date, date_format))
            return timestamp
        except ValueError:
            print(
                " parameter: '%s' is not a valid string format: '%s'",
                param_date, date_format
            )
    else:
        try:
            # Date is supposed to be received as a struct time ...
            # ... and assume it is local time!
            # ----------------------------------------------------
            timestamp = timegm(param_date.timetuple())
            return timestamp
        except TypeError:  # pragma: no cover, simple protection
            print(
                " parameter: %s is not a valid time tuple", param_date
            )
    return None


def get_iso_date(param_date, fmt='%Y-%m-%d %H:%M:%S'):
    """
    Format the provided `_date` as a string according to the specified format.

    If no date format is specified, it uses the one defined in the ElementState object that is
    the date format defined in the application configuration.

    If duration is True, the date is displayed as a pretty date: 1 day 12 minutes ago ...

    :type param_date: float
    """

    tz_from = tz.gettz('UTC')
    tz_to = tz.gettz('Europe/Paris')

    # Make timestamp to datetime
    _date = datetime.utcfromtimestamp(param_date)
    # Tell the datetime object that it's in UTC time zone since
    # datetime objects are 'naive' by default
    _date = _date.replace(tzinfo=tz_from)
    # Convert to required time zone
    _date = _date.astimezone(tz_to)

    if fmt:
        return _date.strftime(fmt)

    return _date.isoformat(' ')


class BackendExport(object):
    """
    Class to manage an item
    An Item is the base of many objects of Alignak. So it define common properties,
    common functions.
    """

    # Store list of errors found
    errors_found = []

    def __init__(self):
        self.result = False

        # Get command line parameters
        args = None
        try:
            args = docopt(__doc__, version=__version__)
        except DocoptExit:
            print(
                "Command line parsing error.\n"
                "alignak_backend_counters -h will display the command line parameters syntax."
            )
            exit(64)

        # Verbose
        self.verbose = False
        if '--verbose' in args and args['--verbose']:
            logger.setLevel('DEBUG')
            self.verbose = True

        # Quiet mode
        self.quiet = False
        if args['--quiet']:
            logger.setLevel('NOTSET')
            self.quiet = True

        logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        logger.info("alignak-backend-counters, version: %s", __version__)
        logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

        # Backend and URL
        self.backend = None
        self.backend_url = args['--backend']
        logger.debug("Backend URL: %s", self.backend_url)

        # Backend authentication
        self.username = args['--username']
        self.password = args['--password']
        logger.debug("Backend login with credentials: %s/%s", self.username, self.password)

        # Concerned hosts
        self.targeted_host = args['--hostnames'].split(',')
        logger.debug("Targeted hosts: %s", self.targeted_host)

        # Concerned services
        self.targeted_service = args['--services'].split(',')
        logger.debug("Targeted services: %s", self.targeted_service)

        # Concerned metrics
        self.metrics = []
        self.targeted_metrics = args['--metrics'].split(',')
        logger.debug("Targeted counters: %s", self.targeted_metrics)

        # Fetched counters
        self.counters = {}

    def authenticate(self):
        """
        Login on backend with username and password

        :return: None
        """
        logger.info("Authenticating to %s...", self.backend_url)
        try:
            # Backend authentication with token generation
            # headers = {'Content-Type': 'application/json'}
            # payload = {'username': self.username, 'password': self.password, 'action': 'generate'}
            self.backend = Backend(self.backend_url)
            self.backend.login(self.username, self.password)
        except BackendException as e:
            print("Alignak backend error: %s" % e.message)
            return False

        if self.backend.token is None:
            print("Access is denied!")
            return False

        logger.info("Authenticated.")
        return True

    def get_counters(self):
        """
        Search required counters in the backend performance data

        :return: True / False if some counters were found
        """
        # Log check results
        params = {
            'sort': '-last_check',
            'projection': json.dumps(
                {
                    "host_name": 1, "service_name": 1,
                    "last_check": 1, "state": 1, "state_type": 1, "perf_data": 1
                }
            )
        }
        if len(self.targeted_service) > 1:
            if len(self.targeted_host) > 1:
                params['where'] = {"$and": [
                    {"host_name": {"$in": self.targeted_host}},
                    {"service_name": {"$in": self.targeted_service}}
                ]}
            else:
                params['where'] = {"$and": [
                    {"host_name": {"$regex": ".*" + self.targeted_host[0] + ".*"}},
                    {"service_name": {"$in": self.targeted_service}}
                ]}
        else:
            if len(self.targeted_host) > 1:
                params['where'] = {"$and": [
                    {"host_name": {"$in": self.targeted_host}},
                    {"service_name": {"$regex": ".*" + self.targeted_service[0] + ".*"}}
                ]}
            else:
                params['where'] = {"$and": [
                    {"host_name": {"$regex": ".*%s.*" % self.targeted_host[0]}},
                    {"service_name": {"$regex": ".*" + self.targeted_service[0] + ".*"}}
                ]}
        params['where'] = json.dumps(params['where'])

        logger.debug("Search parameters: %s", params)

        result = self.backend.get('logcheckresult', params=params)
        if '_items' not in result or not result['_items']:
            logger.error("No check result log matching the search query: %s", params)
            self.errors_found.append("No log matching the search query: %s" % params)
            return []

        logger.info("Found %d matching items", len(result['_items']))
        for item in result['_items']:
            logger.debug("Parsing: %s", item)
            date = get_iso_date(float(item['last_check']))

            try:
                p = PerfDatas(item['perf_data'])
                for metric in sorted(p):
                    # self.log("metrics, service perfdata metric: %s" % m.__dict__)
                    if self.targeted_metrics == ['all'] or metric.name in self.targeted_metrics:
                        logger.debug("found: %s - %s = %s", date, metric.name, metric.value)
                        if item['host_name'] not in self.counters:
                            self.counters[item['host_name']] = {}
                        if item['service_name'] not in self.counters[item['host_name']]:
                            self.counters[item['host_name']][item['service_name']] = {}
                        if metric.name not in self.counters[item['host_name']][
                                item['service_name']]:
                            self.counters[item['host_name']][item['service_name']][metric.name] = []
                        self.counters[item['host_name']][item['service_name']][metric.name].append(
                            (item['last_check'], metric.value))
            except Exception as exp:
                logger.exception("exception: %s", str(exp))

        if not self.counters.keys():
            logger.error("No performance data metrics matching the searched counters")
            self.errors_found.append("No performance data metrics matching the searched counters")
            return False

        logger.info("Got %d counters", len(self.counters.keys()))
        return True


def main():
    """
    Main function
    """
    exportation = BackendExport()

    # Authenticate on Backend
    if not exportation.authenticate():
        exit(2)

    # Export from the backend
    if not exportation.get_counters():
        print("################################################################################")
        print("alignak_backend_counters, errors encountered during extraction :")

        for error in exportation.errors_found:
            print("- %s" % error)
        print("################################################################################")
        exit(4)

    logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    logger.info("alignak_backend_counters, found elements: ")
    logger.info(json.dumps(exportation.counters))
    print(json.dumps(exportation.counters))

if __name__ == "__main__":  # pragma: no cover
    main()
