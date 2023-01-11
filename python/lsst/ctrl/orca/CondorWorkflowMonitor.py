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
import threading
import time

from lsst.ctrl.orca.CondorJobs import CondorJobs
from lsst.ctrl.orca.multithreading import SharedData
from lsst.ctrl.orca.WorkflowMonitor import WorkflowMonitor

log = logging.getLogger(__name__)


# HTCondor workflow monitor
class CondorWorkflowMonitor(WorkflowMonitor):
    """Monitors the progress of the running workflow.

    Parameters
    ----------
    condorDagId : `str`
        job id of submitted HTCondor dag
    monitorConfig : Config
        configuration file for monitor information
    """

    def __init__(self, condorDagId, monitorConfig):

        # _locked: a container for data to be shared across threads that
        # have access to this object.
        self._locked = SharedData.SharedData(False, {"running": False, "done": False})

        log.debug("CondorWorkflowMonitor:__init__")
        self._statusListeners = []

        # make a copy of this liste, since we'll be removing things.

        self.condorDagId = condorDagId

        self.monitorConfig = monitorConfig

        self._wfMonitorThread = None

        with self._locked:
            self._wfMonitorThread = CondorWorkflowMonitor._WorkflowMonitorThread(
                self, self.condorDagId, self.monitorConfig
            )

    class _WorkflowMonitorThread(threading.Thread):
        """Workflow thread that watches for shutdown

        Parameters
        ----------
        parent : `Thread`
            direct parent thread of this thread
        condorDagId : `str`
            job id of submitted HTCondor dag
        monitorConfig : `Config`
            configuration file for monitor information
        """

        def __init__(self, parent, condorDagId, monitorConfig):
            threading.Thread.__init__(self)
            self.setDaemon(True)
            self._parent = parent

            # the dag id assigned to this workflow
            self.condorDagId = condorDagId

            # monitor configuration
            self.monitorConfig = monitorConfig

        def run(self):
            """Continously monitor life of workflow, shutting down when
            complete."""
            cj = CondorJobs()
            log.debug("CondorWorkflowMonitor Thread started")
            statusCheckInterval = int(self.monitorConfig.statusCheckInterval)
            sleepInterval = statusCheckInterval
            # we don't decide when we finish, someone else does.
            while True:
                time.sleep(sleepInterval)

                # if the dag is no longer running, return
                if not cj.isJobAlive(self.condorDagId):
                    print("work complete.")
                    with self._parent._locked:
                        self._parent._locked.running = False

    def startMonitorThread(self):
        """Begin one monitor thread"""
        with self._locked:
            self._wfMonitorThread.start()
            self._locked.running = True

    def stopWorkflow(self, urgency):
        """Stop the workflow"""
        log.debug("CondorWorkflowMonitor:stopWorkflow")

        # do a condor_rm on the cluster id for the dag we submitted.
        print("shutdown request received: stopping workflow")
        cj = CondorJobs()
        cj.killCondorId(self.condorDagId)
