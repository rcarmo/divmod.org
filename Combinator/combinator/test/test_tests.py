
"""
Since combinator sets up the environment for the tests, these tests
attempt to verify that the tests are actually running the code that you think
they're running.
"""

import combinator

from twisted.python.filepath import FilePath
from twisted.trial.unittest import TestCase

class EnvironmentTestCase(TestCase):
    """
    Tests that verify that the test environment is sane.
    """

    def test_pathsMatch(self):
        """
        Verify that the path of this unit test is the same as the Combinator
        imported and under test.
        """
        cdir = FilePath(combinator.__file__).parent()
        self.assertEquals(FilePath(__file__).parent().parent(), cdir)
