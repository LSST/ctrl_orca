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

import lsst.log as log
from lsst.ctrl.orca.NamedClassFactory import NamedClassFactory

##
# @brief an abstract class for configuring a workflow
#
#


class WorkflowConfigurator:
    """Abstract class for configuring a workflow

    Parameters
    ----------
    runid : `str`
        run id
    prodConfig : `Config`
        production Config object
    wfConfig : `Config`
        workflow Config object

    Notes
    -----
    This class should not be used directly but rather must be subclassed,
    providing an implementation for at least _configureWorkflowLauncher.
    Usually, _configureSpecialized() should also be overridden to carry
    out the non-database setup, including deploying the workflow onto the
    remote platform.
    """

    # configuration group
    class ConfigGroup:
        """Configuration group

        Parameters
        ----------
        name : `str`
            Name of this Config
        config: `Config`
            The Config object itself
        number : `int`
            The number assigned to this ConfigGroup
        offset : `int`
            global offset (deprecated)

        Notes
        -----
        Names and numbers are assigned to ConfigGroups in order to address
        them either way.
        """

        def __init__(self, name, config, number, offset):
            # name of this configuration
            self.configName = name

            # the configuration itself
            self.config = config

            # the value assigned to this particular configuration
            self.configNumber = number

            # @deprecated global offset
            self.globalOffset = offset

        def getConfig(self):
            """Accessor to the Config object

            Returns
            -------
            The config object
            """
            return self.config

        def getConfigName(self):
            """Accessor to the Config name

            Returns
            -------
            The config name
            """

            return self.configName

        def getConfigNumber(self):
            """Accessor to the Config number

            Returns
            -------
            This Config's number
            """

            return self.configNumber

        # @deprecated the offset to use
        def getGlobalOffset(self):
            return self.globalOffset

        # @return a string describing this configuration group
        def __str__(self):
            print("self.configName = ", self.configName, "self.config = ", self.config)
            return "configName =" + self.configName

    def __init__(self, runid, prodConfig, wfConfig):
        # the run id associated with this workflow
        self.runid = runid

        log.debug("WorkflowConfigurator:__init__")

        # the production configuration
        self.prodConfig = prodConfig

        # the workflow configuration
        self.wfConfig = wfConfig

        raise RuntimeError(
            "Attempt to instantiate abstract class: WorkflowConfigurator; see class docs"
        )

    def configure(self, provSetup, workflowVerbosity=None):
        """Configure the workflow (including database, and any specialized
        required setup)

        Parameters
        ----------
        provSetup : `Config`
            provenance Configuration
        workflowVerbosity : `int`
            verbosity level to set for workflow

        Returns
        -------
        WorkflowLauncher object to launch the workflow
        """
        log.debug("WorkflowConfigurator:configure")
        self._configureDatabases(provSetup)
        return self._configureSpecialized(self.wfConfig, workflowVerbosity)

    ##
    # @brief Setup as much as possible in preparation to execute the workflow
    #            and return a WorkflowLauncher object that will launch the
    #            configured workflow.
    # @param config the workflow config
    # @param provSetup
    #
    def _configureDatabases(self, provSetup):
        """Configure database in preparation to execute the workflow

        Parameters
        ----------
        provSetup : `Config`
            provenance Configuration
        """
        log.debug("WorkflowConfigurator:_configureDatabases")

        #
        # setup the database for each database listed in workflow config
        #

        if self.wfConfig.database is not None:
            databaseConfigs = self.wfConfig.database

            for databaseConfig in databaseConfigs:
                databaseConfigurator = self.createDatabaseConfigurator(databaseConfig)
                databaseConfigurator.setup(provSetup)
        return

    def _configureSpecialized(self, wfConfig):
        """Complete non-database setup, including deploying the workfow and
        its pipelines.

        Notes
        -----
        Normally, this method should be overridden.

        Returns
        -------
        WorkflowLauncher object
        """

        workflowLauncher = self._createWorkflowLauncher()
        return workflowLauncher

    def _createWorkflowLauncher(self):
        """Create the workflow launcher

        Notes
        -----
        This abstract method must be overridden; otherwise an exception is
        raised.
        """

        msg = 'called "abstract" WorkflowConfigurator._createWorkflowLauncher'
        log.info(msg)
        raise RuntimeError(msg)

    def createDatabaseConfigurator(self, databaseConfig):
        """Lookup and create the configurator for database operations

        Parameters
        ----------
        databaseConfig : `Config`
            Config object containing database configuration information.

        Returns
        -------
        Initialized DatabaseConfigurator object
        """

        log.debug("WorkflowConfigurator:createDatabaseConfigurator")
        className = databaseConfig.configurationClass
        classFactory = NamedClassFactory()
        configurationClass = classFactory.createClass(className)
        configurator = configurationClass(self.runid, databaseConfig)
        return configurator

    ##
    # @brief given a list of pipelineConfigs, number the section we're
    # interested in based on the order they are in, in the productionConfig
    # We use this number Provenance to uniquely identify this set of pipelines
    #
    def expandConfigs(self, wfShortName):
        # Pipeline provenance requires that "activoffset" be unique and
        # sequential for each pipeline in the production.  Each workflow
        # in the production can have multiple pipelines, and even a call for
        # duplicates of the same pipeline within it.
        #
        # Since these aren't numbered within the production config file itself,
        # we need to do this ourselves. This is slightly tricky, since each
        # workflow is handled individually by orca and had has no reference
        # to the other workflows or the number of pipelines within
        # those workflows.
        #
        # Therefore, what we have to do is go through and count all the
        # pipelines in the other workflows so we can enumerate the pipelines
        # in this particular workflow correctly. This needs to be reworked.

        print("expandConfigs wfShortName = ", wfShortName)
        totalCount = 1
        for wfName in self.prodConfig.workflow:
            wfConfig = self.prodConfig.workflow[wfName]
            if wfName == wfShortName:
                # we're in the config which needs to be numbered
                expanded = []

                for pipelineName in wfConfig.pipeline:
                    config = wfConfig.pipeline[pipelineName]
                    # default to 1, if runCount doesn't exist
                    runCount = 1
                    if config.runCount is not None:
                        runCount = config.runCount
                    for i in range(runCount):
                        expanded.append(
                            self.ConfigGroup(pipelineName, config, i + 1, totalCount)
                        )
                        totalCount = totalCount + 1

                return expanded
            else:

                for pipelineName in wfConfig.pipeline:
                    pipelineConfig = wfConfig.pipeline[pipelineName]
                    if pipelineConfig.runCount is not None:
                        totalCount = totalCount + pipelineConfig.runCount
                    else:
                        totalCount = totalCount + 1
        # should never reach here - this is an error
        return None
