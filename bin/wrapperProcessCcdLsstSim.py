#!/usr/bin/env python
#
# LSST Data Management System
# Copyright 2008, 2009, 2010 LSST Corporation.
#
# This product includes software developed by the
# LSST Project (http://www.lsst.org/).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
#
# You should have received a copy of the LSST License Statement and
# the GNU General Public License along with this program.  If not,
# see <http://www.lsstcorp.org/LegalNotices/>.
#

# XXXXXX XXXXXXXXXX XXXXXX XXXXXXXXXX XXXXXX XXXXXXXXXX XXXXXX XXXXXXXXXX
# This wrapper code is only here temporarily until we can find it a better
# home.  This wrapper code should *not* be in ctrl_orca
# XXXXXX XXXXXXXXXX XXXXXX XXXXXXXXXX XXXXXX XXXXXXXXXX XXXXXX XXXXXXXXXX

import sys
import traceback

from lsst.pipe.base import ArgumentParser
from lsst.pipe.tasks.processCcdLsstSim import ProcessCcdLsstSimTask as TaskClass
# added by srp
from lsst.ctrl.events import EventLog
###### 

if __name__ == "__main__":
    # added by srp
    runid = sys.argv[1]
    workerid = int(sys.argv[2])
    sys.argv.pop(1)
    sys.argv.pop(1)
    EventLog.createDefaultLog(runid, workerid)
    ###### 
    parser = ArgumentParser()
    namespace = parser.parse_args(config=TaskClass.ConfigClass())
    task = TaskClass(namespace.config, log = namespace.log)
    for sensorRef in namespace.dataRefList:
        sensorRef.put(namespace.config, "processCcd_config")
        if namespace.doRaise:
            task.run(sensorRef)
        else:
            try:
                task.run(sensorRef)
            except Exception, e:
                task.log.log(task.log.FATAL, "Failed on dataId=%s: %s" % (sensorRef.dataId, e))
                traceback.print_exc(file=sys.stderr)
        sensorRef.put(task.getFullMetadata(), "processCcd_metadata")

