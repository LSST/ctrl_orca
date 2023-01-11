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

import argparse
import shlex
import sys


def _line_to_args(self, line):
    for arg in shlex.split(line, comments=True, posix=True):
        if not arg.strip():
            continue
        yield arg


def makeArgumentParser(description, inRootsRequired=True, addRegistryOption=True):

    parser = argparse.ArgumentParser(
        description=description,
        fromfile_prefix_chars="@",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=" \n" "ly.",
    )
    parser.convert_arg_line_to_args = _line_to_args

    parser.add_argument(
        "-s", "--source", dest="source", help="Source site for file transfer."
    )

    parser.add_argument("-w", "--workerdir", dest="workerdir", help="workers directory")

    parser.add_argument("-t", "--template", dest="template", help="template file")

    parser.add_argument("-p", "--prescript", dest="prescript", help="pre shell script")

    parser.add_argument("-r", "--runid", dest="runid", help="runid of this job")

    parser.add_argument(
        "-i", "--idsPerJob", dest="idsPerJob", help="number of ids to run per job"
    )

    return parser


def writeDagFile(
    pipeline, templateFile, infile, workerdir, prescriptFile, runid, idsPerJob
):
    """
    Write Condor Dag Submission files.
    """

    print("Writing DAG file ")

    outname = pipeline + ".diamond.dag"

    print(outname)

    outObj = open(outname, "w")

    outObj.write("JOB A " + workerdir + "/" + pipeline + ".pre\n")
    outObj.write("JOB B " + workerdir + "/" + pipeline + ".post\n")
    outObj.write(" \n")

    print("prescriptFile = ", prescriptFile)
    if prescriptFile is not None:
        outObj.write("SCRIPT PRE A " + prescriptFile + "\n")

    print("First Input File loop ")

    # Loop over input entries
    fileObj = open(infile, "r")
    count = 0
    for aline in fileObj:
        count += 1
        outObj.write("JOB A" + str(count) + " " + workerdir + "/" + templateFile + "\n")

    outObj.write(" \n")

    print("Second Input File loop ")

    # Loop over input entries
    fileObj = open(infile, "r")
    count = 0
    for aline in fileObj:
        count += 1
        myData = aline.rstrip()

        # Searching for a space detects
        # extended input like :  visit=887136081 raft=2,2 sensor=0,1
        # No space is something simple like a skytile id
        if " " in myData:
            # Change space to :
            myList = myData.split(" ")
            new1Data = "%s:%s:%s" % tuple(myList)
            # Change = to -
            myList2 = new1Data.split("=")
            new2Data = "%s-%s-%s-%s" % tuple(myList2)
            # Change , to _
            myList3 = new2Data.split(",")
            new3Data = "%s_%s_%s" % tuple(myList3)

            newData = new3Data
            visit = myList[0].split("=")[1]
        else:
            newData = myData
            visit = myData

        #  VARS A1 var1="visit=887136081 raft=2,2 sensor=0,1"
        #  VARS A1 var2="visit-887136081:raft-2_2:sensor-0_1"
        outObj.write("VARS A" + str(count) + ' var1="' + myData + '" \n')
        outObj.write("VARS A" + str(count) + ' var2="' + newData + '" \n')
        outObj.write("VARS A" + str(count) + ' visit="' + visit + '" \n')
        outObj.write("VARS A" + str(count) + ' runid="' + runid + '" \n')
        outObj.write("VARS A" + str(count) + ' workerid="' + str(count) + '" \n')

    print("Third Input File loop ")

    fileObj = open(infile, "r")
    count = 0
    for aline in fileObj:
        count += 1
        # PARENT A CHILD A1
        # PARENT A1 CHILD B
        outObj.write("PARENT A CHILD A" + str(count) + " \n")
        outObj.write("PARENT A" + str(count) + " CHILD B \n")

    outObj.close()


def main():
    print("Starting generateDag.py")
    parser = makeArgumentParser(
        description="generateDag.py write a Condor DAG for job submission"
        "by reading input list and writing the attribute as an argument."
    )
    print("Created parser")
    ns = parser.parse_args()
    print("Parsed Arguments")
    print(ns)

    # SA
    # templateFile = "SourceAssoc-template.condor"
    # pipeline = "SourceAssoc"
    # infile   = "sky-tiles"

    # Pipeqa
    # templateFile = "pipeqa-template.template"
    # pipeline = "pipeqa"
    # infile   = "visits-449"

    #   processCcdLsstSim
    pipeline = "S2012Pipe"

    writeDagFile(
        pipeline,
        ns.template,
        ns.source,
        ns.workerdir,
        ns.prescript,
        ns.runid,
        ns.idsPerJob,
    )

    sys.exit(0)


if __name__ == "__main__":
    main()
