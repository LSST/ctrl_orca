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

import os
import os.path
import socket
import threading
import time
from http.server import HTTPServer
from socketserver import ThreadingMixIn

import lsst.log as log
from lsst.ctrl.orca.config.ProductionConfig import ProductionConfig
from lsst.ctrl.orca.NamedClassFactory import NamedClassFactory
from lsst.ctrl.orca.StatusListener import StatusListener

from .EnvString import EnvString
from .exceptions import ConfigurationError, MultiIssueConfigurationError
from .multithreading import SharedData
from .ProductionRunConfigurator import ProductionRunConfigurator
from .ServiceHandler import ServiceHandler


def MakeServiceHandlerClass(productionRunManager, runid):
    class CustomHandler(ServiceHandler, object):
        def __init__(self, *args, **kwargs):
            self.setParent(productionRunManager, runid)
            super(CustomHandler, self).__init__(*args, **kwargs)

    return CustomHandler


class ProductionRunManager:
    """In charge of launching, monitoring, managing, and stopping a production run

    Parameters
    ----------
    runid : `str`
        name of the run
    configFileName : `Config`
         production run config file
    repository : `str`, optional
         the config repository to assume; this will override the value in the config file
    """

    def __init__(self, runid, configFileName, repository=None):

        # _locked: a container for data to be shared across threads that
        # have access to this object.
        self._locked = SharedData.SharedData(False, {"running": False, "done": False})

        # the run id for this production
        self.runid = runid

        # once the workflows that make up this production is created we will
        # cache them here
        self._workflowManagers = None

        # a list of workflow Monitors
        self._workflowMonitors = []

        # the cached ProductionRunConfigurator instance
        self._productionRunConfigurator = None

        # the full path the configuration
        self.fullConfigFilePath = ""
        if os.path.isabs(configFileName):
            self.fullConfigFilePath = configFileName
        else:
            self.fullConfigFilePath = os.path.join(
                os.path.realpath("."), configFileName
            )

        # create Production configuration
        self.config = ProductionConfig()
        # load the production config object
        self.config.load(self.fullConfigFilePath)

        # the repository location
        self.repository = repository

        # determine repository location
        if not self.repository:
            self.repository = self.config.production.repositoryDirectory
        if not self.repository:
            self.repository = "."
        else:
            self.repository = EnvString.resolve(self.repository)

        # shutdown thread
        self._sdthread = None

    def getRunId(self):
        """Accessor to return the run id for this production run

        Returns
        -------
        The runid of this production run
        """
        return self.runid

    def configure(self, workflowVerbosity=None):
        """Configure this production run

        Parameters
        ----------
        workflowVerbosity : `int`
            The verbosity to pass down to configured workflows and the pipelines they run.

        Raises
        ------
        `ConfigurationError`
            If any error arises during configuration or while checking the configuration.

        Notes
        -----
        If the production was already configured, this call will be ignored and will not be reconfigured.
        """

        if self._productionRunConfigurator:
            log.info("production has already been configured.")
            return

        # lock this branch of code
        try:
            self._locked.acquire()

            # TODO - SRP
            self._productionRunConfigurator = self.createConfigurator(
                self.runid, self.fullConfigFilePath
            )
            workflowManagers = self._productionRunConfigurator.configure(
                workflowVerbosity
            )

            self._workflowManagers = {"__order": []}
            for wfm in workflowManagers:
                self._workflowManagers["__order"].append(wfm)
                self._workflowManagers[wfm.getName()] = wfm

        finally:
            self._locked.release()

    def runProduction(self, skipConfigCheck=False, workflowVerbosity=None):
        """Run the entire production

        Parameters
        ----------
        skipConfigCheck : `bool`
            Skips configuration checks, if True
        workflowVerbosity: `int`, optional
            overrides the config-specified logger verbosity

        Raises
        ------
        `ConfigurationError`
            if any error arises during configuration or while checking the configuration.

        Notes
        -----
        The skipConfigCheck parameter will be overridden by configCheckCare config parameter, if it exists.
        The workflowVerbosity parameter will only be used if the run has not already been configured via
        configure().
        """
        log.debug("Running production: %s", self.runid)

        if not self.isRunnable():
            if self.isRunning():
                log.info("Production Run %s is already running" % self.runid)
            if self.isDone():
                log.info(
                    "Production Run %s has already run; start with new runid"
                    % self.runid
                )
            return False

        # set configuration check care level.
        # Note: this is not a sanctioned pattern; should be replaced with use
        # of default config.
        checkCare = 1

        if self.config.production.configCheckCare != 0:
            checkCare = self.config.production.configCheckCare
        if checkCare < 0:
            skipConfigCheck = True

        # lock this branch of code
        try:
            self._locked.acquire()
            self._locked.running = True

            # configure the production run (if it hasn't been already)
            if not self._productionRunConfigurator:
                self.configure(workflowVerbosity)

            # make sure the configuration was successful.
            if not self._workflowManagers:
                raise ConfigurationError(
                    "Failed to obtain workflowManagers from configurator"
                )

            if not skipConfigCheck:
                self.checkConfiguration(checkCare)

            # TODO - Re-add when Provenance is complete
            # provSetup = self._productionRunConfigurator.getProvenanceSetup()
            #
            # provSetup.recordProduction()

            for workflow in self._workflowManagers["__order"]:
                mgr = self._workflowManagers[workflow.getName()]

                statusListener = StatusListener()
                # this will block until the monitor is created.
                monitor = mgr.runWorkflow(statusListener)
                self._workflowMonitors.append(monitor)

        finally:
            self._locked.release()

        self._startServiceThread()

        print("Production launched.")
        print("Waiting for shutdown request.")

    def isRunning(self):
        """Determine whether production is currently running

        Returns
        -------
        running : `bool`
            Returns True if production is running, otherwise returns False
        """
        #
        # check each monitor.  If any of them are still running,
        # the production is still running.
        #
        for monitor in self._workflowMonitors:
            if monitor.isRunning():
                return True

        with self._locked:
            self._locked.running = False

        return False

    def isDone(self):
        """Determine whether production has completed

        Returns
        -------
        done : `bool`
            Returns True if production has completed, otherwise returns False
        """

        return self._locked.done

    def isRunnable(self):
        """Determine whether production can be run

        Returns
        -------
        runnable : `bool`
            Returns True if production can be run, otherwise returns False

        Notes
        -----
        Production is runnable if it isn't already running, or hasn't already been completed.  It
        can not be re-started once it's already running, or re-run if it has been completed.
        """
        return not self.isRunning() and not self.isDone()

    def createConfigurator(self, runid, configFile):
        """Create the ProductionRunConfigurator specified in the config file

        Parameters
        ----------
        runid : `str`
            run id
        configFile: `Config`
            Config file containing which ProductinRunConfigurator to create

        Returns
        -------
        Initialized ProductionRunConfigurator of the type specified in configFile
        """
        log.debug("ProductionRunManager:createConfigurator")

        configuratorClass = ProductionRunConfigurator
        configuratorClassName = None
        if self.config.configurationClass is not None:
            configuratorClassName = self.config.configurationClass
        if configuratorClassName is not None:
            classFactory = NamedClassFactory()
            configuratorClass = classFactory.createClass(configuratorClassName)

        return configuratorClass(runid, configFile, self.repository)

    def checkConfiguration(self, care=1, issueExc=None):
        """Check the configuration of the production

        Parameters
        ----------
        care : `int`, optional
            The level of "care" to take in checking the configuration.
        issueExc : `MultiIssueConfigurationError`, optional
            An exception to add addition problems to. (see note)

        Notes
        -----
        In general, the higher the care number, the more checks that are made.
        If issueExc is not None, this method will not raise an exception when problems are
        encountered;  they will be added to the issueExc instance.  It is assumed that the caller
        will raise that exception as necessary.
        """

        log.debug("checkConfiguration")

        if not self._workflowManagers:
            msg = "%s: production has not been configured yet" % self.runid
            if self._name:
                msg = "%s %s" % (self._name, msg)
            if issueExc is None:
                raise ConfigurationError(msg)
            else:
                issueExc.addProblem(msg)
                return

        myProblems = issueExc
        if myProblems is None:
            myProblems = MultiIssueConfigurationError(
                "problems encountered while checking configuration"
            )

        # check production-wide configuration
        self._productionRunConfigurator.checkConfiguration(care, myProblems)

        # check configuration for each workflow
        for workflow in self._workflowManagers["__order"]:
            workflowMgr = self._workflowManagers[workflow]
            workflowMgr.checkConfiguration(care, myProblems)

        if not issueExc and myProblems.hasProblems():
            raise myProblems

    def stopProduction(self, urgency, timeout=1800):
        """Stops all workflows in this production run

        Parameters
        ----------
        urgency : `int`
            An indicator of how urgently to carry out the shutdown.
        timeout : `int`
            An time to wait (in sec nds) for workflows to finish.

        Returns
        -------
        success : `bool`
            True on successful shutdown of workflows, False otherwise.

        Notes
        -----
        For urgency, it is intended that recognized values should be:

        FINISH_PENDING_DATA - end after all currently available data has been processed
        END_ITERATION       - end after the current data looping iteration
        CHECKPOINT          - end at next checkpoint opportunity (typically between stages)
        NOW                 - end as soon as possible, foregoing any check-pointing
        """
        if not self.isRunning():
            log.info("shutdown requested when production is not running")
            return

        log.info("Shutting down production (urgency=%s)" % urgency)

        for workflow in self._workflowManagers["__order"]:
            workflowMgr = self._workflowManagers[workflow.getName()]
            workflowMgr.stopWorkflow(urgency)

        pollintv = 0.2
        running = self.isRunning()
        lasttime = time.time()
        while running and timeout > 0:
            time.sleep(pollintv)
            for workflow in self._workflowManagers["__order"]:
                running = self._workflowManagers[workflow.getName()].isRunning()
                if running:
                    break
            timeout -= time.time() - lasttime
        if not running:
            with self._locked:
                self._locked.running = False
                self._locked.done = True
        else:
            log.debug("Failed to shutdown pipelines within timeout: %ss" % timeout)
            return False

        return True

    def getWorkflowNames(self):
        """Accessor to return the "short" name for each workflow in this production.

        Returns
        -------
        names : [ 'wfShortName1', 'wfShortName2' ]
           list of "short" names for these workflows.

        Notes
        -----
        These names may have been adjusted to ensure a unique list.  These are names that can be
        passed by getWorkflowManager().   "Short" names are aliases to the workflows.
        """
        if self._workflowManagers:
            return self._workflowManagers["__order"]
        elif self._productionRunConfigurator:
            return self._productionRunConfigurator.getWorkflowNames()
        else:
            cfg = self.createConfigurator(self.fullConfigFilePath)
            return cfg.getWorkflowNames()

    def getWorkflowManager(self, name):
        """Accessor to return the named WorkflowManager

        Parameters
        ----------
        name : `str`
            The name of the WorkflowManager to retrieve

        Returns
        -------
        wfMgr : `WorkflowManager`
            A WorkflowManager instance or None if it has not been created yet or name is not one of
            the names returned by getWorkflowNames()
        """

        if not self._workflowManagers or name not in self._workflowManagers:
            return None
        return self._workflowManagers[name]

    class ThreadedServer(ThreadingMixIn, HTTPServer):
        """threaded server"""

        def server_bind(self):
            HTTPServer.server_bind(self)

        def setManager(self, manager):
            self.manager = manager
            self.socket.settimeout(1)

        def serve(self):
            while self.manager.isRunning():
                self.handle_request()

    class _ServiceEndpoint(threading.Thread):
        """This thread deals with incoming requests, and if one is received during production, we
           shut everything down.

        Parameters
        ----------
        parent : `Thread`
            The parent Thread of this Thread.
        runid : `str`
            run id
        pollingIntv : `float`
            the polling interval to sleep, in seconds.
        listenTimeout : `int`
            the interval, in seconds, to wait for an incoming request

        Notes
        -----
        This is a private class.
        """

        def __init__(self, parent, runid, pollingIntv=1.0, listenTimeout=10):
            threading.Thread.__init__(self)
            self.setDaemon(True)
            self._runid = runid
            self._parent = parent
            self._pollintv = pollingIntv
            self._timeout = listenTimeout

            handlerClass = MakeServiceHandlerClass(parent, runid)
            self.server = parent.ThreadedServer(("0.0.0.0", 0), handlerClass)
            self.server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            print("server socket listening at %d" % self.server.server_port)

        def run(self):
            """Set Manager and serve requests until complete."""
            self.server.setManager(self._parent)

            self.server.serve()
            log.debug("Everything shutdown - All finished")

    def _startServiceThread(self):
        """Create a shutdown thread, and start it"""
        self._sdthread = ProductionRunManager._ServiceEndpoint(self, self.runid)
        self._sdthread.start()

    def getShutdownThread(self):
        """Accessor to return shutdown thread for this production

        Returns
        -------
        t : `Thread`
            The shutdown Thread.
        """
        return self._sdthread

    def joinShutdownThread(self):
        """Thread join the shutdown thread for this production"""
        if self._sdthread is not None:
            self._sdthread.join()
