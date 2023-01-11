#
# LSST Data Management System
# Copyright 2017 LSST Corporation.
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
import re
import subprocess

from lsst.ctrl.orca.CondorJobs import CondorJobs

log = logging.getLogger(__name__)


class PegasusJobs(CondorJobs):
    """Handles interaction with Pegasus
    This class is highly dependent on the output of the pegasus commands
    """

    def __init__(self):
        log.debug("PegasusJobs:__init__")
        return

    def pegasusSubmitDax(self, sitesFile, transformationFile, daxFile):
        """Submit a pegagus dax and return its cluster number.

        Parameters
        ----------
        daxFile : `str`
            name of pegasus DAX file

        Notes
        -----
        This is the type of output we're dealing with....

        ---expected output begin---  # noqa
        2017.02.07 14:06:53.482 CST:
        2017.02.07 14:06:53.488 CST:   -----------------------------------------------------------------------
        2017.02.07 14:06:53.493 CST:   File for submitting this DAG to HTCondor           : CiHscDax-0.dag.condor.sub
        2017.02.07 14:06:53.498 CST:   Log of DAGMan debugging messages                 : CiHscDax-0.dag.dagman.out
        2017.02.07 14:06:53.504 CST:   Log of HTCondor library output                     : CiHscDax-0.dag.lib.out
        2017.02.07 14:06:53.509 CST:   Log of HTCondor library error messages             : CiHscDax-0.dag.lib.err
        2017.02.07 14:06:53.514 CST:   Log of the life of condor_dagman itself          : CiHscDax-0.dag.dagman.log
        2017.02.07 14:06:53.519 CST:

        2017.02.07 14:06:53.525 CST:   -no_submit given, not submitting DAG to HTCondor.  You can do this with:
        2017.02.07 14:06:53.535 CST:   -----------------------------------------------------------------------
        2017.02.07 14:06:55.207 CST:   Your database is compatible with Pegasus version: 4.7.0
        2017.02.07 14:06:55.326 CST:   Submitting to condor CiHscDax-0.dag.condor.sub
        2017.02.07 14:06:55.382 CST:   Submitting job(s).
        2017.02.07 14:06:55.387 CST:   1 job(s) submitted to cluster 164870.
        2017.02.07 14:06:55.392 CST:

        2017.02.07 14:06:55.398 CST:   Your workflow has been started and is running in the base directory:
        2017.02.07 14:06:55.403 CST:
        2017.02.07 14:06:55.408 CST:     /scratch/srp/condor_scratch/srp_2017_0207_110530/scripts/submit/srp/pegasus/CiHscDax/run0008  # noqa: E501
        2017.02.07 14:06:55.414 CST:
        2017.02.07 14:06:55.419 CST:   *** To monitor the workflow you can run ***
        2017.02.07 14:06:55.424 CST:
        2017.02.07 14:06:55.429 CST:     pegasus-status -l /scratch/srp/condor_scratch/srp_2017_0207_110530/scripts/submit/srp/pegasus/CiHscDax/run0008
        2017.02.07 14:06:55.435 CST:
        2017.02.07 14:06:55.440 CST:   *** To remove your workflow run ***
        2017.02.07 14:06:55.445 CST:
        2017.02.07 14:06:55.451 CST:     pegasus-remove /scratch/srp/condor_scratch/srp_2017_0207_110530/scripts/submit/srp/pegasus/CiHscDax/run0008
        2017.02.07 14:06:55.456 CST:
        2017.02.07 14:06:55.637 CST:   Time taken to execute is 3.555 seconds
        ---expected output end---
        """

        log.debug("PegasusJobs: pegasusSubmitDax %s", daxFile)

        # expressions to match
        clusterexp = re.compile(r".*1 job\(s\) submitted to cluster (\d+).")
        statusexp = re.compile(r".*pegasus-status -l ((\W|\w)+)")
        removeexp = re.compile(r".*pegasus-remove ((\W|\w)+)")

        cmd = (
            "pegasus-plan -Dpegasus.transfer.links=true -Dpegasus.catalog.site.file=%s"
            " -Dpegasus.catalog.transformation.file=%s -Dpegasus.data.configuration=sharedfs"
            " --sites lsstvc --output-dir output --dir submit --dax %s --submit"
            % (sitesFile, transformationFile, daxFile)
        )
        print(cmd)
        log.debug(cmd)
        process = subprocess.Popen(cmd.split(), shell=False, stdout=subprocess.PIPE)
        output = []
        line = process.stdout.readline()
        line = line.decode()
        i = 0
        while line != "":
            line = line.strip()
            output.append(line)
            line = process.stdout.readline()
            line = line.decode()
            i += 1

        condorClusterId = -1
        statusInfo = None
        removeInfo = None
        for line in output:
            cluster = clusterexp.findall(line)
            if len(cluster) != 0:
                condorClusterId = cluster[0]
                continue
            status = statusexp.findall(line)
            if len(status) != 0:
                statusInfo = status[0]
                continue
            remove = removeexp.findall(line)
            if len(remove) != 0:
                removeInfo = remove[0]

        # read the rest (if any) and terminate
        stdoutdata, stderrdata = process.communicate()
        return condorClusterId, statusInfo, removeInfo
