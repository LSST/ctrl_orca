import lsst.pex.config as pexConfig

from . import DatabaseConfig as db  # noqa: N813
from . import FakeTypeMap as fake  # noqa: N813
from . import WorkflowConfig as work  # noqa: N813

# production level configuration


class ProductionLevelConfig(pexConfig.Config):
    # class that handles production level
    configurationClass = pexConfig.Field("configuration class", str)


# production information


class Production(pexConfig.Config):
    # name of the production
    shortName = pexConfig.Field("name of production", str)

    # repository directory location
    repositoryDirectory = pexConfig.Field("location of production repository", str)

    # config check
    configCheckCare = pexConfig.Field("config check", int, default=-1)

    # log level threshold
    logThreshold = pexConfig.Field("logging threshold", int)

    # production configuration class
    configuration = pexConfig.ConfigField(
        "production level config", ProductionLevelConfig
    )


# production configuration


class ProductionConfig(pexConfig.Config):
    # production configuration
    production = pexConfig.ConfigField("production configuration", Production)

    # database configuration
    database = pexConfig.ConfigChoiceField(
        "database information", fake.FakeTypeMap(db.DatabaseConfig)
    )

    # workflow configuration
    workflow = pexConfig.ConfigChoiceField(
        "workflow", fake.FakeTypeMap(work.WorkflowConfig)
    )

    # config check
    configCheckCare = pexConfig.Field("config check care", int, default=-1)

    # class that handles production configuration
    configurationClass = pexConfig.Field("configuration class", str)
