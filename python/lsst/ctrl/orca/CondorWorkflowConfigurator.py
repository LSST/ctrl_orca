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

import getpass
import logging
import os
import os.path
import stat
import sys

from lsst.ctrl.orca.CondorWorkflowLauncher import CondorWorkflowLauncher
from lsst.ctrl.orca.EnvString import EnvString
from lsst.ctrl.orca.TemplateWriter import TemplateWriter
from lsst.ctrl.orca.WorkflowConfigurator import WorkflowConfigurator

log = logging.getLogger(__name__)

##
#
# CondorWorkflowConfigurator
#


class CondorWorkflowConfigurator(WorkflowConfigurator):
    """Condor specialized workflow configurator

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
        log.debug("CondorWorkflowConfigurator:__init__")

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
        log.debug("CondorWorkflowConfigurator:configure")

        localConfig = wfConfig.configuration["condor"]

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
            log.debug("CondorWorkflowConfigurator: not writing glidein file")
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
            taskOutputDir = os.path.join(self.localStagingDir, task.scriptDir)
            os.makedirs(taskOutputDir)
            os.chdir(taskOutputDir)

            # generate pre job
            preJobScript = EnvString.resolve(task.preJob.script.outputFile)
            preJobScriptInputFile = EnvString.resolve(task.preJob.script.inputFile)
            keywords = task.preJob.script.keywords
            self.writeJobScript(preJobScript, preJobScriptInputFile, keywords)

            preJobCondorOutputFile = EnvString.resolve(task.preJob.condor.outputFile)
            preJobCondorInputFile = EnvString.resolve(task.preJob.condor.inputFile)
            keywords = task.preJob.condor.keywords
            self.writeJobScript(
                preJobCondorOutputFile, preJobCondorInputFile, keywords, preJobScript
            )

            # generate post job
            postJobScript = EnvString.resolve(task.postJob.script.outputFile)
            postJobScriptInputFile = EnvString.resolve(task.postJob.script.inputFile)
            keywords = task.postJob.script.keywords
            self.writeJobScript(postJobScript, postJobScriptInputFile, keywords)

            postJobCondorOutputFile = EnvString.resolve(task.postJob.condor.outputFile)
            postJobCondorInputFile = EnvString.resolve(task.postJob.condor.inputFile)
            keywords = task.postJob.condor.keywords
            self.writeJobScript(
                postJobCondorOutputFile, postJobCondorInputFile, keywords, postJobScript
            )

            # generate worker job
            workerJobScript = EnvString.resolve(task.workerJob.script.outputFile)
            workerJobScriptInputFile = EnvString.resolve(
                task.workerJob.script.inputFile
            )
            keywords = task.workerJob.script.keywords
            self.writeJobScript(workerJobScript, workerJobScriptInputFile, keywords)

            workerJobCondorOutputFile = EnvString.resolve(
                task.workerJob.condor.outputFile
            )
            workerJobCondorInputFile = EnvString.resolve(
                task.workerJob.condor.inputFile
            )
            keywords = task.workerJob.condor.keywords
            self.writeJobScript(
                workerJobCondorOutputFile,
                workerJobCondorInputFile,
                keywords,
                workerJobScript,
            )

            # switch to staging directory
            os.chdir(self.localStagingDir)

            # generate pre script
            log.debug("CondorWorkflowConfigurator:configure: generate pre script")

            if task.preScript.script.outputFile is not None:
                preScriptOutputFile = EnvString.resolve(
                    task.preScript.script.outputFile
                )
                preScriptInputFile = EnvString.resolve(task.preScript.script.inputFile)
                keywords = task.preScript.script.keywords
                self.writePreScript(preScriptOutputFile, preScriptInputFile, keywords)
                os.chmod(
                    task.preScript.outputFile,
                    stat.S_IRWXU
                    | stat.S_IRGRP
                    | stat.S_IXGRP
                    | stat.S_IROTH
                    | stat.S_IXOTH,
                )

            # generate dag
            log.debug("CondorWorkflowConfigurator:configure: generate dag")

            task.generator.name = "dag"
            generatorConfig = task.generator.active
            dagGenerator = EnvString.resolve(generatorConfig.script)
            dagGeneratorInput = EnvString.resolve(generatorConfig.inputFile)
            dagCreatorCmd = [
                dagGenerator,
                "-s",
                dagGeneratorInput,
                "-w",
                task.scriptDir,
                "-t",
                task.workerJob.condor.outputFile,
                "-r",
                self.runid,
                "--idsPerJob",
                str(generatorConfig.idsPerJob),
            ]
            if task.preScript.script.outputFile is not None:
                dagCreatorCmd.append("-p")
                dagCreatorCmd.append(task.preScript.script.outputFile)
            pid = os.fork()
            if not pid:
                # turn off all output from this command
                sys.stdin.close()
                sys.stdout.close()
                sys.stderr.close()
                os.close(0)
                os.close(1)
                os.close(2)
                os.execvp(dagCreatorCmd[0], dagCreatorCmd)
            os.wait()[0]

            # create dag logs directories
            fileObj = open(dagGeneratorInput, "r")
            visitSet = set()
            count = 0
            # this info from gd:
            # Searching for a space detects
            # extended input like :  visit=887136081 raft=2,2 sensor=0,1
            # No space is something simple like a skytile id
            for aline in fileObj:
                count += 1
                visit = str(count // 100)
                visitSet.add(visit)
            log.debug("CondorWorkflowConfigurator:configure: about to make logs")
            logDirName = os.path.join(self.localStagingDir, "logs")
            log.debug(
                "CondorWorkflowConfigurator:configure: logDirName = %s", logDirName
            )
            logDirName = os.path.join(self.localStagingDir, "logs")
            os.makedirs(logDirName)
            for visit in visitSet:
                dirName = os.path.join(logDirName, visit)
                log.debug("making dir %s ", dirName)
                os.makedirs(dirName)

            # change back to initial directory
            os.chdir(startDir)

        # create the Launcher

        workflowLauncher = CondorWorkflowLauncher(
            self.prodConfig,
            self.wfConfig,
            self.runid,
            self.localStagingDir,
            generatorConfig.dagName + ".diamond.dag",
            wfConfig.monitor,
        )
        return workflowLauncher

    def writePreScript(self, outputFileName, template, keywords):
        """Write the HTCondor prescript script

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
        writer.rewrite(template, outputFileName, pairs)

    def writeJobScript(self, outputFileName, template, keywords, scriptName=None):
        """Write the HTCondor script that is used to execute the job

        Parameters
        ----------
        outputFileName : str
            output file name for pre script
        template : Config
            config file template
        keywords : { 'key1' : 'value', 'key2' : 'value2'}
            keyword/value dictionary
        scriptName : str, optional
            name of script to substitute in place of default
        """
        pairs = {}
        for value in keywords:
            val = keywords[value]
            pairs[value] = val
        if scriptName is not None:
            pairs["ORCA_SCRIPT"] = self.scriptDir + "/" + scriptName
        pairs["ORCA_RUNID"] = self.runid
        pairs["ORCA_DEFAULTROOT"] = self.defaultRoot
        writer = TemplateWriter()
        writer.rewrite(template, outputFileName, pairs)

    def writeGlideinFile(self, glideinConfig):
        """Write the HTCondor glide-in file

        Parameters
        ----------
        glideinConfig : Config
            config file used to write glide-in information
        """
        template = glideinConfig.template
        inputFile = EnvString.resolve(template.inputFile)

        # copy the keywords so we can add a couple more
        pairs = {}
        for value in template.keywords:
            val = template.keywords[value]
            pairs[value] = val
        pairs["ORCA_REMOTE_WORKDIR"] = self.defaultRoot + "/" + self.runid
        if "ORCA_START_OWNER" not in pairs:
            pairs["ORCA_START_OWNER"] = getpass.getuser()

        writer = TemplateWriter()
        writer.rewrite(inputFile, template.outputFile, pairs)

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
