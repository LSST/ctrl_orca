import lsst.pex.config as pexConfig

# from . import FakeTypeMap as fake
# from . import WorkflowConfig as work

# authorization information


class AuthInfo(pexConfig.Config):
    # host name
    host = pexConfig.Field("hostname", str)
    # port number
    port = pexConfig.Field("database port", int)


# run cleanup configuration


class RunCleanup(pexConfig.Config):
    # days until first notice is sent
    daysFirstNotice = pexConfig.Field("first notice", int)
    # days until final notice is sent
    daysFinalNotice = pexConfig.Field("last notice", int)


# database system configuration


class DatabaseSystem(pexConfig.Config):
    # authorization configuration
    authInfo = pexConfig.ConfigField("database authorization information", AuthInfo)
    # run clean up configuration
    runCleanup = pexConfig.ConfigField("runCleanup ", RunCleanup)


# production database configuration


class ProductionDatabaseConfig(pexConfig.Config):
    # global database name
    globalDbName = pexConfig.Field("global db name", str)


# workflow database configuration


class WorkflowDatabaseConfig(pexConfig.Config):
    # workflow database name
    dbName = pexConfig.Field("database name", str)


dbTypemap = {"production": ProductionDatabaseConfig, "workflow": WorkflowDatabaseConfig}

# database configuration


class DatabaseConfig(pexConfig.Config):
    # database name
    name = pexConfig.Field("database name", str)
    # database system configuration
    system = pexConfig.ConfigField("database system info", DatabaseSystem)
    # class used to configure database
    configurationClass = pexConfig.Field("database configuration class", str)
    # type of database configuration
    configuration = pexConfig.ConfigChoiceField("configuration", dbTypemap)
