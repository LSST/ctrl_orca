#
# LSST Data Management System
# Copyright 2008-2017 LSST Corporation.
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
import sys
from shutil import copy

import lsst.log as log
from lsst.ctrl.orca.EnvString import EnvString
from lsst.ctrl.orca.PegasusWorkflowLauncher import PegasusWorkflowLauncher
from lsst.ctrl.orca.TemplateWriter import TemplateWriter
from lsst.ctrl.orca.WorkflowConfigurator import WorkflowConfigurator

##
#
# PegasusWorkflowConfigurator
#


class PegasusWorkflowConfigurator(WorkflowConfigurator):
    """Pegasus specialized workflow configurator

    Parameters
    ----------
    runid : str
        run id
    repository : str
        repository directory
    prodConfig : Config
        production config object
    wfConfig : Config
        workflow config object
    wfName : str
        workflow name
    """

    def __init__(self, runid, repository, prodConfig, wfConfig, wfName):
        log.debug("PegasusWorkflowConfigurator:__init__")

        self.runid = runid
        self.repository = repository
        self.prodConfig = prodConfig
        self.wfConfig = wfConfig
        self.wfName = wfName

        # logging verbosity of workflow
        self.wfVerbosity = None

        # @deprecated directories
        self.dirs = None

        # directories
        self.directories = None

        # @deprecated nodes used in this production
        self.nodes = None

        # @deprecated number of nodes
        self.numNodes = None

        # @deprecated names of the log file
        self.logFileNames = []

        # names of the pipelines
        self.pipelineNames = []

        # @deprecated list of directories
        self.directoryList = {}

        # @deprecated initial working directory
        self.initialWorkDir = None

        # @deprecated first initial working directory
        self.firstRemoteWorkDir = None

        # default root for the production
        self.defaultRoot = wfConfig.platform.dir.defaultRoot

    def configure(self, provSetup, wfVerbosity):
        """Setup as much as possible in preparation to execute the workflow
           and return a WorkflowLauncher object that will launch the
           configured workflow.

        Parameters
        ----------
        provSetup : Config
            provenance setup
        wfVerbosity : int
            verbosity level of workflow

        Notes
        -----
        Provenance info is set here has a placeholder for when it gets
        reintroduced.
        """
        self.wfVerbosity = wfVerbosity
        self._configureDatabases(provSetup)
        return self._configureSpecialized(provSetup, self.wfConfig)

    def _configureSpecialized(self, provSetup, wfConfig):
        log.debug("PegasusWorkflowConfigurator:configure")

        localConfig = wfConfig.configuration["pegasus"]

        # local scratch directory
        self.localScratch = localConfig.condorData.localScratch

        # platformConfig = wfConfig.platform
        taskConfigs = wfConfig.task

        # local staging directory
        self.localStagingDir = os.path.join(self.localScratch, self.runid)
        os.makedirs(self.localStagingDir)

        # write the glidein file
        startDir = os.getcwd()
        os.chdir(self.localStagingDir)

        if localConfig.glidein.template.inputFile is not None:
            self.writeGlideinFile(localConfig.glidein)
        else:
            log.debug("PegasusWorkflowConfigurator: not writing glidein file")
        os.chdir(startDir)

        # TODO - fix this loop for multiple condor submits; still working
        # out what this might mean.
        for taskName in taskConfigs:
            task = taskConfigs[taskName]

            # script directory
            self.scriptDir = task.scriptDir

            # save initial directory we were called from so we can get back
            # to it
            startDir = os.getcwd()

            # switch to staging directory
            os.chdir(self.localStagingDir)

            # switch to tasks directory in staging directory
            scriptDir = os.path.join(self.localStagingDir, task.scriptDir)
            os.makedirs(scriptDir)
            os.chdir(scriptDir)

            # set configuration
            task.generator.name = "dax"
            generatorConfig = task.generator.active

            # generate sites file

            sitesTemplate = EnvString.resolve(generatorConfig.sites.inputFile)
            sitesOutputFile = EnvString.resolve(generatorConfig.sites.outputFile)
            keywords = generatorConfig.sites.keywords
            self.writeSitesXML(sitesOutputFile, sitesTemplate, keywords)
            sitesXMLFile = os.path.join(scriptDir, sitesOutputFile)

            # copy transform file
            transform = EnvString.resolve(generatorConfig.transformFile)
            copy(transform, scriptDir)
            transformFile = os.path.join(scriptDir, transform)

            # generate dax
            daxScript = EnvString.resolve(generatorConfig.script)
            copy(daxScript, scriptDir)
            daxGenerator = os.path.join(
                scriptDir, os.path.basename(generatorConfig.script)
            )

            log.debug("PegasusWorkflowConfigurator:configure: generate dax")
            daxGeneratorInput = EnvString.resolve(generatorConfig.inputFile)

            # change into the local staging area to create the DAX file, and
            # its output.
            os.chdir(self.localStagingDir)
            daxCreatorCmd = [daxGenerator, "-i", daxGeneratorInput, "-o", "output.dax"]

            pid = os.fork()
            if not pid:
                # turn off all output from this command
                sys.stdin.close()
                sys.stdout.close()
                sys.stderr.close()
                os.close(0)
                os.close(1)
                os.close(2)
                os.execvp(daxCreatorCmd[0], daxCreatorCmd)
            os.wait()[0]

            # create dax log directories ?

            # change back to initial directory
            os.chdir(startDir)

        # create the Launcher

        workflowLauncher = PegasusWorkflowLauncher(
            self.prodConfig,
            self.wfConfig,
            self.runid,
            self.localStagingDir,
            sitesXMLFile,
            transformFile,
            "output.dax",
            wfConfig.monitor,
        )
        return workflowLauncher

    def writeSitesXML(self, outputFile, template, keywords):
        """Write the prescript script

        Parameters
        ----------
        outputFileName : str
            output file name for pre script
        template : Config
            config file template
        keywords : { 'key1' : 'value', 'key2' : 'value2'}
            keyword/value dictionary
        """
        pairs = {}
        for value in keywords:
            val = keywords[value]
            pairs[value] = val
        pairs["ORCA_RUNID"] = self.runid
        pairs["ORCA_DEFAULTROOT"] = self.defaultRoot
        writer = TemplateWriter()
        writer.rewrite(template, outputFile, pairs)

    def getWorkflowName(self):
        """get the workflow name"""
        return self.wfName

    # @deprecated
    def deploySetup(self, provSetup, wfConfig, platformConfig, pipelineConfigGroup):
        log.debug("CondorWorkflowConfigurator:deploySetup")

    # @deprecated create the platform.dir directories
    def createDirs(self, localStagingDir, platformDirConfig):
        log.debug("CondorWorkflowConfigurator:createDirs")

    # @deprecated set up this workflow's database
    def setupDatabase(self):
        log.debug("CondorWorkflowConfigurator:setupDatabase")
