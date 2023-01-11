import lsst.pex.config as pexConfig

from . import CondorWorkflowConfig as condor  # noqa: N813
from . import DatabaseConfig as data  # noqa: N813
from . import FakeTypeMap as fake  # noqa: N813
from . import MonitorConfig as mon  # noqa: N813
from . import PlatformConfig as plat  # noqa: N813
from . import TaskConfig as task  # noqa: N813

typemap = {
    "condor": condor.CondorWorkflowConfig,
    "pegasus": condor.CondorWorkflowConfig,
}

#
# definition of a workflow


class WorkflowConfig(pexConfig.Config):
    # name of this workflow
    shortName = pexConfig.Field("name of this workflow", str)

    # platform configuration file
    platform = pexConfig.ConfigField("platform configuration file", plat.PlatformConfig)

    # plugin type
    configurationType = pexConfig.Field("plugin type", str)

    # plugin class name
    configurationClass = pexConfig.Field("orca plugin class", str)

    # configuration
    configuration = pexConfig.ConfigChoiceField("configuration", typemap)

    # this usually isn't used, but is here because the design calls for this
    # possibility.
    # database name
    database = pexConfig.ConfigChoiceField(
        "database", fake.FakeTypeMap(data.DatabaseConfig)
    )

    # task
    task = pexConfig.ConfigChoiceField("task", fake.FakeTypeMap(task.TaskConfig))

    # monitor configuration
    monitor = pexConfig.ConfigField("monitor configuration", mon.MonitorConfig)
