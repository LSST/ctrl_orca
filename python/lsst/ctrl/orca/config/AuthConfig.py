import lsst.pex.config as pexConfig

from . import FakeTypeMap as fake  # noqa: N813

# authorization


class AuthInfoConfig(pexConfig.Config):
    # host name
    host = pexConfig.Field("host", str)
    # user name
    user = pexConfig.Field("user", str)
    # password
    password = pexConfig.Field("password", str)
    # port number
    port = pexConfig.Field("port", int)


# database authorization


class AuthDatabaseConfig(pexConfig.Config):
    # authorization configuration
    authInfo = pexConfig.ConfigChoiceField(
        "auth info", fake.FakeTypeMap(AuthInfoConfig)
    )


# general authorization
class AuthConfig(pexConfig.Config):
    # authorization database configuration
    database = pexConfig.ConfigField("root", AuthDatabaseConfig)
