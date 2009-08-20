import subprocess
from lsst.pex.logging import Log
from lsst.ctrl.orca.EnvString import EnvString
from lsst.ctrl.orca.PipelineMonitor import PipelineMonitor

class PipelineLauncher:
    def __init__(self, runid, policy, pipeline, masterNode, logger, verbosity):
        self.logger = logger
        self.logger.log(Log.DEBUG, "PipelineLauncher:__init__")
        self.runid = runid
        self.pipeline = pipeline
        self.policy = policy
        self.masterNode = masterNode
        self.pipelineVerbosity = verbosity

    def launch(self):
        self.logger.log(Log.DEBUG, "PipelineLauncher:launch")

        self.pipelineMonitor = PipelineMonitor(self.logger)
        return self.pipelineMonitor # returns PipelineMonitor

    def cleanUp(self):
        self.logger.log(Log.DEBUG, "PipelineLauncher:cleanUp")

    def checkConfiguration(self, care):
        # the level of care taken in the checks.  In general, the higher
        # the number of checks that will be done.
        self.logger.log(Log.DEBUG, "PipelineLauncher:checkConfiguration")
