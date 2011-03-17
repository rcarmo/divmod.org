# -*- test-case-name: combinator.test.test_subversion -*-

"""
Minimal API for interacting with Subversion repositories.
"""

from os import system

def createSubversionRepository(path, contents, cleanup=True, runCommand=system):
    """
    Create a new subversion repository at the given location and put the
    specified files in it.

    @type path: L{FilePath}
    @param path: The path at which to create the new repository.  This path
        should not exist yet.

    @param contents: A C{dict} mapping C{str} to either C{dict} or C{str}.  The
        keys in this C{dict} give names of top-level entries in the repository
        to be created.  A key mapped to a C{str} value will be created as a
        regular file with that value as its contents.  A key mapped to a
        C{dict} value will be created as a directory with the keys in that
        value as path entries within it.  The nesting of this structure may be
        arbitrarily deep.

        For example::

            {'trunk': {'README': 'Good things.\n'},
             'branches': {'foo-bar': {'README': 'Better things.\n'}}}

    @param runCommand: A one-argument callable which takes a string and
        executes it as a shell command.

    @rtype: C{None}
    """
    working = path.sibling('working')
    runCommand("svnadmin create " + path.path)
    if contents:
        runCommand("svn co file://" + path.path + " " + working.path)
        _createFiles(working, contents, runCommand)
        runCommand("svn commit -m 'Create specified files' " + working.path)
        if cleanup:
            working.remove()


def _createFiles(path, contents, runCommand):
    for entry, innards in contents.iteritems():
        if isinstance(innards, str):
            regular = path.child(entry)
            regular.setContent(innards)
            runCommand("svn add " + regular.path)
        else:
            directory = path.child(entry)
            directory.makedirs()
            runCommand("svn add " + directory.path)
            _createFiles(directory, innards, runCommand)


def commit(path, message, runCommand=system):
    """
    Commit outstanding changes in the working copy indicated by C{path} using
    the specified commit message.

    @param path: The working copy with outstanding changes to commit.
    @type path: L{FilePath}

    @param message: The commit message to use.
    @type message: C{str}
    """
    runCommand("svn commit -m '%s' %s" % (message, path.path))

