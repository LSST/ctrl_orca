import lsst.pex.config as pexConfig
from lsst.ctrl.orca.config.DirectoryConfig import DirectoryConfig

# hardware configuration


class HwConfig(pexConfig.Config):
    # number of nodes requested
    nodeCount = pexConfig.Field("number of nodes", int)
    # minimum number of cores per node
    minCoresPerNode = pexConfig.Field("minimum cores per node", int)
    # maximum number of cores per node
    maxCoresPerNode = pexConfig.Field("maximum cores per node", int)
    # minimum ram used per node
    minRamPerNode = pexConfig.Field("minimum RAM per node", float)
    # maximum ram used node
    maxRamPerNode = pexConfig.Field("maximum RAM per node", float)


# deployment configuration


class DeployConfig(pexConfig.Config):
    # domain name of nodes in this deployment
    defaultDomain = pexConfig.Field("default internet domain", str)
    # node names requested
    nodes = pexConfig.ListField("node names", str)


# platform configuration


class PlatformConfig(pexConfig.Config):
    # directory configuration
    dir = pexConfig.ConfigField("directory info", DirectoryConfig)
    # hardware configuration
    hw = pexConfig.ConfigField("hardware info", HwConfig)
    # deployment configuration
    deploy = pexConfig.ConfigField("deploy", DeployConfig)
