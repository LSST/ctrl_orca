import os, os.path, shutil, sets, stat
import lsst.ctrl.orca as orca
import lsst.pex.policy as pol

from lsst.ctrl.orca.Directories import Directories
from lsst.pex.logging import Log

from lsst.ctrl.orca.EnvString import EnvString
from lsst.ctrl.orca.PipelineConfigurator import PipelineConfigurator
from lsst.ctrl.orca.BasicPipelineLauncher import BasicPipelineLauncher

##
#
# BasicPipelineConfigurator 
#
class BasicPipelineConfigurator(PipelineConfigurator):
    def __init__(self, runid, logger, verbosity):
        self.runid = runid
        self.logger = logger
        self.logger.log(Log.DEBUG, "BasicPipelineConfigurator:__init__")
        self.verbosity = verbosity

        self.nodes = None
        self.dirs = None
        self.policySet = sets.Set()


    ##
    # @brief Setup as much as possible in preparation to execute the pipeline
    #            and return a PipelineLauncher object that will launch the
    #            configured pipeline.
    # @param policy the pipeline policy to use for configuration
    # @param configurationDict a dictionary containing configuration info
    # @param provenanceDict a dictionary containing info to record provenance
    # @param repository policy file repository location
    #
    def configure(self, policy, configurationDict, provenanceDict, repository):
        self.logger.log(Log.DEBUG, "BasicPipelineConfigurator:configure")
        self.policy = policy
        self.configurationDict = configurationDict
        self.provenanceDict = provenanceDict
        self.repository = repository
        self.pipeline = self.policy.get("shortName")
        self.nodes = self.createNodeList()
        self.prepPlatform()
        self.deploySetup()
        self.setupDatabase()
        cmd = self.createLaunchCommand()
        pipelineLauncher = BasicPipelineLauncher(cmd, self.pipeline, self.logger)
        return pipelineLauncher

    ##
    # @brief create the command which will launch the pipeline
    # @return a string containing the shell commands to execute
    #
    def createLaunchCommand(self):
        self.logger.log(Log.DEBUG, "BasicPipelineConfigurator:createLaunchCommand")

        execPath = self.policy.get("configuration.framework.exec")
        launchcmd = EnvString.resolve(execPath)
        filename = self.configurationDict["filename"]
        #configurationPolicyFile =  os.path.join(self.dirs.get("work"), filename)
        #launchcmd =  os.path.join(self.dirs.get("work"), "orca_launch.sh")

        cmd = ["ssh", self.masterNode, "cd %s; source %s; %s %s %s -L %s" % (self.dirs.get("work"), self.script, launchcmd, filename, self.runid, self.verbosity) ]
        return cmd


    ##
    # @brief creates a list of nodes from platform.deploy.nodes
    # @return the list of nodes
    #
    def createNodeList(self):
        self.logger.log(Log.DEBUG, "BasicPipelineConfigurator:createNodeList")
        node = self.policy.getArray("platform.deploy.nodes")
        self.defaultDomain = self.policy.get("platform.deploy.defaultDomain")

        nodes = map(self.expandNodeHost, node)
        # by convention, the master node is the first node in the list
        # we use this later to launch things, so strip out the info past ":", if it's there.
        self.masterNode = nodes[0]
        colon = self.masterNode.find(':')
        if colon > 1:
            self.masterNode = self.masterNode[0:colon]
        return nodes

    def getPipelineName(self):
        return self.pipeline
    
    def getNodeCount(self):
        return len(self.nodes)

    ##
    # @brief prepare the platform by creating directories and writing the node list
    #
    def prepPlatform(self):
        self.logger.log(Log.DEBUG, "BasicPipelineConfigurator:prepPlatform")
        self.createDirs()

    ##
    # @brief write the node list to the "work" directory
    #
    def writeNodeList(self):
        
        # write this only for debug
        nodelist = open(os.path.join(self.dirs.get("work"), "nodelist.scr"), 'w')
        for node in self.nodes:
            print >> nodelist, node
        nodelist.close()

        p = pol.Policy()
        x = 0
        for node in self.nodes:
            p.set("node%d" % x, node)
            x = x + 1
        pw = pol.PAFWriter(os.path.join(self.dirs.get("work"), "nodelist.paf"))
        pw.write(p)
        pw.close()


    ##
    # @brief 
    #
    def deploySetup(self):
        self.logger.log(Log.DEBUG, "BasicPipelineConfigurator:deploySetup")

        # write the nodelist to "work"
        self.writeNodeList()

        # copy /bin/sh script responsible for environment setting

        setupPath = self.policy.get("configuration.framework.environment")
        if setupPath == None:
             raise RuntimeError("couldn't find configuration.framework.environment")
        self.script = EnvString.resolve(setupPath)

        if orca.envscript == None:
            print "using default setup.sh"
        else:
            self.script = orca.envscript

        shutil.copy(self.script, self.dirs.get("work"))

        # now point at the new location for the setup script
        self.script = os.path.join(self.dirs.get("work"),os.path.basename(self.script))

        # This policy has the override values, but must be written out and
        # recorded.
        #  write file to self.dirs["work"]
        #  call provenance.recordPolicy()
        # 
        # copy the policies to the working directory
        
        configurationFileName = self.configurationDict["filename"]
        
        configurationPolicy = self.configurationDict["policy"]
        newPolicyFile = os.path.join(self.dirs.get("work"), configurationFileName)
        if os.path.exists(newPolicyFile):
            self.logger.log(Log.WARN, "Working directory already contains %s")
        else:
            pw = pol.PAFWriter(newPolicyFile)
            pw.write(configurationPolicy)
            pw.close()

        # TODO: Provenance script needs to write out newPolicyFile
        #self.provenance.recordPolicy(newPolicyFile)
        self.policySet.add(newPolicyFile)

        # TODO: cont'd - also needs to writeout child policies
        newPolicyObj = pol.Policy.createPolicy(newPolicyFile, False)
        pipelinePolicySet = sets.Set()
        self.extractChildPolicies(self.repository, newPolicyObj, pipelinePolicySet)

        if os.path.exists(os.path.join(self.dirs.get("work"), self.pipeline)):
            self.logger.log(Log.WARN,
              "Working directory already contains %s directory; won't overwrite" % self.pipeline)
        else:
            #shutil.copytree(os.path.join(self.repository, self.pipeline), os.path.join(self.dirs.get("work"),self.pipeline))
            #
            # instead of blindly copying the whole directory, take the set
            # if files from policySet and copy those.
            #
            # This is slightly tricky, because we want to copy from the policy file     
            # repository directory to the "work" directory, but we also want to keep    
            # that partial directory hierarchy we're copying to as well.
            #
            for filename  in pipelinePolicySet:
                destinationDir = self.dirs.get("work")
                destName = filename.replace(self.repository+"/","")
                tokens = destName.split('/')
                tokensLength = len(tokens)
                # if the destination directory heirarchy doesn't exist, create all          
                # the missing directories
                destinationFile = tokens[len(tokens)-1]
                for newDestinationDir in tokens[:len(tokens)-1]:
                    newDir = os.path.join(destinationDir, newDestinationDir)
                    if os.path.exists(newDir) == False:
                        os.mkdir(newDir)
                    destinationDir = newDir
                shutil.copyfile(filename, os.path.join(destinationDir, destinationFile))

        self.writeLaunchScript()

    ##
    # @brief write a shell script to launch a pipeline
    #
    def writeLaunchScript(self):
        # write out the script we use to kick things off
        name = os.path.join(self.dirs.get("work"), "orca_launch.sh")

        user = self.provenanceDict["user"]
        runid = self.provenanceDict["runid"]
        dbrun = self.provenanceDict["dbrun"]
        dbglobal = self.provenanceDict["dbglobal"]
        repos = self.provenanceDict["repos"]

        filename = os.path.join(self.dirs.get("work"), self.configurationDict["filename"])

        s = "ProvenanceRecorder.py --type=%s --user=%s --runid=%s --dbrun=%s --dbglobal=%s --filename=%s --repos=%s\n" % ("lsst.ctrl.orca.provenance.BasicRecorder", user, runid, dbrun, dbglobal, filename, repos)

        launcher = open(name, 'w')
        launcher.write("#!/bin/sh\n")

        launcher.write("echo $PATH >path.txt\n")
        launcher.write("eups list 2>/dev/null | grep Setup >eups-env.txt\n")
        launcher.write("pipeline=`echo ${1} | sed -e 's/\..*$//'`\n")
        launcher.write(s)
        launcher.write("#$CTRL_ORCA_DIR/bin/writeNodeList.py %s nodelist.paf\n" % self.dirs.get("work"))
        launcher.write("nohup $PEX_HARNESS_DIR/bin/launchPipeline.py $* > ${pipeline}-${2}.log 2>&1  &\n")
        launcher.close()
        # make it executable
        os.chmod(name, stat.S_IRWXU)
        return

    ##
    # @brief create the platform.dir directories
    #
    def createDirs(self):
        self.logger.log(Log.DEBUG, "BasicPipelineConfigurator:createDirs")

        dirPolicy = self.policy.getPolicy("platform.dir")
        directories = Directories(dirPolicy, self.pipeline, self.runid)
        self.dirs = directories.getDirs()

        for name in self.dirs.names():
            if not os.path.exists(self.dirs.get(name)): os.makedirs(self.dirs.get(name))

    ##
    # @brief set up this pipeline's database
    #
    def setupDatabase(self):
        self.logger.log(Log.DEBUG, "BasicPipelineConfigurator:setupDatabase")

    ##
    # @brief perform a node host name expansion
    #
    def expandNodeHost(self, nodeentry):
        """Add a default network domain to a node list entry if necessary """

        if nodeentry.find(".") < 0:
            node = nodeentry
            colon = nodeentry.find(":")
            if colon == 0:
                raise RuntimeError("bad nodelist format: " + nodeentry)
            elif colon > 0:
                node = nodeentry[0:colon]
                if len(node) < 3:
                    #logger.log(Log.WARN, "Suspiciously short node name: " + node)
                    self.logger.log(Log.DEBUG, "Suspiciously short node name: " + node)
                self.logger.log(Log.DEBUG, "-> nodeentry  =" + nodeentry)
                self.logger.log(Log.DEBUG, "-> node  =" + node)

                if self.defaultDomain is not None:
                    node += "."+self.defaultDomain
                nodeentry = "%s:%s" % (node, nodeentry[colon+1:])
            else:
                if self.defaultDomain is not None:
                    nodeentry = "%s%s:1" % (node, self.defaultDomain)
                else:
                    nodeentry = "%s:1" % node
        return nodeentry
        
    ##
    # @brief given a policy, recursively add all child policies to a policy set
    # 
    def extractChildPolicies(self, repos, policy, pipelinePolicySet):
        names = policy.fileNames()
        for name in names:
            if name.rfind('.') > 0:
                desc = name[0:name.rfind('.')]
                field = name[name.rfind('.')+1:]
                policyObjs = policy.getPolicyArray(desc)
                for policyObj in policyObjs:
                    if policyObj.getValueType(field) == pol.Policy.FILE:
                        filename = policyObj.getFile(field).getPath()
                        filename = os.path.join(repos, filename)
                        if (filename in self.policySet) == False:
                            #self.provenance.recordPolicy(filename)
                            self.policySet.add(filename)
                        if (filename in pipelinePolicySet) == False:
                            pipelinePolicySet.add(filename)
                        newPolicy = pol.Policy.createPolicy(filename, False)
                        self.extractChildPolicies(repos, newPolicy, pipelinePolicySet)
            else:
                field = name
                if policy.getValueType(field) == pol.Policy.FILE:
                    filename = policy.getFile(field).getPath()
                    filename = policy.getFile(field).getPath()
                    filename = os.path.join(repos, filename)
                    if (filename in self.policySet) == False:
                        #self.provenance.recordPolicy(filename)
                        self.policySet.add(filename)
                    if (filename in pipelinePolicySet) == False:
                        pipelinePolicySet.add(filename)
                    newPolicy = pol.Policy.createPolicy(filename, False)
                    self.extractChildPolicies(repos, newPolicy, pipelinePolicySet)
