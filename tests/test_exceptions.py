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

"""
Tests of orca exceptions
"""
import unittest

import lsst.utils.tests
from lsst.ctrl.orca.exceptions import MultiIssueConfigurationError


def setup_module(module):
    lsst.utils.tests.init()


class MultiIssueTestCase(lsst.utils.tests.TestCase):
    unspecified = "Unspecified configuration problems encountered"
    generic = "Multiple configuration problems encountered"

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testNoProb(self):
        err = MultiIssueConfigurationError()
        self.assertFalse(err.hasProblems())
        self.assertEqual(str(err), self.unspecified)

        probs = err.getProblems()
        self.assertEqual(len(probs), 0)

    def testOneProb(self):
        msg = "first problem"
        err = MultiIssueConfigurationError(problem=msg)
        self.assertEqual(str(err), msg)

        probs = err.getProblems()
        self.assertEqual(len(probs), 1)
        self.assertEqual(probs[0], msg)

    def testTwoProbs(self):
        msg = "first problem"
        err = MultiIssueConfigurationError(problem=msg)
        self.assertEqual(str(err), msg)
        msg2 = "second problem"
        err.addProblem(msg2)
        self.assertEqual(str(err), self.generic)

        probs = err.getProblems()
        self.assertEqual(len(probs), 2)
        self.assertEqual(probs[0], msg)
        self.assertEqual(probs[1], msg2)

    def testGenericMsg(self):
        msg = "problems encountered while checking configuration"
        err = MultiIssueConfigurationError(msg)
        self.assertEqual(str(err), self.unspecified)

        msg1 = "first problem"
        err.addProblem(msg1)
        self.assertEqual(str(err), msg1)

        err.addProblem("2nd problem")
        self.assertEqual(str(err), msg)


class ExceptionsMemoryTester(lsst.utils.tests.MemoryTestCase):
    pass


__all__ = "MultiIssueTestCase".split()

if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()
