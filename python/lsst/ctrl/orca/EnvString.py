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

import os
import re


class EnvString:
    def resolve(strVal):
        """Replace environment variables within a string

        Extended Summary
        ----------------
        Given a string, look for any $ prefixed word, attempt to subsitute
        an environment variable with that name.

        Raises
        ------
        `RuntimeError`
            if the environment variable doesn't exist

        Returns
        -------
        retVal : `str`
            the resulting string with environment variable info substituted.
        """

        p = re.compile(r"\$[a-zA-Z0-9_]+")
        retVal = strVal
        exprs = p.findall(retVal)
        for i in exprs:
            var = i[1:]
            val = os.getenv(var, None)
            if val is None:
                raise RuntimeError("couldn't find " + i + " environment variable")
            retVal = p.sub(val, retVal, 1)
        return retVal

    # static method to resolve string
    resolve = staticmethod(resolve)
