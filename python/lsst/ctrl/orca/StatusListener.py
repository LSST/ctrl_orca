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

log = logging.getLogger(__name__)


class StatusListener:
    """Used receive messages about changes in a workflow"""

    # initializer
    def __init__(self):
        log.debug("StatusListener:__init__")

    def workflowFailed(self, name, errorName, errmsg, response, pipelineName):
        """Indicate that a workflow has experienced an as-yet unhandled
        failure and can't process further

        Parameters
        ----------
        name : `str`
            name of the workflow
        errorName : `str`
            name of the error
        errmsg : `str`
            error message
        request : dict
            dictionary containing the remote response message
        pipelineName : `str`
            the name of the pipeline in which this error occurred.
        """
        return

    def workflowShutdown(self, name):
        """The workflow has successfully shutdown and ready to be cleaned up

        Parameters
        ----------
        name : `str`
            name of the workflow
        """
        return

    def workflowStarted(self, name):
        """Called when a workflow has started up correctly and is
           ready to process data.

        Parameters
        ----------
        name : `str`
            name of the workflow

        Notes
        -----
        If a pipeline is waiting for an request, the listener should be
        notified via workflowWaiting
        """
        return

    def workflowWaiting(self, name):
        """Indicate that a workflow is waiting for an request to proceed.

        Parameters
        ----------
        name : `str`
            name of the workflow
        """
        return
