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

from lsst.ctrl.orca.config.ProductionConfig import ProductionConfig
from lsst.ctrl.orca.exceptions import MultiIssueConfigurationError
from lsst.ctrl.orca.NamedClassFactory import NamedClassFactory
from lsst.ctrl.orca.WorkflowManager import WorkflowManager

log = logging.getLogger(__name__)


class ProductionRunConfigurator:
    """Create a basic production run.

    Parameters
    ----------
    runid : `str`
        run id
    configFile : `str`
        production configuration file
    repository : `str`, optional
        file system location of the repository
    workflowVerbosity : `int`, optional
        verbosity level of the workflow
    """

    def __init__(self, runid, configFile, repository=None, workflowVerbosity=None):

        log.debug("ProductionRunConfigurator:__init__")

        # run id for this production
        self.runid = runid

        self._prodConfigFile = configFile

        # production configuration
        self.prodConfig = ProductionConfig()
        self.prodConfig.load(configFile)

        # location of the repository
        self.repository = repository

        # verbosity level for this workflow
        self.workflowVerbosity = workflowVerbosity

        self._provSetup = None

        # provenance dictionary
        self.provenanceDict = {}
        self._wfnames = None

        # cache the database configurators for checking the configuraiton.
        self._databaseConfigurators = []

        # these are config settings which can be overriden from what they
        # are in the workflow policies.

        # dictionary of configuration override values
        self.configOverrides = dict()

        production = self.prodConfig.production
        if production.logThreshold is not None:
            self.configOverrides["execute.logThreshold"] = production.logThreshold

    def createWorkflowManager(self, prodConfig, wfName, wfConfig):
        """Create the WorkflowManager for the pipeline with the given shortName

        Parameters
        ----------
        prodConfig : `Config`
        wfName : `str`
        wfConfig : `Config`
        """
        log.debug("ProductionRunConfigurator:createWorkflowManager")

        wfManager = WorkflowManager(
            wfName, self.runid, self.repository, prodConfig, wfConfig
        )
        return wfManager

    def getProvenanceSetup(self):
        """Accessor to provenance setup information

        Returns
        -------
        s : `str`
            provenance setup information
        """
        return self._provSetup

    def configure(self, workflowVerbosity):
        """Configure this production run

        Parameters
        ----------
        workflowVerbosity : `int`
            verbosity level of the workflows

        Returns
        -------
        mgrs : [ wfMgr1, wfMgr2 ]
            list of workflow managers, one per workflow
        """
        log.debug("ProductionRunConfigurator:configure")

        # TODO - IMPORTANT - NEXT TWO LINES ARE FOR PROVENANCE
        # --------------
        # self._provSetup = ProvenanceSetup()
        # self._provSetup.addAllProductionConfigFiles(self._prodConfigFile,
        #                                             self.repository)
        # --------------

        #
        # setup the database for each database listed in production config.
        # cache the configurators in case we want to check the configuration
        # later.
        #
        databaseConfigs = self.prodConfig.database

        for databaseName in databaseConfigs:
            databaseConfig = databaseConfigs[databaseName]
            cfg = self.createDatabaseConfigurator(databaseConfig)
            cfg.setup(self._provSetup)

            self._databaseConfigurators.append(cfg)

        #
        # do specialized production level configuration, if it exists
        #
        if self.prodConfig.production.configuration.configurationClass is not None:
            specialConfigurationConfig = self.prodConfig.production.configuration
            # XXX - specialConfigurationConfig maybe?
            self.specializedConfigure(specialConfigurationConfig)

        workflowConfigs = self.prodConfig.workflow
        workflowManagers = []
        for wfName in workflowConfigs:
            wfConfig = workflowConfigs[wfName]
            # copy in appropriate production level info into workflow Node -- ?

            workflowManager = self.createWorkflowManager(
                self.prodConfig, wfName, wfConfig
            )
            workflowLauncher = workflowManager.configure(
                self._provSetup, workflowVerbosity
            )
            if workflowLauncher is None:
                raise MultiIssueConfigurationError("error configuring workflowLauncher")

            workflowManagers.append(workflowManager)

        return workflowManagers

    def checkConfiguration(self, care=1, issueExc=None):
        """Carry out production-wide configuration checks.

        Parameters
        ----------
        care : `int`
            throughness level of the checks
        issueExc : `MultiIssueConfigurationError`
            an instance of MultiIssueConfigurationError to add problems to

        Raises
        ------
        `MultiIssueConfigurationError`
            If issueExc is None, and a configuration error is detected.

        Notes
        -----
        If issueExc is not None, this method will not raise an exception when
        problems are encountered; they will merely be added to the instance.
        It is assumed that the caller will raise the exception as necessary.
        """
        log.debug("checkConfiguration")
        myProblems = issueExc
        if myProblems is None:
            myProblems = MultiIssueConfigurationError(
                "problems encountered while checking configuration"
            )

        for dbconfig in self._databaseConfigurators:
            print("-> dbconfig = ", dbconfig)
            dbconfig.checkConfiguration(care, issueExc)

        if not issueExc and myProblems.hasProblems():
            raise myProblems

    def createDatabaseConfigurator(self, databaseConfig):
        """Create the configurator for database operations

        Parameters
        ----------
        databaseConfig: `Config`
            database Config object

        Returns
        -------
        configurator : `DatabaseConfigurator`
            the configurator specified in the database Config object
        """
        log.debug("ProductionRunConfigurator:createDatabaseConfigurator")
        className = databaseConfig.configurationClass
        classFactory = NamedClassFactory()
        configurationClass = classFactory.createClass(className)
        configurator = configurationClass(self.runid, databaseConfig, self.prodConfig)
        return configurator

    def _specializedConfigure(self, specialConfigurationConfig):
        """Do any production-wide setup not covered by the setup of the #
        databases or the individual workflows.

        Parameters
        ----------
        specialConfigurationConfig : `Config`
            Config object for specialized configurations

        Notes
        -----
        This implementation does nothing.  Subclasses may override this method
        to provide specialized production-wide setup.
        """
        pass

    def getWorkflowNames(self):
        """Accessor to return workflow names

        Returns
        -------
        names : [ 'wfName1', 'wfName2' ]
            list of strings with named workflows
        """
        return self.prodConfig.workflowNames
