
"""
Tests for L{reverend.thomas}.
"""

from twisted.trial.unittest import TestCase

from reverend.thomas import Bayes


class BayesTests(TestCase):
    """
    Tests for L{Bayes}.
    """
    def test_untrainedGuess(self):
        """
        The C{guess} method of a L{Bayes} instance with no training data returns
        an empty list.
        """
        bayes = Bayes()
        self.assertEquals(bayes.guess("hello, world"), [])
