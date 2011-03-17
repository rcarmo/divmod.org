# Copyright (c) 2006 Divmod.
# See LICENSE for details.

"""
Runs hyperbola javascript tests as part of the hyperbola python tests
"""

from nevow.testutil import JavaScriptTestCase

class HyperbolaJavaScriptTestCase(JavaScriptTestCase):
    """
    Run all the hyperbola javascript tests.
    """

    def test_scrolltable(self):
        """
        Test the blurb-listing scrolltable.
        """
        return 'Hyperbola.ConsoleTest.TestScrollTable'


    def test_blogPostBlurbController(self):
        """
        Test the blog post blurb controller!
        """
        return 'Hyperbola.Test.TestBlogPostBlurb'
