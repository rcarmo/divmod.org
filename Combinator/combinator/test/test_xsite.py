"""
This module contains tests for combinator.xsite.
"""

import os
from combinator.xsite import addsitedir
from twisted.trial import unittest

class Pth(unittest.TestCase):
    """
    Some tests for .pth file handling.
    """

    def makeSomeDirs(self):
        """
        Set up some directories for the test.
        """
        dir1 = self.mktemp()
        os.makedirs(dir1)
        dir2 = os.path.join(dir1, "subdir")
        os.makedirs(dir2)
        pthfile = file(os.path.join(os.path.abspath(dir1), "test.pth"), 'w')
        pthfile.write("subdir\n")
        pthfile.close()
        return dir1, dir2

    def test_addSiteDir(self):
        """
        Test that addSiteDir reads .pth files and adds them to the path passed
        to it.
        """
        dir1, dir2 = self.makeSomeDirs()
        syspath = []
        addsitedir(dir1, syspath)
        self.assertEqual(syspath, [os.path.abspath(x) for x in (dir1, dir2)])
        dir3 = self.mktemp()
        os.makedirs(dir3)
        syspath = [dir3]
        addsitedir(dir1, syspath)
        self.assertEqual(syspath, [dir3] + [os.path.abspath(x)
                                            for x in (dir1, dir2)])

    def test_invalidSiteDir(self):
        """
        Test that invalid entries in syspath doesn't cause addsitedir to raise
        an error.
        """
        dir1, dir2 = self.makeSomeDirs()
        syspath = [17]
        addsitedir(dir1, syspath)
        del syspath[0]
        self.assertEqual(syspath, [os.path.abspath(x) for x in (dir1, dir2)])

    def test_extraPthBits(self):
        """
        Test that comments are ignored and import statements are honored in pth
        files.
        """
        dir1 = self.mktemp()
        os.makedirs(dir1)
        dir2 = os.path.join(dir1, "subdir")
        os.makedirs(dir2)
        pthfile = file(os.path.join(os.path.abspath(dir1), "test.pth"), 'w')
        pthfile.write("import sys\n#a comment\nsubdir\n")
        pthfile.close()
        syspath = []
        addsitedir(dir1, syspath)
        self.assertEqual(syspath, [os.path.abspath(x) for x in (dir1, dir2)])
