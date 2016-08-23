#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
    Alignak counters

    This module contains utility tools to search and extract counters from
    an Alignak REST Backend.
"""
# Application version and manifest
VERSION = (0, 0, 1, 'a')

__application__ = u"Alignak backend counterzs"
__short_version__ = '.'.join((str(each) for each in VERSION[:2]))
__version__ = '.'.join((str(each) for each in VERSION[:4]))
__author__ = u"Frederic Mohier"
__copyright__ = u"(c) 2016, %s" % __author__
__license__ = u"GNU Affero General Public License, version 3"
__description__ = u"Alignak backend counters"
__releasenotes__ = u"""Alignak Backend counters"""
__doc_url__ = "https://github.com/Alignak-monitoring-contrib/alignak-counters"
# Application manifest
manifest = {
    'name': __application__,
    'version': __version__,
    'author': __author__,
    'description': __description__,
    'copyright': __copyright__,
    'license': __license__,
    'release': __releasenotes__,
    'doc': __doc_url__
}
