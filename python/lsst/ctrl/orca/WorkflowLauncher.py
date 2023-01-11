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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the LSST License Statement and
# the GNU General Public License along with this program.  If not,
# see <http://www.lsstcorp.org/LegalNotices/>.
#

import logging

from lsst.ctrl.orca.WorkflowMonitor import WorkflowMonitor

log = logging.getLogger(__name__)

##
# @brief an abstract class for configuring a workflow
#
# This class should not be used directly but rather must be subclassed,
# providing an implementation for _configureSpecialized.
#


class WorkflowLauncher:
    ##
    # @brief
    #
    # This constructor should only be called from a subclass's
    # constructor, in which case the fromSub parameter must be
    # set to True.
    #
    # @param wfConfig    workflow config
    #

    def __init__(self, wfConfig):
        log.debug("WorkflowLauncher:__init__")

        # workflow configuration
        self.wfConfig = wfConfig

    ##
    # @brief perform cleanup after workflow has ended.
    #
    def cleanUp(self):
        log.debug("WorkflowLauncher:cleanUp")

    ##
    # @brief launch this workflow
    #
    def launch(self, statusListener):
        log.debug("WorkflowLauncher:launch")

        # monitors status of the workflow
        self.workflowMonitor = WorkflowMonitor()
        if statusListener is not None:
            self.workflowMonitor.addStatusListener(statusListener)

        # returns WorkflowMonitor
        return self.workflowMonitor
