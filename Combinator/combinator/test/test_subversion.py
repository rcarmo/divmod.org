
"""
Tests for L{combinator.subversion}.
"""

from twisted.trial.unittest import TestCase
from twisted.python.filepath import FilePath

from combinator.subversion import createSubversionRepository, commit


class CreateSubversionRepositoryTests(TestCase):
    """
    Tests for L{createSubversionRepository}.

    @ivar commands: A list of the commands which have been executed.
    """

    def setUp(self):
        self.commands = []
        self.repository = FilePath(self.mktemp())
        self.workingCopy = self.repository.sibling('working')


    def runCommand(self, command):
        """
        Record the execution of a command.  Inspect the command and create a
        directory if it is an "svn co" command.
        """
        if self.workingCopy.isdir():
            children = list(self.workingCopy.walk())
            children.remove(self.workingCopy)
        else:
            children = None
        self.commands.append((command, children))
        if command.startswith("svn co "):
            self.workingCopy.makedirs()


    def test_emptyRepository(self):
        """
        L{createSubversionRepository} should create a repository with no
        entries or revisions if it is passed an empty dictionary.
        """
        createSubversionRepository(self.repository, {}, False, self.commands.append)
        self.assertEqual(
            self.commands,
            ["svnadmin create " + self.repository.path])


    def _fileTest(self, entry, contents):
        """
        """
        createSubversionRepository(
            self.repository, {entry: contents}, False, self.runCommand)

        repo = self.repository.path
        wc = self.workingCopy.path
        self.assertEqual(
            self.commands,
            [("svnadmin create " + repo, None),
             ("svn co file://" + repo + " " + wc, None),
             ("svn add " + self.workingCopy.child(entry).path,
              [self.workingCopy.child(entry)]),
             ("svn commit -m 'Create specified files' " + self.workingCopy.path,
              [self.workingCopy.child(entry)])])


    def test_emptyFile(self):
        """
        L{createSubversionRepository} should create a repository with one empty
        file in it if passed a dictionary with one key mapped to the empty
        string.
        """
        entry = 'filename'
        contents = ''
        self._fileTest(entry, contents)
        self.assertEqual(self.workingCopy.child(entry).getContent(), contents)


    def test_fileWithContents(self):
        """
        L{createSubversionRepository} should create a repository with a file
        with the contents given as the corresponding value.
        """
        entry = 'filename'
        contents = 'some bytes\n'
        self._fileTest(entry, contents)
        self.assertEqual(
            self.workingCopy.child(entry).getContent(), contents)


    def test_directory(self):
        """
        L{createSubversionRepository} should create a directory for a key with
        a C{dict} as a value.
        """
        entry = 'dirname'
        contents = {}
        self._fileTest(entry, contents)
        self.assertTrue(self.workingCopy.child(entry).isdir())


    def test_directoryContainingFile(self):
        """
        For a key associated with a value of a C{dict} with a key associated
        with a value of a C{str}, L{createSubversionRepository} should create a
        directory containing a file with the specified string as its content.
        """
        directory = 'dirname'
        file = 'filename'
        content = 'bytes'
        createSubversionRepository(
            self.repository,
            {directory: {file: content}},
            False,
            self.runCommand)

        repo = self.repository.path
        wc = self.workingCopy.path
        self.assertEqual(
            self.commands,
            [("svnadmin create " + repo, None),
             ("svn co file://" + repo + " " + wc, None),
             ("svn add " + self.workingCopy.child(directory).path,
              [self.workingCopy.child(directory)]),
             ("svn add " + self.workingCopy.child(directory).child(file).path,
              [self.workingCopy.child(directory),
               self.workingCopy.child(directory).child(file)]),
             ("svn commit -m 'Create specified files' " + self.workingCopy.path,
              [self.workingCopy.child(directory),
               self.workingCopy.child(directory).child(file)])])


    def test_workingCopyRemoved(self):
        """
        The temporary working copy should be deleted after
        L{createSubversionRepository} is finished using it to populate the
        repository if C{True} is passed for the I{cleanup} parameter.
        """
        createSubversionRepository(
            self.repository, {'file': 'bytes'}, True, self.runCommand)
        self.workingCopy.restat(False)
        self.assertFalse(self.workingCopy.exists())


    def test_commit(self):
        """
        Changes in the working copy passed to L{commit} are committed to the
        repository.
        """
        commit(self.workingCopy, "change stuff about", self.runCommand)
        self.assertEquals(
            self.commands,
            [("svn commit -m 'change stuff about' " + self.workingCopy.path, None)])
