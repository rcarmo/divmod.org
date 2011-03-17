
"""
Tests for L{Filter} schema upgrading.
"""

from axiom.test.historic.stubloader import StubbedTest

from xquotient.spam import Filter
from xquotient.mail import MessageSource
from xquotient.exmess import _TrainingInstructionSource

from xquotient.test.historic.stub_filter3to4 import USE_POSTINI_SCORE, POSTINI_THRESHHOLD


class FilterUpgradeTest(StubbedTest):
    """
    Tests for L{Filter} schema upgrading.
    """
    def test_attributes(self):
        """
        The upgrade preserves the values of all the remaining attributes.
        """
        filter = self.store.findUnique(Filter)
        self.assertEquals(filter.usePostiniScore, USE_POSTINI_SCORE)
        self.assertEquals(filter.postiniThreshhold, POSTINI_THRESHHOLD)
        self.assertTrue(isinstance(filter.messageSource, MessageSource))
        self.assertTrue(isinstance(filter.tiSource, _TrainingInstructionSource))

