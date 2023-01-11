import lsst.pex.config as pexConfig

# script template


class ScriptTemplateConfig(pexConfig.Config):
    # input file
    inputFile = pexConfig.Field("input file", str)
    # key value pars to substitute for the template
    keywords = pexConfig.DictField(
        "key value pairs", keytype=str, itemtype=str, default=dict()
    )
    # output file for results of template substitution
    outputFile = pexConfig.Field("output file", str)


# job template
class JobTemplateConfig(pexConfig.Config):
    # job script template configuration
    script = pexConfig.ConfigField("job script", ScriptTemplateConfig)
    # condor template configuration
    condor = pexConfig.ConfigField("template", ScriptTemplateConfig)


# script


class ScriptConfig(pexConfig.Config):
    # job script template
    script = pexConfig.ConfigField("job script", ScriptTemplateConfig)


# DAG generation script


class DagGeneratorConfig(pexConfig.Config):
    # DAG name
    dagName = pexConfig.Field("dag name", str)
    # script name
    script = pexConfig.Field("script", str)
    # input file
    inputFile = pexConfig.Field("input", str)
    # number of ids per job given to execute
    idsPerJob = pexConfig.Field("the number of ids that will be handled per job", int)


class SitesConfig(pexConfig.Config):
    inputFile = pexConfig.Field("input", str)
    outputFile = pexConfig.Field("output", str)
    keywords = pexConfig.DictField(
        "key value pairs", keytype=str, itemtype=str, default=dict()
    )


# DAX generation script


class DaxGeneratorConfig(pexConfig.Config):
    # DAG name
    daxName = pexConfig.Field("dax name", str)
    # script name
    script = pexConfig.Field("script", str)
    # input file
    inputFile = pexConfig.Field("input", str)
    # sites file
    sites = pexConfig.ConfigField("sites", SitesConfig)
    # transform file
    transformFile = pexConfig.Field("transform", str)


typemap = {"dag": DagGeneratorConfig, "dax": DaxGeneratorConfig}


# task
class TaskConfig(pexConfig.Config):
    # script directory
    scriptDir = pexConfig.Field("script directory", str)
    # pre script  (run before any jobs)
    preScript = pexConfig.ConfigField("pre script", ScriptConfig)
    # pre job script (run before each job)
    preJob = pexConfig.ConfigField("pre job", JobTemplateConfig)
    # post job script (run after each job)
    postJob = pexConfig.ConfigField("post job", JobTemplateConfig)
    # worker job configuration
    workerJob = pexConfig.ConfigField("worker job", JobTemplateConfig)
    # DAG generator script to use to create DAG submission file
    generator = pexConfig.ConfigChoiceField("generator", typemap)
