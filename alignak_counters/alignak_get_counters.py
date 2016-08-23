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
alignak_get_counters command line interface::

    Usage:
        {command} [-h] [-v]
                  [-b=url] [-u=username] [-p=password]
                  [-H=hostnames] [-S=services] [-M=metrics]

    Options:
        -h, --help                  Show this screen.
        -V, --version               Show application version.
        -b, --backend url           Specify backend URL [default: http://127.0.0.1:5000]
        -u, --username username     Backend login username [default: admin]
        -p, --password password     Backend login password [default: admin]
        -v, --verbose               Run in verbose mode (more info to display)
        -H, --hostnames hosts       Extract data for a list of hosts [default: all]
        -S, --services services     Extract data for a list of services [default: all]
        -M, --metrics metrics       Extract data for a list of counters [default: all]

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

import time
from calendar import timegm
from datetime import datetime
from dateutil import tz

from docopt import docopt
from docopt import DocoptExit

from alignak_backend_client.client import Backend, BackendException

from alignak_counters import __version__
from alignak_counters.perfdata import PerfDatas


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
                "alignak_get_counters -h will display the command line parameters syntax."
            )
            exit(64)

        # Verbose
        self.verbose = False
        if '--verbose' in args and args['--verbose']:
            self.verbose = True
        print("Verbose mode: %s" % self.verbose)

        # Backend and URL
        self.backend = None
        self.backend_url = args['--backend']
        self.log("Backend URL: %s" % self.backend_url)
        # print("Backend URL: %s" % self.backend_url)

        # Backend authentication
        self.username = args['--username']
        self.password = args['--password']
        self.log("Backend login with credentials: %s/%s" % (self.username, self.password))

        # Concerned hosts
        self.hosts = []
        self.targeted_host = args['--hostnames'].split(',')
        self.log("Targeted hosts: %s" % self.targeted_host)

        # Concerned services
        self.services = []
        self.targeted_service = args['--services'].split(',')
        self.log("Targeted services: %s" % self.targeted_service)

        # Concerned metrics
        self.metrics = []
        self.targeted_metrics = args['--metrics'].split(',')
        self.log("Targeted counters: %s" % self.targeted_metrics)

        # Fetched counters
        self.counters = {}

    def authenticate(self):
        """
        Login on backend with username and password

        :return: None
        """
        print("Backend authentication ...")
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

        print("Access granted")
        return True

    def log(self, message):
        """
        Display message if in verbose mode

        :param message: message to display
        :type message: str
        :return: None
        """
        if self.verbose:
            print(message)

    def get_hosts(self):
        """
        Search matching hosts in the backend
        :return:
        """
        params = {
            'sort': 'name',
            'projection': json.dumps({"_id": 1, "name": 1})
        }
        if self.targeted_host != ['all']:
            params.update({'where': json.dumps({"name": {"$in": self.targeted_host}})})
        result = self.backend.get_all('host', params)
        if '_items' not in result:
            self.errors_found.append("No matching hosts found")
            return False

        self.log("Found %d matching hosts" % len(result['_items']))
        hosts = []
        for item in result['_items']:
            self.log(" - host: %s" % item['name'])
            hosts.append((item['_id'], item['name']))

        return hosts

    def get_services(self, host_id):
        """
        Search matching services in the backend

        :return:
        """
        params = {
            'sort': 'name',
            'where': json.dumps({"host": host_id}),
            'embedded': json.dumps({'host': 1}),
            'projection': json.dumps({"_id": 1, "host": 1, "name": 1})
        }
        if self.targeted_service != ['all']:
            params.update({'where': json.dumps(
                {"$and": [
                    {"host": {"$in": self.hosts}},
                    {"name": {"$in": self.targeted_service}}
                ]}
            )})
        result = self.backend.get_all('service', params)
        if '_items' not in result or len(result['_items']) == 0:
            self.errors_found.append("No matching services found")
            return False

        self.log("Found %d matching services" % len(result['_items']))
        services = []
        for item in result['_items']:
            self.log(" - service: %s/%s" % (item['host']['name'], item['name']))
            services.append((item['_id'], item['name']))

        return services

    def get_counters(self):
        """
        Search required counters in the backend performance data

        :return: True / False if some counters were found
        """
        for host_id, host_name in self.get_hosts():
            for service_id, service_name in self.get_services(host_id):
                # Log check results
                params = {
                    'sort': '-last_check',
                    'where': json.dumps({"service": service_id}),
                    'embedded': json.dumps({'host': 1, 'service': 1}),
                    'projection': json.dumps(
                        {
                            "last_check": 1, "state": 1, "state_type": 1, "perf_data": 1
                        }
                    )
                }
                result = self.backend.get('logcheckresult', params=params)
                if '_items' not in result or len(result['_items']) == 0:
                    self.errors_found.append("No log matching the search query")
                    return False

                self.log("Found %d matching items for %s/%s" % (len(result['_items']), host_name, service_name))
                for item in result['_items']:
                    date = get_iso_date(float(item['last_check']))

                    try:
                        p = PerfDatas(item['perf_data'])
                        for metric in sorted(p):
                            # self.log("metrics, service perfdata metric: %s" % m.__dict__)
                            if self.targeted_metrics == ['all'] or metric.name in self.targeted_metrics:
                                self.log("found: %s - %s = %s" % (date, metric.name, metric.value))
                                if host_name not in self.counters:
                                    self.counters[host_name] = {}
                                if service_name not in self.counters[host_name]:
                                    self.counters[host_name][service_name] = {}
                                if metric.name not in self.counters[host_name][service_name]:
                                    self.counters[host_name][service_name][metric.name] = []
                                    self.counters[host_name][service_name][metric.name].append((item['last_check'], metric.value))
                    except Exception as exp:
                        self.log("exception: %s" % str(exp))
                        self.log("traceback: %s" % traceback.format_exc())

        if len(self.counters.keys()) == 0:
            self.errors_found.append("No performance data metrics matching the searched counters")
            return False

        self.log("Got %d counters" % len(self.counters.keys()))
        return True


def main():
    """
    Main function
    """
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print("alignak_get_counters, version: %s" % __version__)
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    exportation = BackendExport()

    # Authenticate on Backend
    if not exportation.authenticate():
        exit(2)

    # Export from the backend
    if not exportation.get_counters():
        print("################################################################################")
        print("alignak_get_counters, errors encountered during extraction :")

        for error in exportation.errors_found:
            print("- %s" % error)
        print("################################################################################")
        exit(4)

    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print("alignak_get_counters, found elements: ")
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print(json.dumps(exportation.counters))

if __name__ == "__main__":  # pragma: no cover
    main()
