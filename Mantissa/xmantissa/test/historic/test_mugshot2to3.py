"""
Tests for L{Mugshot}'s version 2 to version 3 upgrader.
"""
from twisted.trial.unittest import SkipTest

from axiom.test.historic.stubloader import StubbedTest

from xmantissa.people import Mugshot, Person
from xmantissa.test.historic.stub_mugshot2to3 import (
    MUGSHOT_TYPE, MUGSHOT_BODY_PATH_SEGMENTS)


class MugshotUpgraderTestCase(StubbedTest):
    """
    Tests for L{Mugshot}'s version 2 to version 3 upgrader.
    """
    def setUp(self):
        """
        Skip the tests if PIL is unavailable.
        """
        try:
            import PIL
        except ImportError:
            raise SkipTest('PIL is not available')
        return StubbedTest.setUp(self)


    def test_attributesCopied(self):
        """
        The C{person}, C{smallerBody} and C{type} attributes of L{Mugshot}
        should have been copied over from the previous version.
        """
        from PIL import Image
        mugshot = self.store.findUnique(Mugshot)
        self.assertIdentical(mugshot.person, self.store.findUnique(Person))
        self.assertEqual(mugshot.type, MUGSHOT_TYPE)
        self.assertEqual(
            mugshot.body, self.store.newFilePath(*MUGSHOT_BODY_PATH_SEGMENTS))
        # mugshot.body should be untouched, it should have the same dimensions
        # as test/resources/square.png (240x240)
        self.assertEqual(Image.open(mugshot.body.open()).size, (240, 240))


    def test_smallerBodyAttribute(self):
        """
        L{Mugshot.smallerBody} should point to an image with the same
        dimensions as the current value of L{Mugshot.smallerSize}.
        """
        from PIL import Image
        mugshot = self.store.findUnique(Mugshot)
        self.assertEqual(
            Image.open(mugshot.smallerBody.open()).size,
            (mugshot.smallerSize, mugshot.smallerSize))
