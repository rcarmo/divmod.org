
"""
This module contains tests for combinator.branchmgr.
"""

import os, sys, StringIO

from twisted.trial.unittest import TestCase
from twisted.python.filepath import FilePath

from combinator import branchmgr
from combinator.branchmgr import DuplicateBranch, NonExistentBranch
from combinator.branchmgr import InvalidBranch, UncleanTrunkWorkingCopy
from combinator.branchmgr import MissingTrunkLocation
from combinator.branchmgr import BranchManager, subversionURLExists
from combinator.branchmgr import chbranchMain, mkbranchMain, whbranchMain
from combinator.branchmgr import unbranchMain
from combinator.subversion import createSubversionRepository, commit



class SubversionUtilitiesTests(TestCase):
    """
    Tests to more or less general subversion-related functionality.
    """
    def setUp(self):
        """
        Compute the path and URL to a subversion repository which can be
        tested against and set up standard out to be recorded and hidden.
        """
        self.repository = FilePath(self.mktemp())
        createSubversionRepository(self.repository, {'foo': {}})
        self.url = 'file://' + self.repository.path
        self.stdout = sys.stdout
        sys.stdout = StringIO.StringIO()


    def tearDown(self):
        """
        Restore the normal standard out behavior.
        """
        sys.stdout = self.stdout


    def test_subversionURLExists(self):
        """
        L{subversionURLExists} should return True if given an URL which does
        exist.
        """
        self.assertTrue(subversionURLExists(self.url))


    def test_subversionURLDoesNotExist(self):
        """
        L{subversionURLExists} should return False if given an URL which
        does not exist.
        """
        self.assertFalse(subversionURLExists(self.url + '/bar'))



class BranchManagerTests(TestCase):
    """
    Tests for the BranchManager object.
    """

    def setUp(self):
        """
        Start keeping a record of all changed environment variables.
        """
        self.changedEnv = {}


    def changeEnvironment(self, key, value):
        """
        Change an environmnt variable such that it will be set back to its
        previous value at the end of the test.
        """
        self.changedEnv[key] = os.environ[key]
        os.environ[key] = value


    def tearDown(self):
        """
        Change back all environment variables altered during the course of this
        test.
        """
        for k, v in self.changedEnv.items():
            os.environ[k] = v


    def test_creation(self):
        """
        Verify that a newly-created branch manager can locate the paths it
        needs to do things.
        """
        b = BranchManager()
        self.assertNotEqual(b.svnProjectsDir, None)
        self.assertNotEqual(b.sitePathsPath, None)
        self.assertNotEqual(b.binCachePath, None)


    def test_projectsEnvironment(self):
        """
        Verify that BranchManager draws from the environment for the projects
        path.
        """
        self.changeEnvironment("COMBINATOR_PROJECTS", "somedir")
        b = BranchManager()
        self.assertEqual(b.svnProjectsDir, os.path.abspath("somedir"))


    def test_pathsEnvironment(self):
        """
        Verify that BranchManager draws from the environment for the paths
        path.
        """
        self.changeEnvironment("COMBINATOR_PATHS", "pathdir")
        b = BranchManager()
        self.assertEqual(b.sitePathsPath, os.path.abspath("pathdir"))
        self.assertEqual(b.binCachePath, "pathdir/bincache")


    def _perUserSitePackages(self, home):
        """
        Construct the path to the user-specific site-packages path.
        """
        return os.path.abspath(os.path.join(
            home, '.local', 'lib', 'python%d.%d' % tuple(sys.version_info[:2]),
            'site-packages'))


    def test_userSitePackages(self):
        """
        L{BranchManager.getPaths} should return an iterable which has as an
        element the user-specific site-packages directory, if that directory
        exists.
        """
        home = self.mktemp()
        sitePackages = self._perUserSitePackages(home)
        os.makedirs(sitePackages)
        self.changeEnvironment('HOME', home)
        b = BranchManager()
        self.assertIn(sitePackages, list(b.getPaths()))


    def test_missingUserSitePackages(self):
        """
        L{BranchManager.getPaths} should return an iterable which does not
        have as an element the user-specific site-packages directory, if
        that directory does not exist.
        """
        home = self.mktemp()
        self.changeEnvironment('HOME', home)
        b = BranchManager()
        self.assertNotIn(self._perUserSitePackages(home), list(b.getPaths()))



class FakeBranchManager(object):
    """
    Purely in-memory implementation of the branch manager API.

    @ivar activeBranches: A mapping from C{str} project names to C{str} branch
        names.  The branch name corresponding to each project name is the
        branch which is currently active for that project.

    @ivar repositories: A mapping from C{str} project names to C{dict}s
        representing the contents of the repository for that project.  Keys are
        C{str} giving path segments and values are either C{str} giving file
        contents or C{dict} with similar structure.

    @ivar workingCopies: A mapping from C{str} project names to C{list} of
        C{str} branch names.  Each branch name in a list is a branch which has
        been checked out for the corresponding project.
    """
    def __init__(self, repositories=None):
        self.activeBranches = {}
        if repositories is None:
            repositories = {}
        self.repositories = repositories
        self.workingCopies = {}
        self.trunkClean = True


    def _exists(self, path):
        place = self.repositories
        while path:
            try:
                place = place[path[0]]
            except KeyError:
                return False
            path = path[1:]
        return True


    def changeProjectBranch(self, projectName, branchName, branchURI=None):
        """
        Change the in-memory record of the active branch for the indicated
        project.
        """
        if (projectName not in self.workingCopies or
            branchName not in self.workingCopies[projectName]):
            if branchURI is None:
                if projectName in self.activeBranches:
                    path = (projectName, 'branches', branchName)
                else:
                    raise MissingTrunkLocation(projectName)
            else:
                path = branchURI

            # Make sure the branch URI is valid.
            if not self._exists(path):
                raise NonExistentBranch(branchURI or branchName)
            self.workingCopies.setdefault(projectName, []).append(branchName)
        self.activeBranches[projectName] = branchName


    def currentBranchFor(self, projectName):
        """
        Retrieve the currently active branch for the given project name.
        """
        return self.activeBranches[projectName]


    def getCurrentBranches(self):
        """
        Retrieve all of the currently active branches.
        """
        return self.activeBranches.iteritems()


    def newProjectBranch(self, projectName, branchName):
        """
        Change the given project's active branch.
        """
        if (projectName not in self.workingCopies or
            "trunk" not in self.workingCopies[projectName]):
            raise MissingTrunkLocation(projectName)
        if self._exists((projectName,) + ('branches', branchName)):
            raise DuplicateBranch(branchName)
        self.activeBranches[projectName] = branchName


    def mergeProjectBranch(self, projectName, force=False):
        """
        Change the given project's active branch to trunk, unless it is trunk
        already.
        """
        if self.activeBranches.get(projectName, None) == "trunk":
            raise InvalidBranch()
        if not self.trunkClean and not force:
            raise UncleanTrunkWorkingCopy()
        self.changeProjectBranch(projectName, 'trunk')



def _uri(repository, *branch):
    return 'file://' + reduce(FilePath.child, branch, repository).path



class ChangeBranchTestsMixin:
    def test_getCurrentBranches(self):
        """
        L{BranchManager.getCurrentBranches} returns an iterable of two-tuples
        of project names and current active branches for all known branches.
        """
        self.createRepository("Quux", {"trunk": {}})
        self.manager.changeProjectBranch(
            "Quux", "trunk", self.uri("Quux", "trunk"))
        self.createRepository("Quarj", {"trunk": {},
                                        "branches":
                                            {"foo": {}}})
        self.manager.changeProjectBranch(
            "Quarj", "trunk", self.uri("Quarj", "trunk"))
        self.manager.changeProjectBranch("Quarj", "foo")
        self.assertEqual(
            set(self.manager.getCurrentBranches()),
            set([("Quux", "trunk"), ("Quarj", "foo")]))


    def test_trunkCheckout(self):
        """
        L{BranchManager.changeProjectBranch} creates in the projects directory
        a checkout of trunk of the given project.
        """
        projectName = 'Quux'
        self.createRepository(projectName, {'trunk': {}})
        self.manager.changeProjectBranch(
            projectName, 'trunk', self.uri(projectName, 'trunk'))
        self.checkTrunkCheckout(projectName)


    def test_trunkCheckoutWritesBranchFile(self):
        """
        L{BranchManager.changeProjectBranch} should write a new I{.bch} file
        for the given project when switching to trunk for the first time.
        """
        projectName = 'Quux'
        self.createRepository(projectName, {'trunk': {}})
        self.manager.changeProjectBranch(
            projectName, 'trunk', self.uri(projectName, 'trunk'))
        self.assertEqual(self.manager.currentBranchFor(projectName), 'trunk')


    def test_branchCheckoutChangesBranchFile(self):
        """
        L{BranchManager.changeProjectBranch} should rewrite an existing
        project's I{.bch} file when changing to a different branch.  The
        repository URI should not be required for this case.
        """
        projectName = 'Quux'
        branchName = 'foo'

        self.createRepository(
            projectName, {'trunk': {},
                          'branches':
                              {branchName: {}}})

        # First get trunk
        self.manager.changeProjectBranch(
            projectName, 'trunk', self.uri(projectName, 'trunk'))

        # Then switch to the branch
        self.manager.changeProjectBranch(projectName, branchName)

        self.assertEqual(
            self.manager.currentBranchFor(projectName), branchName)


    def test_changeToTrunkMissingTrunkLocation(self):
        """
        L{BranchManager.changeProjectBranch} raises L{MissingTrunkLocation}
        when asked to change the active branch of a project to trunk when the
        trunk URI has not been specified.
        """
        err = self.assertRaises(
            MissingTrunkLocation,
            self.manager.changeProjectBranch, 'Quux', 'trunk')
        self.assertEqual(err.args, ("Quux",))


    def test_changeToBranchMissingTrunkLocation(self):
        """
        L{BranchManager.changeProjectBranch} raises L{MissingTrunkLocation}
        when asked to change the active branch of a project to non-trunk when
        the trunk URI has not been specified.
        """
        err = self.assertRaises(
            MissingTrunkLocation,
            self.manager.changeProjectBranch, 'Quux', 'foo')
        self.assertEqual(err.args, ("Quux",))


    def test_changeBranchRejectsInvalid(self):
        """
        L{BranchManager.changeProjectBranch} raises L{NonExistentBranch} when
        passed the name of a branch which does not already exist.
        """
        projectName = 'Quux'
        branchName = 'fantastical'

        self.createRepository(projectName, {'trunk': {}})

        # First get trunk
        self.manager.changeProjectBranch(
            projectName, 'trunk', self.uri(projectName, 'trunk'))

        # Then try to change to a branch which isn't real.
        err = self.assertRaises(
            NonExistentBranch,
            self.manager.changeProjectBranch,
            projectName, branchName)
        self.assertEqual(err.args, (branchName,))


    def test_changeBranchRejectsExplicitInvalid(self):
        """
        L{BranchManager.changeProjectBranch} raises L{IOError} when passed a
        branch URI which is invalid.
        """
        projectName = 'Quux'
        branchName = 'foo'

        self.createRepository(projectName,
                              {'trunk': {},
                               'branches':
                                   {branchName: {}}})

        # First get trunk
        self.manager.changeProjectBranch(
            projectName, 'trunk', self.uri(projectName, 'trunk'))

        # Then try to change to a branch using a URI which is invalid.
        uri = self.uri(projectName, 'not a real thing')
        err = self.assertRaises(
            NonExistentBranch,
            self.manager.changeProjectBranch,
            projectName, branchName, uri)
        self.assertEqual(err.args, (uri,))


    def test_changeToCheckedOutBranch(self):
        """
        L{BranchManager.changeProjectBranch} succeeds if the repository is
        inaccessible but there is already a checkout of the specified
        branch.
        """
        projectName = 'Quux'
        branchName = 'foo'

        self.createRepository(projectName,
                              {'trunk': {},
                               'branches':
                                   {branchName: {}}})

        # First get trunk
        self.manager.changeProjectBranch(
            projectName, 'trunk', self.uri(projectName, 'trunk'))

        # Then switch to the branch
        self.manager.changeProjectBranch(projectName, branchName)

        # Go offline
        self.makeRepositoryInaccessible(projectName)

        # Switch back to trunk and (since trunk is slightly different than
        # other branches) then back to the branch
        self.manager.changeProjectBranch(projectName, 'trunk')
        self.assertEqual(self.manager.currentBranchFor(projectName), 'trunk')
        self.manager.changeProjectBranch(projectName, branchName)
        self.assertEqual(
            self.manager.currentBranchFor(projectName), branchName)


    def test_newBranchForUnknownProject(self):
        """
        L{BranchManager.newProjectBranch} raises L{MissingTrunkLocation} if
        passed the name of an unrecognized project.
        """
        err = self.assertRaises(
            MissingTrunkLocation,
            self.manager.newProjectBranch, "Quux", "foo")
        self.assertEqual(err.args, ("Quux",))


    def test_changeCurrentBranch(self):
        """
        L{BranchManager.newProjectBranch} should change the current branch of
        the given project to the newly created branch.
        """
        projectName = 'Quux'
        branchName = 'bar'
        self.createRepository(projectName, {'trunk': {}, 'branches': {}})
        self.manager.changeProjectBranch(
            projectName, 'trunk', self.uri(projectName, 'trunk'))
        self.manager.newProjectBranch(projectName, branchName)
        self.assertEqual(
            self.manager.currentBranchFor(projectName), branchName)


    def test_rejectDuplicateBranch(self):
        """
        L{BranchManager.newProjectBranch} should refuse to copy trunk into an
        existing branch.
        """
        projectName = 'Quux'
        branchName = 'baz'
        self.createRepository(projectName, {'trunk': {},
                                            'branches':
                                                {branchName: {}}})
        self.manager.changeProjectBranch(
            projectName, 'trunk', self.uri(projectName, 'trunk'))
        err = self.assertRaises(
            DuplicateBranch,
            self.manager.newProjectBranch, projectName, branchName)
        self.assertEqual(err.args, (branchName,))

    def test_merge(self):
        """
        Merging a branch does not produce any errors under normal conditions.
        """
        projectName = "Quux"
        branchName = 'baz'
        self.createRepository(projectName, {"trunk": {},
                                            'branches': {branchName: {}}})
        self.manager.changeProjectBranch(
            projectName, 'trunk', self.uri(projectName, 'trunk'))
        self.manager.changeProjectBranch(projectName, branchName)
        self.manager.mergeProjectBranch(projectName)
        self.assertEqual(
            self.manager.currentBranchFor(projectName), 'trunk')


    def test_mergeUnknownProject(self):
        """
        L{BranchManager.mergeProjectBranch} raises L{MissingTrunkLocation} if
        passed the name of a project for which the trunk URI has not been
        specified.
        """
        projectName = "Quux"
        err = self.assertRaises(
            MissingTrunkLocation,
            self.manager.mergeProjectBranch, projectName)
        self.assertEqual(err.args, (projectName,))


    def test_mergeTrunk(self):
        """
        L{BranchManager.mergeProjectBranch} raises L{InvalidBranch} if passed
        the name of a project for which the current active branch is trunk.
        """
        projectName = "Quux"
        self.createRepository(projectName, {"trunk": {}})
        self.manager.changeProjectBranch(
            projectName, "trunk", self.uri(projectName, "trunk"))
        err = self.assertRaises(
            InvalidBranch,
            self.manager.mergeProjectBranch, projectName)
        self.assertEqual(err.args, ())


    def test_mergeUnclean(self):
        """
        L{BranchManager.mergeProjectBranch} raises L{UncleanTrunkWorkingCopy}
        if there are uncommitted changes in trunk.
        """
        projectName = "Quux"
        branchName = 'baz'
        fname = 'foo.txt'
        contents = {fname: 'some data'}
        self.createRepository(projectName, {"trunk": contents,
                                            'branches': {branchName: contents}})
        self.manager.changeProjectBranch(
            projectName, 'trunk', self.uri(projectName, 'trunk'))
        self.manager.changeProjectBranch(projectName, branchName)
        self.modifyTrunk(projectName, fname, 'some new data')
        err = self.assertRaises(
            UncleanTrunkWorkingCopy,
            self.manager.mergeProjectBranch, projectName)
        self.assertEqual(
            self.manager.currentBranchFor(projectName), branchName)


    def test_forceMergeUnclean(self):
        """
        L{BranchManager.mergeProjectBranch} does not raise
        L{UncleanTrunkWorkingCopy} if the 'force' flag is specified.
        """
        projectName = "Quux"
        branchName = 'baz'
        fname = 'foo.txt'
        contents = {fname: 'some data'}
        self.createRepository(projectName, {"trunk": contents,
                                            'branches': {branchName: contents}})
        self.manager.changeProjectBranch(
            projectName, 'trunk', self.uri(projectName, 'trunk'))
        self.manager.changeProjectBranch(projectName, branchName)
        self.modifyTrunk(projectName, fname, 'some new data')
        self.manager.mergeProjectBranch(projectName, force=True)
        self.assertEqual(
            self.manager.currentBranchFor(projectName), 'trunk')



class FakeBranchManagerChangeBranchTests(TestCase, ChangeBranchTestsMixin):
    """
    Tests for L{FakeBranchManager.changeProjectBranch}.
    """
    def setUp(self):
        """
        Create an in-memory branch manager which knows about the repository for
        a project with some branches.
        """
        self.manager = FakeBranchManager()


    def uri(self, project, *branch):
        """
        Create an identifier for the given project's branch.
        L{FakeBranchManager} can interpret this.
        """
        return (project,) + branch


    def createRepository(self, projectName, contents):
        """
        Add an in-memory repository for the given project with the given
        contents.
        """
        self.manager.repositories[projectName] = contents


    def checkTrunkCheckout(self, projectName):
        """
        Make sure there is a trunk working copy for the given project.
        """
        self.assertIn(projectName, self.manager.workingCopies)
        self.assertIn("trunk", self.manager.workingCopies[projectName])


    def makeRepositoryInaccessible(self, projectName):
        """
        Discard the repository for the given project.
        """
        del self.manager.repositories[projectName]


    def modifyTrunk(self, projectName, fname, newData):
        """
        Make a change to a file in trunk.
        """
        self.manager.trunkClean = False



class BranchManagerChangeBranchTests(TestCase, ChangeBranchTestsMixin):
    """
    Tests for L{BranchManager.changeProjectBranch}.
    """
    projectName = 'Quux'

    def setUp(self):
        """
        Create a branch manager with temporary directories for all its working
        filesystem paths.
        """
        self.paths = self.mktemp()
        self.projects = self.mktemp()
        os.makedirs(self.paths)
        os.makedirs(self.projects)
        self.manager = BranchManager(self.paths, self.projects)
        self.cwd = os.getcwd()
        self.repositories = FilePath(self.mktemp())


    def tearDown(self):
        """
        Assert that the working directory has been restored to its original
        value if it was changed.
        """
        try:
            self.assertEqual(self.cwd, os.getcwd())
        finally:
            os.chdir(self.cwd)


    def createRepository(self, projectName, contents):
        """
        Create a new SVN repository with the given contents and associate it
        with given project.
        """
        path = self.repositories.child(projectName)
        path.makedirs()
        createSubversionRepository(path, contents)


    def uri(self, projectName, *branch):
        """
        Return a I{file} URI for the given branch of the given project.
        """
        return _uri(self.repositories.child(projectName), *branch)


    def checkTrunkCheckout(self, project):
        """
        Assert that a trunk checkout of the given project exists.
        """
        trunkWorkingCopy = FilePath(self.paths).child(project).child('trunk')
        self.assertTrue(
            trunkWorkingCopy.exists(),
            "%r did not exist." % (trunkWorkingCopy.path,))


    def makeRepositoryInaccessible(self, projectName):
        """
        Make the repository inaccessible so checks for the existence of
        branches can't possibly succeed.
        """
        self.repositories.child(projectName).remove()


    def modifyTrunk(self, projectName, fname, newData):
        """
        Make a change to a file in trunk.
        """
        trunkpath = FilePath(self.paths).child(projectName).child('trunk')
        f = trunkpath.child(fname).open('w')
        f.write(newData)
        f.close()


    def commitTrunk(self, projectName):
        """
        Commit the trunk working copy for the given project.
        """
        commit(
            FilePath(self.paths).child(projectName).child('trunk'),
            'Commit some changes')


    def modifyBranch(self, projectName, branchName, fname, newData):
        """
        Make a change to a file in a branch.
        """
        fObj = FilePath(self.paths).child(projectName).child(
            'branches').child(branchName).child(fname).open('w')
        fObj.write(newData)
        fObj.close()


    def commitBranch(self, projectName, branchName):
        """
        Commit a branch working for the given project.
        """
        commit(
            FilePath(self.paths).child(projectName).child(
                'branches').child(branchName),
            'Commit some changes')


    def test_mergeConflict(self):
        """
        L{BranchManager.mergeProjectBranch} performs merges
        non-interactively so that they complete even if there is a merge
        conflict.
        """
        projectName = "Quux"
        branchName = 'baz'
        fname = 'foo.txt'
        contents = {fname: 'some data'}
        self.createRepository(projectName, {"trunk": contents,
                                            "branches": {}})

        self.manager.changeProjectBranch(
            projectName, 'trunk', self.uri(projectName, 'trunk'))
        self.manager.newProjectBranch(projectName, branchName)
        self.modifyTrunk(projectName, fname, 'changed data')
        self.commitTrunk(projectName)
        self.modifyBranch(
            projectName, branchName, fname, 'differently changed data')
        self.commitBranch(projectName, branchName)

        self.manager.mergeProjectBranch(projectName)



class MainFunctionTests(TestCase):
    """
    Tests for the main functions for the Combinator command line tools.
    """
    def setUp(self):
        """
        Replace the global branch manager instance with a fake branch manager
        that is easier to manipulate to test different situations.  Replace
        stdout with a StringIO.
        """
        self.originalBranchManager = branchmgr.theBranchManager
        self.manager = branchmgr.theBranchManager = FakeBranchManager()
        self.originalStandardOutput = sys.stdout
        sys.stdout = StringIO.StringIO()


    def tearDown(self):
        """
        Restore the real branch manager and stdout.
        """
        branchmgr.theBranchManager = self.originalBranchManager
        sys.stdout = self.originalStandardOutput


    def test_chbranchTrunkCheckoutWithoutURI(self):
        """
        C{chbranchMain} raises L{SystemExit} with a string explaining that the
        branchURI parameter is required if it is called to check out trunk
        without a branchURI.
        """
        err = self.assertRaises(
            SystemExit,
            chbranchMain, ["/bin/chbranch", "Quux", "trunk"])
        self.assertEqual(
            err.args,
            ("The location of %r trunk is not known.  Specify a URI as the "
             "3rd argument to check out a branch (check out trunk to make "
             "this unnecessary)." % ("Quux",),))


    def test_chbranchUnknownProject(self):
        """
        L{chbranchMain} raises L{SystemExit} with a string explaining that
        there is no such project if it is called with the name of a project
        which is unknown and a branch other than trunk.
        """
        err = self.assertRaises(
            SystemExit,
            chbranchMain, ["/bin/chbranch", "Quux", "baz"])
        self.assertEqual(
            err.args,
            ("The location of %r trunk is not known.  Specify a URI as the "
             "3rd argument to check out a branch (check out trunk to make "
             "this unnecessary)." % ("Quux",),))


    def test_chbranchInvalidBranchName(self):
        """
        C{chbranchMain} raises L{SystemExit} with a string explaining that
        there is no such branch if it is called to check out a branch which
        does not exist.
        """
        self.manager.repositories["Quux"] = {"trunk": {}}
        self.manager.changeProjectBranch("Quux", "trunk", ("Quux", "trunk"))
        err = self.assertRaises(
            SystemExit,
            chbranchMain, ["/bin/chbranch", "Quux", "baz"])
        self.assertEqual(
            err.args,
            ("No such branch: %r" % ("baz",),))


    def test_chbranchInvalidURI(self):
        """
        L{chbranchMain} raises L{SystemExit} with a string explaining that
        there is no such URI if it is called to checkout a branch with an
        explicit URI which does not exist.
        """
        self.manager.repositories["Quux"] = {"trunk": {}}
        self.manager.changeProjectBranch("Quux", "trunk", ("Quux", "trunk"))
        err = self.assertRaises(
            SystemExit,
            chbranchMain, ["/bin/chbranch", "Quux", "baz", "foobar"])
        self.assertEqual(
            err.args,
            ("No such branch: %r" % ("foobar",),))


    def test_chbranchWrongNumberOfArguments(self):
        """
        L{chbranchMain} raises L{SystemExit} with usage information if it is
        called with fewer than three arguments or more than four arguments.
        """
        for args in [
            ["/bin/chbranch", "Quux"],
            ["/bin/chbranch", "Quux", "foo", "bar", "baz"]]:
            err = self.assertRaises(
                SystemExit, chbranchMain, args)
            self.assertEqual(
                err.args, ("Usage: chbranch <project> <branch name> [trunk url]",))


    def test_chbranch(self):
        """
        L{chbranchMain} returns without exception when called to checkout a
        branch which exists.  It changes the active branch for the specified
        project.
        """
        branchName = "foo"
        self.manager.repositories["Quux"] = {"trunk": {},
                                             "branches":
                                                 {branchName: {}}}
        self.manager.changeProjectBranch("Quux", "trunk", ("Quux", "trunk"))
        chbranchMain(["/bin/chbranch", "Quux", branchName])
        self.assertEqual(self.manager.currentBranchFor("Quux"), branchName)


    def test_mkbranchWrongNumberOfArguments(self):
        """
        L{mkbranchMain} raises L{SystemExit} with usage information when called
        with a number of arguments other than three.
        """
        for args in [
            ["/bin/mkbranch", "Foo"],
            ["/bin/mkbranch", "Foo", "bar", "baz"]]:
            err = self.assertRaises(SystemExit, mkbranchMain, args)
            self.assertEqual(
                err.args,
                ("Usage: mkbranch <project> <branch name>",))


    def test_mkbranchUnknownProject(self):
        """
        L{mkbranchMain} raises L{SystemExit} with a string explaining there is
        no such project if it is called with the name of a project which is
        unknown.
        """
        err = self.assertRaises(
            SystemExit,
            mkbranchMain, ["/bin/mkbranch", "Quux", "foo"])
        self.assertEqual(
            err.args,
            ("The location of %r trunk is not known.  Specify a URI as the "
             "3rd argument to check out a branch (check out trunk to make "
             "this unnecessary)." % ("Quux",),))


    def test_mkbranchDuplicateBranch(self):
        """
        L{mkbranchMain} raises L{SystemExit} with a string explaining there is
        already a branch by the given name when called with the name of a
        branch which already exists.
        """
        self.manager.repositories["Quux"] = {"trunk": {},
                                             "branches":
                                                 {"foo": {}}}
        self.manager.changeProjectBranch("Quux", "trunk", ("Quux", "trunk"))
        err = self.assertRaises(
            SystemExit,
            mkbranchMain, ["/bin/mkbranch", "Quux", "foo"])


    def test_mkbranch(self):
        """
        L{mkbranchMain} returns without exception when called to create a new
        branch for a project which exists.  It changes the active branch for
        the specified project.
        """
        self.manager.repositories["Quux"] = {"trunk": {},
                                             "branches":
                                                 {"foo": {}}}
        self.manager.changeProjectBranch("Quux", "trunk", ("Quux", "trunk"))
        mkbranchMain(["/bin/mkbranch", "Quux", "bar"])
        self.assertEqual(self.manager.currentBranchFor("Quux"), "bar")


    def test_whbranchWrongNumberOfArguments(self):
        """
        L{whbranchMain} raises L{SystemExit} with a string explaining usage
        information if called with more than two arguments.
        """
        err = self.assertRaises(
            SystemExit,
            whbranchMain, ["/bin/whbranch", "foo", "bar"])
        self.assertEqual(
            err.args,
            ("Usage: whbranch [project]",))


    def test_whbranchOneArgument(self):
        """
        L{whbranchMain} prints the current branch for each known project if
        called with one argument.
        """
        self.manager.repositories["Quux"] = {"trunk": {}}
        self.manager.repositories["Quarj"] = {"trunk": {},
                                              "branches":
                                                  {"foo": {}}}
        self.manager.changeProjectBranch("Quux", "trunk", ("Quux", "trunk"))
        self.manager.changeProjectBranch("Quarj", "trunk", ("Quarj", "trunk"))
        self.manager.changeProjectBranch("Quarj", "foo")
        whbranchMain(["/bin/whbranch"])
        self.assertEqual(
            set(sys.stdout.getvalue().splitlines()),
            set(["Quux: trunk", "Quarj: foo"]))


    def test_whbranchTwoArguments(self):
        """
        L{whbranchMain} prints the current branch for the named project if
        called with two arguments.
        """
        self.manager.repositories["Quux"] = {"trunk": {}}
        self.manager.repositories["Quarj"] = {"trunk": {},
                                              "branches":
                                                  {"foo": {}}}
        self.manager.changeProjectBranch("Quux", "trunk", ("Quux", "trunk"))
        self.manager.changeProjectBranch("Quarj", "trunk", ("Quarj", "trunk"))
        self.manager.changeProjectBranch("Quarj", "foo")
        whbranchMain(["/bin/mkbranch", "Quux"])
        self.assertEqual(sys.stdout.getvalue(), "trunk\n")
        sys.stdout.truncate(0)
        whbranchMain(["/bin/mkbranch", "Quarj"])
        self.assertEqual(sys.stdout.getvalue(), "foo\n")


    def test_unbranchWrongNumberOfArgments(self):
        """
        L{unbranchMain} raises L{SystemExit} with usage information if it is
        called with a number of arguments other than two.
        """
        for args in [
            ["/bin/unbranch"],
            ["/bin/unbranch", "Foo", "bar"]]:
            err = self.assertRaises(
                SystemExit,
                unbranchMain, args)
            self.assertEqual(
                err.args,
                ("Usage: unbranch [--force] <project>",))


    def test_unbranchUnknownProject(self):
        """
        L{unbranchMain} raises L{SystemExit} with a string explaining that
        there is no such project if it is called with the name of a project
        which is unknown.
        """
        err = self.assertRaises(
            SystemExit,
            unbranchMain, ["/bin/unbranch", "Quux"])
        self.assertEqual(
            err.args,
            ("The location of %r trunk is not known.  Specify a URI as the "
             "3rd argument to check out a branch (check out trunk to make "
             "this unnecessary)." % ("Quux",),))


    def test_unbranchTrunk(self):
        """
        L{unbranchMain} raises L{SystemExit} with a string explaining that
        trunk cannot be unbranch if called with the name of a project for which
        the current active branch is trunk.
        """
        projectName = "Quux"
        self.manager.repositories[projectName] = {"trunk": {}}
        self.manager.changeProjectBranch(
            projectName, "trunk", (projectName, "trunk"))
        err = self.assertRaises(
            SystemExit,
            unbranchMain, ["/bin/unbranch", projectName])
        self.assertEqual(err.args, ("Cannot merge trunk.",))


    def test_unbranch(self):
        """
        L{unbranchMain} returns without exception when called with the name of
        a project which is known and for which the current active branch is not
        trunk.  The active branch afterwards is trunk.
        """
        projectName = "Quux"
        self.manager.repositories[projectName] = {"trunk": {},
                                                  "branches":
                                                      {"foo": {}}}
        self.manager.changeProjectBranch(
            projectName, "trunk", (projectName, "trunk"))
        self.manager.changeProjectBranch(projectName, "foo")
        unbranchMain(["/bin/unbranch", projectName])
        self.assertEqual(self.manager.currentBranchFor(projectName), "trunk")
