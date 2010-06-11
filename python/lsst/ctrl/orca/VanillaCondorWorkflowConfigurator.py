import sys, os, os.path, shutil, sets, stat, socket
import lsst.ctrl.orca as orca
import lsst.pex.policy as pol

from lsst.pex.harness.Directories import Directories
from lsst.pex.logging import Log

from lsst.ctrl.orca.EnvString import EnvString
from lsst.ctrl.orca.PolicyUtils import PolicyUtils
from lsst.ctrl.orca.WorkflowConfigurator import WorkflowConfigurator
from lsst.ctrl.orca.VanillaCondorWorkflowLauncher import VanillaCondorWorkflowLauncher
from lsst.ctrl.orca.TemplateWriter import TemplateWriter
from lsst.ctrl.orca.FileWaiter import FileWaiter

##
#
# VanillaCondorWorkflowConfigurator 
#
class VanillaCondorWorkflowConfigurator(WorkflowConfigurator):
    def __init__(self, runid, prodPolicy, wfPolicy, logger):
        self.logger = logger
        self.logger.log(Log.DEBUG, "VanillaCondorWorkflowConfigurator:__init__")

        self.runid = runid
        self.prodPolicy = prodPolicy
        self.wfPolicy = wfPolicy

        self.wfVerbosity = None

        self.dirs = None
        self.directories = None
        self.nodes = None
        self.numNodes = None
        self.logFileNames = []

    ##
    # @brief Setup as much as possible in preparation to execute the workflow
    #            and return a WorkflowLauncher object that will launch the
    #            configured workflow.
    # @param provSetup
    # @param wfVerbosity
    #
    def configure(self, provSetup, wfVerbosity):
        self.wfVerbosity = wfVerbosity
        self._configureDatabases(provSetup)
        return self._configureSpecialized(provSetup, self.wfPolicy)

    ##
    # @brief Setup as much as possible in preparation to execute the workflow
    #            and return a WorkflowLauncher object that will launch the
    #            configured workflow.
    # @param policy the workflow policy to use for configuration
    # @param configurationDict a dictionary containing configuration info
    # @param provenanceDict a dictionary containing info to record provenance
    # @param repository policy file repository location
    #
    def _configureSpecialized(self, provSetup, wfPolicy):
        self.logger.log(Log.DEBUG, "VanillaCondorWorkflowConfigurator:configure")

        self.remoteLoginName = wfPolicy.get("configuration.condorData.loginNode")
        self.remoteFTPName = wfPolicy.get("configuration.condorData.ftpNode")
        self.transferProtocolPrefix = wfPolicy.get("configuration.condorData.transferProtocol")+"://"+self.remoteFTPName
        self.localScratch = wfPolicy.get("configuration.condorData.localScratch")

        if wfPolicy.getValueType("platform") == pol.Policy.FILE:
            filename = wfPolicy.getFile("platform").getPath()
            platformPolicy = pol.Policy.createPolicy(filename)
        else:
            platformPolicy = wfPolicy.getPolicy("platform")

        self.repository = self.prodPolicy.get("repositoryDirectory")
        self.repository = EnvString.resolve(self.repository)

        self.shortName = self.wfPolicy.get("shortName")

        pipelinePolicies = wfPolicy.getPolicyArray("pipeline")
        expandedPipelinePolicies = self.expandPolicies(self.shortName, pipelinePolicies)

        jobs = []
        for pipelinePolicyGroup in expandedPipelinePolicies:
            pipelinePolicy = pipelinePolicyGroup[0]
            num = pipelinePolicyGroup[1]
            self.createDirs(platformPolicy, pipelinePolicy)

            pipelineShortName = pipelinePolicy.get("shortName")
            launchName = "%s_%d" % (pipelineShortName, num)

            self.logger.log(Log.DEBUG, "VanillaCondorWorkflowConfigurator: launchName = %s" % launchName)
            #launchCmd = self.deploySetup(pipelinePolicy)
            self.deploySetup(provSetup, wfPolicy, platformPolicy, pipelinePolicyGroup)
            condorFile = self.writeCondorFile(launchName, "launch_%s.sh" % launchName)
            launchCmd = ["condor_submit", condorFile]
            jobs.append(condorFile)
            self.setupDatabase()
            # copy the $CTRL_ORCA_DIR/etc/condor_glidein_config to local
            condorGlideinConfig = EnvString.resolve("$CTRL_ORCA_DIR/etc/glidein_condor_config")
            condorDir = os.path.join(self.localWorkDir,"Condor_glidein")
            stagedGlideinConfigFile = os.path.join(condorDir, "glidein_condor_config")

            keyvalues = pol.Policy()
            keyvalues.set("ORCA_LOCAL_HOSTNAME", socket.gethostname())
            
            writer = TemplateWriter()
            writer.rewrite(condorGlideinConfig, stagedGlideinConfigFile, keyvalues)
            
        self.logger.log(Log.DEBUG, "launchCmd = %s" % launchCmd)

        # after all the pipelines are created, copy them to the remote location
        # all at once.
        remoteDir = os.path.join(self.directories.getDefaultRootDir(), self.runid)
        # the extra "/" is required below to copy the entire directory
        self.copyToRemote(self.localStagingDir+"/", remoteDir+"/")

        self.runLinkScript(wfPolicy)

        # make remote scripts executable;  this is required because the copy doesn't
        # retain the execution bit setting.
        for pipelinePolicyGroup in expandedPipelinePolicies:
            pipelinePolicy = pipelinePolicyGroup[0]
            num = pipelinePolicyGroup[1]

            pipelineShortName = pipelinePolicy.get("shortName")

            filename = "launch_%s_%d.sh" % (pipelineShortName, num)
            remoteDir = os.path.join(self.dirs.get("work"), "%s_%d" % (pipelineShortName, num))
            remoteFilename = os.path.join(remoteDir, filename)
            self.remoteChmodX(remoteFilename)
        

        # copy the file creation watching utility

        remoteFileWaiterName = self.copyFileWaiterUtility()
        fileWaiter = FileWaiter(self.remoteLoginName, remoteFileWaiterName, self.logFileNames, self.logger)
        
        # TODO: get script from template, write it, and pass it to the Launcher

        glideinFileName = self.writeGlideinRequest(wfPolicy.get("configuration"))

        #

        workflowLauncher = VanillaCondorWorkflowLauncher(jobs, self.localWorkDir, glideinFileName,  self.prodPolicy, self.wfPolicy, self.runid, fileWaiter, self.logger)
        return workflowLauncher

    ##
    # @brief create the command which will launch the workflow
    # @return a string containing the shell commands to execute
    #
    def writeCondorFile(self, launchNamePrefix, launchScriptName):
        self.logger.log(Log.DEBUG, "VanillaCondorWorkflowConfigurator:writeCondorFile")

        # The name "work" should be the suffix of the self.dirs.get("work") portion of the name.  We can't guarantee the name
        # of the directory is "work".
        #condorJobFile = os.path.join(self.localStagingDir, "work")
        #workDirSuffix = self.dirs.get("work")[len(self.directories.getDefaultRunDir()):]
        #workDirSuffix = workDirSuffix.lstrip("/")
        #workDir = os.path.join(self.localStagingDir, workDirSuffix)
        condorJobFile = os.path.join(self.localWorkDir, launchNamePrefix)
        condorJobFile = os.path.join(condorJobFile, launchNamePrefix+".condor")

        clist = []
        clist.append("universe=vanilla\n")
        clist.append("executable=%s/%s\n" % (launchNamePrefix, launchScriptName))
        clist.append("transfer_executable=false\n")
        clist.append("output=%s/%s/Condor.out\n" % (self.localWorkDir, launchNamePrefix))
        clist.append("error=%s/%s/Condor.err\n" % (self.localWorkDir, launchNamePrefix))
        clist.append("log=%s/%s/Condor.log\n" % (self.localWorkDir, launchNamePrefix))
        clist.append("should_transfer_files = YES\n")
        clist.append("when_to_transfer_output = ON_EXIT\n")
        clist.append("remote_initialdir="+self.dirs.get("work")+"\n")
        clist.append("Requirements = (FileSystemDomain != \"dummy\") && (Arch != \"dummy\") && (OpSys != \"dummy\") && (Disk != -1) && (Memory != -1)\n")
        clist.append("queue\n")

        # Create a file object: in "write" mode
        condorFILE = open(condorJobFile,"w")
        condorFILE.writelines(clist)
        condorFILE.close()

        return condorJobFile

    def getWorkflowName(self):
        return self.shortName

    
    def stageLocally(self, localName, remoteName):
        self.logger.log(Log.DEBUG, "VanillaCondorWorkflowConfigurator:stageLocally")

        print "local name  = "+localName
        print "remote name  = "+remoteName

        localStageName = os.path.join(self.localStagingDir, remoteName)

        print "localName = %s, localStageName = %s\n",(localName,localStageName)
        if os.path.exists(os.path.dirname(localStageName)) == False:
            os.makedirs(os.path.dirname(localStageName))
        shutil.copyfile(localName, localStageName)

    def copyToRemote(self, localName, remoteName):
        self.logger.log(Log.DEBUG, "VanillaCondorWorkflowConfigurator:copyToRemote")
        
        localNameURL = "%s%s" % ("file://",localName)
        remoteNameURL = "%s%s" % (self.transferProtocolPrefix, remoteName)

        cmd = "globus-url-copy -r -vb -cd %s %s " % (localNameURL, remoteNameURL)
        
        # perform this copy from the local machine to the remote machine
        pid = os.fork()
        if not pid:
            # when forking stuff, gotta close *BOTH* the python and C level 
            # file descriptors. not strictly needed here, since we're just
            # shutting off stdout and stderr, but a good habit to be in.

            # TODO: Change this to add a check to not close file descriptors
            # if verbosity is set high enough, so you can see the output of the 
            # globus-url-copy
            sys.stdin.close()
            sys.stdout.close()
            sys.stderr.close()
            os.close(0)
            os.close(1)
            os.close(2)
            os.execvp("globus-url-copy",cmd.split())
        os.wait()[0]

    def remoteChmodX(self, remoteName):
        self.logger.log(Log.DEBUG, "VanillaCondorWorkflowConfigurator:remoteChmodX")
        cmd = "gsissh %s chmod +x %s" % (self.remoteLoginName, remoteName)
        pid = os.fork()
        if not pid:
            os.execvp("gsissh",cmd.split())
        os.wait()[0]

    def copyFileWaiterUtility(self):
        script = EnvString.resolve("$CTRL_ORCA_DIR/bin/filewaiter.py")
        remoteName = os.path.join(self.dirs.get("work"), os.path.basename(script))
        self.copyToRemote(script, remoteName)
        self.remoteChmodX(remoteName)
        return remoteName

    def remoteMkdir(self, remoteDir):
        self.logger.log(Log.DEBUG, "VanillaCondorWorkflowConfigurator:remoteMkdir")
        cmd = "gsissh %s mkdir -p %s" % (self.remoteLoginName, remoteDir)
        print "running: "+cmd
        pid = os.fork()
        if not pid:
            os.execvp("gsissh",cmd.split())
        os.wait()[0]
    ##
    # @brief 
    #
    def deploySetup(self, provSetup, wfPolicy, platformPolicy, pipelinePolicyGroup):
        self.logger.log(Log.DEBUG, "VanillaCondorWorkflowConfigurator:deploySetup")

        pipelinePolicy = pipelinePolicyGroup[0]
        shortName = pipelinePolicy.get("shortName")

        pipelinePolicyNumber = pipelinePolicyGroup[1]
        pipelineName = "%s_%d" % (shortName, pipelinePolicyNumber)

        globalPipelineOffset = pipelinePolicyGroup[2]
        # add things to the pipeline policy and write it out to "work"
        #self.rewritePipelinePolicy(pipelinePolicy)

        #workDirSuffix = self.dirs.get("work")[len(self.directories.getDefaultRunDir()):]
        #print "self.directories.getDefaultRunDir() = %s" % self.directories.getDefaultRunDir()
        #print 'self.dirs.get("work") = %s' % self.dirs.get("work")
        #print "workDirSuffix = %s" % workDirSuffix
        #workDirSuffix = workDirSuffix.lstrip("/")
        #workDir = os.path.join(self.localStagingDir, workDirSuffix)
        #print "localStagingDir = %s" % self.localStagingDir
        #print "workDir = %s" % workDir

        # create the subdirectory for the pipeline specific files
        #logDir = os.path.join(self.dirs.get("work"), pipelineName)
        logDir = os.path.join(self.localWorkDir, pipelineName)
        if not os.path.exists(logDir):
            os.makedirs(logDir)
            logFile = os.path.join(pipelineName, "launch.log")
            logFile = os.path.join(self.dirs.get("work"), logFile)
            self.logFileNames.append(logFile)

        
        # only write out the policyfile once
        filename = pipelinePolicy.getFile("definition").getPath()
        definitionPolicy = pol.Policy.createPolicy(filename, False)
        if pipelinePolicyNumber == 1:
            if platformPolicy.exists("dir"):
                definitionPolicy.set("execute.dir", platformPolicy.get("dir"))
            if self.prodPolicy.exists("eventBrokerHost"):
                definitionPolicy.set("execute.eventBrokerHost", self.prodPolicy.get("eventBrokerHost"))
    
            if self.wfPolicy.exists("shutdownTopic"):
                definitionPolicy.set("execute.shutdownTopic", self.wfPolicy.get("shutdownTopic"))
            if self.prodPolicy.exists("logThreshold"):
                definitionPolicy.set("execute.logThreshold", self.prodPolicy.get("logThreshold"))
            newPolicyFile = os.path.join(self.localWorkDir, filename)
            pw = pol.PAFWriter(newPolicyFile)
            pw.write(definitionPolicy)
            pw.close()

        # write the nodelist to "work"
        #self.writeNodeList(logDir)

        # copy /bin/sh script responsible for environment setting

        setupPath = definitionPolicy.get("framework.environment")
        if setupPath == None:
             raise RuntimeError("couldn't find framework.environment")
        #self.script = EnvString.resolve(setupPath)
        self.script = setupPath

        if orca.envscript == None:
            print "using default setup.sh"
        else:
            self.script = orca.envscript

        # only copy the setup script once
        if pipelinePolicyNumber == 1:
            shutil.copy(self.script, self.localWorkDir)

        # now point at the new location for the setup script
        self.script = os.path.join(self.dirs.get("work"), os.path.basename(self.script))

        #
        # Write all policy files out to the work directory, 
        # but only do it once.
        
        if pipelinePolicyNumber == 1:
        
            # first, grab all the file names, and throw them into a Set() to 
            # avoid duplication
            pipelinePolicySet = sets.Set()
            repos = self.prodPolicy.get("repositoryDirectory")
            PolicyUtils.getAllFilenames(repos, definitionPolicy, pipelinePolicySet)

            # Cycle through the file names, creating subdirectories as required,
            # and copy them to the destination directory
            for policyFile in pipelinePolicySet:
                destName = policyFile.replace(repos+"/","")
                tokens = destName.split('/')
                tokensLength = len(tokens)
                destinationFile = tokens[len(tokens)-1]
                destintationDir = self.localWorkDir
                for newDestinationDir in tokens[:len(tokens)-1]:
                    newDir = os.path.join(self.localWorkDir, newDestinationDir)
                    if os.path.exists(newDir) == False:
                        os.mkdir(newDir)
                    destinationDir = newDir
                shutil.copyfile(policyFile, os.path.join(destinationDir, destinationFile))

        # create the launch command
        execPath = definitionPolicy.get("framework.exec")
        #execCmd = EnvString.resolve(execPath)
        execCmd = execPath

        #cmd = ["ssh", self.masterNode, "cd %s; source %s; %s %s %s -L %s" % (self.dirs.get("work"), self.script, execCmd, filename, self.runid, self.wfVerbosity) ]

        # write out the launch script
        # write out the script we use to kick things off
        launchName = "launch_%s.sh" % pipelineName

        name = os.path.join(logDir, launchName)


        launcher = open(name, 'w')
        launcher.write("#!/bin/sh\n")
        launcher.write("export SHELL=/bin/sh\n")
        launcher.write("cd %s\n" % self.dirs.get("work"))
        launcher.write("source %s\n" % self.script)
        remoteLogDir = os.path.join(self.dirs.get("work"), pipelineName)
        launcher.write("eups list 2>/dev/null | grep Setup >%s/eups-env.txt\n" % remoteLogDir)

        cmds = provSetup.getCmds()
        workflowPolicies = self.prodPolicy.getArray("workflow")

        repos = self.prodPolicy.get("repositoryDirectory")
        # append the other information we previously didn't have access to, but need for recording.
        for cmd in cmds:
            wfShortName = wfPolicy.get("shortName")
            cmd.append("--activityname=%s_%s" % (wfShortName, pipelineName))
            cmd.append("--platform=%s" % wfPolicy.get("platform").getPath())
            cmd.append("--localrepos=%s" % self.dirs.get("work"))
            workflowIndex = 1
            for wfPolicy in workflowPolicies:
                if wfPolicy.get("shortName") == wfShortName:
                    #cmd.append("--activoffset=%s" % workflowIndex)
                    cmd.append("--activoffset=%s" % globalPipelineOffset)
                    break
                workflowIndex = workflowIndex + 1
            launchCmd = ' '.join(cmd)

            # extract the pipeline policy and all the files it includes, and add it to the command
            filelist = provSetup.extractSinglePipelineFileNames(pipelinePolicy, repos, self.logger)
            fileargs = ' '.join(filelist)
            launcher.write("%s %s\n" % (launchCmd, fileargs))

        
        # On condor, you have to launch the script, then wait until that
        # script exits.
        launcher.write("%s %s %s -L %s --logdir %s >%s/launch.log 2>&1 &\n" % (execCmd, filename, self.runid, self.wfVerbosity, remoteLogDir, remoteLogDir))
        launcher.write("wait\n")
        launcher.write('echo "from launcher"\n')
        launcher.write("ps -ef\n")

        launcher.close()

        return

    def rewritePipelinePolicy(self, pipelinePolicy):
        #workDirSuffix = self.dirs.get("work")[len(self.dirs.getDefaultRunDir()):]
        #localWorkDir = os.path.join(self.localStagingDir, workDirSuffix)
        
        filename = pipelinePolicy.getFile("definition").getPath()
        oldPolicy = pol.Policy.createPolicy(filename, False)

        if self.prodPolicy.exists("eventBrokerHost"):
            oldPolicy.set("execute.eventBrokerHost", self.prodPolicy.get("eventBrokerHost"))

        if self.prodPolicy.exists("shutdownTopic"):
            oldPolicy.set("execute.shutdownTopic", self.prodPolicy.get("shutdownTopic"))

        if self.prodPolicy.exists("logThreshold"):
            oldPolicy.set("execute.logThreshold", self.prodPolicy.get("logThreshold"))

        newPolicyFile = os.path.join(self.localWorkDir, filename)
        pw = pol.PAFWriter(newPolicyFile)
        pw.write(oldPolicy)
        pw.close()

    ##
    # @brief create the platform.dir directories
    #
    def createDirs(self, platformPolicy, pipelinePolicy):
        self.logger.log(Log.DEBUG, "VanillaCondorWorkflowConfigurator:createDirs")

        dirPolicy = platformPolicy.getPolicy("dir")
        dirName = pipelinePolicy.get("shortName")
        self.directories = Directories(dirPolicy, dirName, self.runid)
        self.dirs = self.directories.getDirs()

        remoteRootDir = self.directories.getDefaultRootDir()
        remoteRunDir = self.directories.getDefaultRunDir()
        suffix = remoteRunDir.split(remoteRootDir)
        self.localStagingDir = os.path.join(self.localScratch, suffix[1][1:])

        workDirSuffix = self.dirs.get("work")[len(self.directories.getDefaultRunDir()):]
        workDirSuffix = workDirSuffix.lstrip("/")
        self.localWorkDir = os.path.join(self.localStagingDir, workDirSuffix)

        for name in self.dirs.names():
            localDirName = os.path.join(self.localStagingDir, name)
    
            if not os.path.exists(localDirName):
                os.makedirs(localDirName)

        # create Condor_glidein/local directory under "work"
        condorDir = os.path.join(self.localWorkDir,"Condor_glidein")
        condorLocalDir = os.path.join(condorDir, "local")
        if not os.path.exists(condorLocalDir):
            os.makedirs(condorLocalDir)

    ##
    # @brief set up this workflow's database
    #
    def setupDatabase(self):
        self.logger.log(Log.DEBUG, "VanillaCondorWorkflowConfigurator:setupDatabase")


    def runLinkScript(self, wfPolicy):
        self.logger.log(Log.DEBUG, "VanillaPipelineWorkflowConfigurator:runLinkScript")

        if wfPolicy.exists("configuration"):
            configuration = wfPolicy.get("configuration")
            if configuration.exists("deployData"):
                deployPolicy = configuration.get("deployData")
                dataRepository = deployPolicy.get("dataRepository")
                dataRepository = EnvString.resolve(dataRepository)
                deployScript = deployPolicy.get("script")
                deployScript = EnvString.resolve(deployScript)
                collection = deployPolicy.get("collection")


                if os.path.isfile(deployScript) == True:
                    # copy the script to the remote side
                    remoteName = os.path.join(self.dirs.get("work"), os.path.basename(deployScript))
                    self.copyToRemote(deployScript, remoteName)
                    self.remoteChmodX(remoteName)
                    runDir = self.directories.getDefaultRunDir()
                    # run the linking script
                    deployCmd = ["gsissh", self.remoteLoginName, remoteName, runDir, dataRepository, collection]
                    print ">>> ",deployCmd
                    pid = os.fork()
                    if not pid:
                        os.execvp(deployCmd[0], deployCmd)
                    os.wait()[0]
                else:
                    self.logger.log(Log.DEBUG, "GenericPipelineWorkflowConfigurator:deployData: warning: script '%s' doesn't exist" % deployScript)
        return

    def writeGlideinRequest(self, configPolicy):
        self.logger.log(Log.DEBUG, "VanillaPipelineWorkflowConfigurator:writeGlideinRequest")
        glideinRequest = configPolicy.get("glideinRequest")
        templateFileName = glideinRequest.get("templateFileName")
        templateFileName = EnvString.resolve(templateFileName)
        outputFileName = glideinRequest.get("outputFileName")
        keyValuePairs = glideinRequest.get("keyValuePairs")

        #workDirSuffix = self.dirs.get("work")[len(self.directories.getDefaultRunDir()):]
        #workDirSuffix = workDirSuffix.lstrip("/")
        #realOutputDir = os.path.join(self.localStagingDir, workDirSuffix)
        realFileName = os.path.join(self.localWorkDir, outputFileName)

        # for glidein request, we add this additional keyword.
        keyValuePairs.set("ORCA_REMOTE_WORKDIR", self.dirs.get("work"))

        writer = TemplateWriter()
        writer.rewrite(templateFileName, realFileName, keyValuePairs)

        return realFileName
