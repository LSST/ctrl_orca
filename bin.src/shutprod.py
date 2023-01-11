#!/usr/bin/env python

#
# LSST Data Management System
# Copyright 2008-2017 LSST Corporation.
#
# This product includes software developed by the
# LSST Project (http://www.lsst.org/).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the LSST License Statement and
# the GNU General Public License along with this program.  If not,
# see <http://www.lsstcorp.org/LegalNotices/>.
#

import argparse
import json
import sys

import requests

# usage:  python bin/shutprod.py host port urgency_level runid
if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog=sys.argv[0])

    parser.add_argument(
        "-H",
        "--host",
        action="store",
        type=str,
        dest="host",
        default=None,
        required=True,
    )
    parser.add_argument(
        "-P",
        "--port",
        action="store",
        type=str,
        dest="port",
        default=None,
        required=True,
    )
    parser.add_argument(
        "-L",
        "--level",
        action="store",
        type=int,
        dest="level",
        default=100,
        required=True,
    )
    parser.add_argument(
        "-R",
        "--runid",
        action="store",
        type=str,
        dest="runid",
        default=None,
        required=True,
    )

    args = parser.parse_args()

    url = "http://%s:%s/api/v1/production" % (args.host, args.port)

    data = {"runid": args.runid, "level": args.level}
    data_json = json.dumps(data)

    r = requests.delete(url, data=data_json)
