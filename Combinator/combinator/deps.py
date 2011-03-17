
from combinator.branchmgr import theBranchManager

dependencies = [
    'Twisted', 'trunk', 'svn+ssh://svn.twistedmatrix.com/svn/Twisted/trunk',
    'Nevow', 'trunk', 'svn+ssh://divmod.org/svn/Nevow/trunk',
    ]

def getAll(anonymously=True):
    for dep, bch, uri in dependencies:
        theBranchManager.changeProjectBranch(dep, bch, uri)
