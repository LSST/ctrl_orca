#!/usr/bin/env python

#
# LSST Data Management System
# Copyright 2008, 2009, 2010 LSST Corporation.
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

import optparse
import os
import os.path
import sys
import time

# filewaiter.py - wait for creation of files
if __name__ == "__main__":

    usage = """usage: %prog [-f|-l] filenames.txt"""

    parser = optparse.OptionParser(usage)
    # TODO: handle "--dryrun"
    parser.add_option(
        "-f",
        "--first",
        action="store_true",
        default=False,
        dest="bFirst",
        help="wait for first file in list",
    )
    parser.add_option(
        "-l",
        "--list",
        action="store_true",
        default=False,
        dest="bList",
        help="wait for all the files in the list",
    )

    parser.opts = {}
    parser.args = []

    # parse and check command line arguments
    (parser.opts, parser.args) = parser.parse_args()
    if len(parser.args) < 1:
        print(usage)
        raise RuntimeError("Missing args: pipelinePolicyFile runId")

    filename = parser.args[0]

    bFirst = parser.opts.bFirst
    bList = parser.opts.bList

    f = open(filename, "r")

    lines = f.readlines()

    fileList = []
    for line in lines:
        list.append(line.split("\n")[0])

    if bFirst:
        item = fileList[0]
        while not os.path.exists(item):
            time.sleep(1)
        sys.exit(0)

    for item in fileList:
        while not os.path.exists(item):
            time.sleep(1)
    sys.exit(0)
