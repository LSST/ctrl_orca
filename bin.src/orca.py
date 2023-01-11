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

import logging
import optparse

import lsst.ctrl.orca as orca

from lsst.ctrl.orca.ProductionRunManager import ProductionRunManager

usage = """usage: %prog [-gndvqsc] [-r dir] [-e script] [-V int][-L lev] pipelineConfigFile runId"""

parser = optparse.OptionParser(usage)
# TODO: handle "--dryrun"
parser.add_option(
    "-n",
    "--dryrun",
    action="store_true",
    dest="dryrun",
    default=False,
    help="print messages, but don't execute anything",
)

parser.add_option(
    "-g",
    "--skipglidein",
    action="store_true",
    dest="skipglidein",
    default=False,
    help="if this run uses condor glidein, skip doing it",
)

parser.add_option(
    "-c",
    "--configcheck",
    action="store_true",
    dest="skipconfigcheck",
    default=False,
    help="skip configuration check",
)

parser.add_option(
    "-V",
    "--verbosity",
    type="int",
    action="store",
    dest="verbosity",
    default=0,
    metavar="int",
    help="orca verbosity level (0=normal, 1=debug, -1=quiet, -3=silent)",
)
parser.add_option(
    "-e",
    "--envscript",
    action="store",
    dest="envscript",
    default=None,
    metavar="script",
    help="an environment-setting script to source on pipeline platform",
)
parser.add_option(
    "-d",
    "--debug",
    action="store_const",
    const=1,
    dest="verbosity",
    help="print maximum amount of messages",
)
parser.add_option(
    "-v",
    "--verbose",
    action="store_const",
    const=1,
    dest="verbosity",
    help="same as -d",
)
parser.add_option(
    "-q",
    "--quiet",
    action="store_const",
    const=-1,
    dest="verbosity",
    help="print only warning & error messages",
)
parser.add_option(
    "-s",
    "--silent",
    action="store_const",
    const=-3,
    dest="verbosity",
    help="print nothing (if possible)",
)
parser.add_option(
    "-P",
    "--pipeverb",
    type="int",
    action="store",
    dest="pipeverb",
    default=0,
    metavar="int",
    help="pipeline verbosity level (0=normal, 1=debug, -1=quiet, -3=silent)",
)

parser.opts = {}
parser.args = []

# parse and check command line arguments
(parser.opts, parser.args) = parser.parse_args()
if len(parser.args) < 2:
    print(usage)
    raise RuntimeError("Missing args: pipelineConfigFile runId")

pipelineConfigFile = parser.args[0]
runId = parser.args[1]

orca.skipglidein = parser.opts.skipglidein
orca.dryrun = parser.opts.dryrun
orca.envscript = parser.opts.envscript

# This is handled via lsst.ctrl.orca (i.e. lsst/ctrl/orca/__init__.py):
#
# orca.logger = Log(Log.getDefaultLog(), "orca")

configPath = None
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("lsst.orca")

orca.verbosity = parser.opts.verbosity

# set the dryrun singleton to the value set on the command line.
# we reference this in other classes
orca.dryrun = parser.opts.dryrun


log.debug("pipelineConfigFile = " + pipelineConfigFile)
log.debug("runId = " + runId)

# create the ProductionRunManager, configure it, and launch it
productionRunManager = ProductionRunManager(runId, pipelineConfigFile)


productionRunManager.runProduction(
    skipConfigCheck=parser.opts.skipconfigcheck, workflowVerbosity=parser.opts.pipeverb
)
productionRunManager.joinShutdownThread()
