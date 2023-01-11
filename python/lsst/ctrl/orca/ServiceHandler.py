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

import json
from http.server import BaseHTTPRequestHandler


class ServiceHandler(BaseHTTPRequestHandler):

    version = "v1"
    production = "/api/%s/production" % version

    def setParent(self, parent, runid):
        """Set the parent object and runid of this handler

        Parameters
        ----------
        parent: object
            The parent object that will deal with requests from this handler
        runid: `str`
            The runid of the production
        """
        self.parent = parent
        self.runid = runid

    def do_DELETE(self):
        """handle a HTTP DELETE request"""
        # check to be sure that we handle this type of request
        # produce an error if we don't see what we expect to see
        if self.path == self.production:
            s = self.rfile.read(int(self.headers["Content-length"]))
            # check for payload validity
            # produce an error if we don't see what we expect to see
            try:
                data = json.loads(s)
                level = data["level"]
                runid = data["runid"]
                if runid != self.runid:
                    raise ValueError("invalid runid received")
                self.send_response(204)
                self.end_headers()
                self.parent.stopProduction(level)
            except Exception as error:  # noqa: F841
                self.send_response(422)
                self.end_headers()
                self.writeError("Unprocessable entity", "Error in syntax of message")
            return
        self.send_response(400)
        self.writeError("Bad Request", "Request is unsupported")
        self.end_headers()

    def writeError(self, status, message):
        """emit an error message as a response to remote client

        Parameters
        ----------
        status : `str`
            type of error
        message : `str`
            explanation of error
        """
        err = {"status": status, "message": message}
        message = json.dumps(err)
        self.wfile.write(message)
