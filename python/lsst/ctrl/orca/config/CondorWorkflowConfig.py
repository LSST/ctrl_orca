import lsst.pex.config as pexConfig

# condor data configuration


class CondorDataConfig(pexConfig.Config):
    # local scratch space
    localScratch = pexConfig.Field("temp data area", str)


# template information


class TemplateConfig(pexConfig.Config):
    # key/value pairs
    keywords = pexConfig.DictField(
        "key value pairs", keytype=str, itemtype=str, default=dict()
    )
    # input file
    inputFile = pexConfig.Field("name of template to fill in", str, default=None)
    # output file
    outputFile = pexConfig.Field("name of file to write", str, default=None)


# condor glide-in configuration


class GlideinConfig(pexConfig.Config):
    # condor glide-in template
    template = pexConfig.ConfigField("condor template", TemplateConfig)


# condor workflow configuration


class CondorWorkflowConfig(pexConfig.Config):
    # condor data configuration
    condorData = pexConfig.ConfigField("condor data", CondorDataConfig)
    # glide in configuration
    glidein = pexConfig.ConfigField("glidein info", GlideinConfig)
