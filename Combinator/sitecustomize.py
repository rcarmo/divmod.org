
import sys
import os

from combinator.branchmgr import theBranchManager
theBranchManager.addPaths()

for key in sys.modules.keys():
    # Unload all Combinator modules that had to be loaded in order to call
    # addPaths().  Although the very very beginning of this script needs to
    # load the trunk combinator (or whichever one your shell points at), once
    # the path has been set up, newer versions of combinator may be used; for
    # example, the 'whbranch', 'chbranch' and 'mkbranch' commands should all
    # import Combinator from the current Divmod branch.  This is especially
    # required so that Combinator's tests can be run on the currently-active
    # Combinator rather than the one responsible for setting up the
    # environment.
    if key == 'combinator' or key.startswith('combinator'):
        del sys.modules[key]

