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

from lsst.ctrl.orca.exceptions import MultiIssueConfigurationError
from lsst.ctrl.orca.multithreading import SharedData
from lsst.ctrl.orca.NamedClassFactory import NamedClassFactory

log = logging.getLogger(__name__)
##
# @brief workflow manager base class
#


class WorkflowManager:
    """Manage lifecycle of this workflow.

    Parameters
    ----------
    name : `str`
        name of this workflow.
    runid : `str`
        run id.
    repository : `str`
        repository directory
    prodConfig : `Config`
        production Config
    wfConfig : `Config`
        workflow Config
    """

    def __init__(self, name, runid, repository, prodConfig, wfConfig):

        # _locked: a container for data to be shared across threads that
        # have access to this object.
        self._locked = SharedData.SharedData(False)

        #  workflow name
        self.name = "unnamed"
        if name is not None:
            self.name = name

        # run id of this workflow
        self.runid = runid

        # repository where the configuration is kept
        self.repository = repository

        # workflow configuration
        self.wfConfig = wfConfig

        # production configuration
        self.prodConfig = prodConfig

        self._workflowConfigurator = None

        log.debug("WorkflowManager:__init__")

        # the urgency level of how fast to stop the workflow
        self.urgency = 0
        self._launcher = None
        self._monitor = None

    # @deprecated return the name of this workflow
    def getName(self):
        return self.name

    ##
    # @brief setup, launch and monitor a workflow to its completion, and then
    #            clean-up.
    #
    def runWorkflow(self, statusListener):
        """setup, launch and monitor a workflow to its completion, and then
        clean up"""
        log.debug("WorkflowManager:runWorkflow")

        if not self.isRunnable():
            if self.isRunning():
                log.info("Workflow %s is already running" % self.runid)
            if self.isDone():
                log.info(
                    "Workflow %s has already run; start with new runid" % self.runid
                )
            return False

        try:
            self._locked.acquire()

            if self._workflowConfigurator is None:
                self._workflowLauncher = self.configure()
            self._monitor = self._workflowLauncher.launch(statusListener)

            self.cleanUp()

        finally:
            self._locked.release()
        return self._monitor

    def stopWorkflow(self, urgency):
        """Stop the workflow

        Parameters
        ----------
        urgency : `int`
            urgency at which to shut down this workflow
        """

        log.debug("WorkflowManager:stopWorkflow")
        if self._monitor:
            self._monitor.stopWorkflow(urgency)
        else:
            log.info("Workflow %s is not running" % self.name)

    def cleanUp(self):
        """Carry out post-execution tasks for removing workflow data and
        state from the platform and archiving/ingesting products as needed.
        """

        log.debug("WorkflowManager:cleanUp")

    def configure(self, provSetup=None, workflowVerbosity=None):
        """Prepare a workflow for launching
        Parameters
        ----------
        provSetup : `object`
            A provenance setup object to pass to Configurator instances.
        workflowVerbosity : `int`
            The logging verbosity level to set for workflows

        Returns
        -------
        WorkflowLauncher
        """
        log.debug("WorkflowManager:configure")
        if self._workflowConfigurator:
            log.info("production has already been configured.")
            return

        # lock this branch of code
        try:
            self._locked.acquire()

            self._workflowConfigurator = self.createConfigurator(
                self.runid, self.repository, self.name, self.wfConfig, self.prodConfig
            )
            self._workflowLauncher = self._workflowConfigurator.configure(
                provSetup, workflowVerbosity
            )
        finally:
            self._locked.release()

        # do specialized workflow level configuration here, this may include
        # calling ProvenanceSetup.getWorkflowCommands()
        return self._workflowLauncher

    def createConfigurator(self, runid, repository, wfName, wfConfig, prodConfig):
        """Create a Workflow configurator for this workflow.

        Parameters
        ----------
        runid : `str`
            the production run id
        repository : `str`
             the directory location of the repository
        wfName : `str`
             the workflow name
        wfConfig : Config
             the config describing the workflow
        prodConfig : Config
             the config describing the overall production.  This provides
             common data that needs to be shared with all pipelines.

        Returns
        -------
        WorkflowConfigurator
        """
        log.debug("WorkflowManager:createConfigurator")

        className = wfConfig.configurationClass
        classFactory = NamedClassFactory()

        configuratorClass = classFactory.createClass(className)
        configurator = configuratorClass(
            self.runid, repository, prodConfig, wfConfig, wfName
        )
        return configurator

    def isRunning(self):
        """Report whether workflow is currently running"""
        if self._monitor:
            return self._monitor.isRunning()
        return False

    def isDone(self):
        """Report whether workflow has completed

        Returns
        -------
        True if the workflow has been run to completion.

        Notes
        -----
        This will be true if the workflow has run normally through cleaned up
        or if it was stopped and clean-up has been called.
        """
        log.debug("WorkflowManager:isDone")
        if self._monitor:
            return self._monitor.isDone()
        return False

    def isRunnable(self):
        """Report whether workflow is capable of running

        Returns
        -------
        True if the workflow can still be called.

        Notes
        -----
        This may return False because the workflow has already been run and
        cannot be re-run.
        """
        log.debug("WorkflowManager:isRunnable")
        return not self.isRunning() and not self.isDone()

    def checkConfiguration(self, care=1, issueExc=None):
        """Runs checks that ensure that the Workflow has been properly set up.

        Raises
        ------
        MultiIssueConfigurationError if problems are found

        Parameters
        ----------
        care : `int`
             the thoroughness of the checks. In general, a higher number will
             result in more checks.
        issueExc : `MultiIssueConfigurationError`
             An instance of MultiIssueConfigurationError to add problems to.
             If not None, this function will not raise an exception when
             problems are encountered; they will merely be added to the
             instance.  It is assumed that the caller will raise that
             exception is necessary.
        """
        log.debug("WorkflowManager:createConfiguration")

        myProblems = issueExc
        if myProblems is None:
            myProblems = MultiIssueConfigurationError(
                "problems encountered while checking configuration"
            )

        # do the checks

        # raise exception if problems found
        if not issueExc and myProblems.hasProblems():
            raise myProblems

    def getWorkflowName(self):
        """Accessor to workflow name

        Returns
        -------
        name : `str`
            The name of this workflow.
        """
        return self.name

    def getNodeCount(self):
        """Accessor to the number of nodes specified in this configuration

        Returns
        -------
        The number of nodes used by this workflow.
        """
        return self._workflowConfigurator.getNodeCount()
