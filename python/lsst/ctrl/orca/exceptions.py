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


class ConfigurationError(RuntimeError):
    """An exception that indicates that an error occurred in the configuration
    of a production run or one of its components.
    """

    pass


class MultiIssueConfigurationError(ConfigurationError):
    """A configuration error that can report on multiple problems.

    Parameters
    ----------
    msg : `str`, optional
        The general message to report when more than problem has been
        encountered.  If only one problem is added to this exception, that
        problem message will be displayed.  If None, a generic message is set.
    problem: `str`, optional
        The first problem to add to this exception.

    Extended Summary
    ---------------
    The intented pattern of use for this class is that it is
    created before any problems are found.  As they are found,
    calls are made to addProblem().  Finally, after all possible
    problems are found, one can call hasProblems().  If it is
    true, then this exception instance should be raised.
    """

    def __init__(self, msg=None, problem=None):
        if msg is None:
            msg = "Multiple configuration problems encountered"
        ConfigurationError.__init__(self, msg)
        self._probs = []
        if problem is not None:
            self.addProblem(problem)

    def addProblem(self, msg):
        """Add a message indicating one of the problems encountered"""
        self._probs.append(msg)

    def hasProblems(self):
        """
        Returns
        -------
        val : `bool`
            return True if this exception as at least one problem added to it.
        """
        return len(self._probs) > 0

    def getProblems(self):
        """
        Returns
        -------
        v : ['string1', 'string2']
            return a copy of the list of problems
        """
        return list(self._probs)

    # overrides __str__ for custom message
    def __str__(self):
        if len(self._probs) < 1:
            return "Unspecified configuration problems encountered"
        elif len(self._probs) == 1:
            return self._probs[0]
        else:
            return ConfigurationError.__str__(self)

    # overrides __repr__ for custom message
    def __repr__(self):
        return "MultiIssueConfigurationError: " + str(self)
