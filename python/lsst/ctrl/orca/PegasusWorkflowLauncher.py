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
import os

from lsst.ctrl.orca.CondorWorkflowMonitor import CondorWorkflowMonitor
from lsst.ctrl.orca.PegasusJobs import PegasusJobs
from lsst.ctrl.orca.WorkflowLauncher import WorkflowLauncher

log = logging.getLogger(__name__)


class PegasusWorkflowLauncher(WorkflowLauncher):
    """Launcher for Pegasus workflows

    Parameters
    ----------
    prodConfig : Config
        production Config
    wfConfig : Config
        workflow Config
    runid : str
        run id
    localStagingDir : str
        local directory where staging occurs
    dagFile : str
        DAGman file
    monitorConfig : Config
        monitor Config
    """

    def __init__(
        self,
        prodConfig,
        wfConfig,
        runid,
        localStagingDir,
        sitesXMLFile,
        transformFile,
        daxFile,
        monitorConfig,
    ):
        log.debug("PegasusWorkflowLauncher:__init__")

        self.prodConfig = prodConfig
        self.wfConfig = wfConfig
        self.runid = runid
        self.localStagingDir = localStagingDir
        self.sitesXMLFile = sitesXMLFile
        self.transformFile = transformFile
        self.daxFile = daxFile
        self.monitorConfig = monitorConfig

    def cleanUp(self):
        """Perform cleanup after workflow has ended."""
        log.debug("PegasusWorkflowLauncher:cleanUp")

    def launch(self, statusListener):
        """Launch this workflow

        Parameters
        ----------
        statusListener : StatusListener
            status listener object
        """
        log.debug("PegasusWorkflowLauncher:launch")

        # start the monitor

        # Launch process
        startDir = os.getcwd()
        os.chdir(self.localStagingDir)

        pj = PegasusJobs()
        condorDagId, statusInfo, removeInfo = pj.pegasusSubmitDax(
            self.sitesXMLFile, self.transformFile, self.daxFile
        )
        if statusInfo is not None:
            print("Pegasus workspace: %s" % statusInfo[0])

        os.chdir(startDir)

        # workflow monitor for HTCondor jobs
        self.workflowMonitor = CondorWorkflowMonitor(condorDagId, self.monitorConfig)

        if statusListener is not None:
            self.workflowMonitor.addStatusListener(statusListener)
        self.workflowMonitor.startMonitorThread()

        return self.workflowMonitor
