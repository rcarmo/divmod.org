# -*- test-case-name: combinator -*-

"""
Local and remote subversion branch manipulation functionality.

This provides the implementation for the mkbranch, chbranch, unbranch, and
whbranch command line tools.
"""

import os
from combinator import xsite
import sys


class InvalidParameter(Exception):
    """
    An operation could not be performed because one or more of the parameters
    was invalid.
    """


class DuplicateBranch(InvalidParameter):
    """
    An attempt was made to create a branch with the same name as an existing branch.
    """


class NonExistentBranch(InvalidParameter):
    """
    An attempt was made to use a branch which does not exist.
    """



class InvalidBranch(InvalidParameter):
    """
    An attempt was made to use a branch in a way which is not allowed for that
    branch.
    """


class MissingCreationRevision(ValueError):
    """
    The revision at which a branch was created could not be determined.
    """



class MissingTrunkLocation(InvalidParameter):
    """
    A checkout of the trunk branch of a project could not be performed because
    the location of the trunk branch is unknown and was not specified.
    """



class UncleanTrunkWorkingCopy(ValueError):
    """
    A merge of the current branch into trunk couldn't be performed because the
    trunk working copy contains uncommitted changes.
    """



_cmdLineQuoteRe = None

def _cmdLineQuote(s):
    global _cmdLineQuoteRe
    if _cmdLineQuoteRe is None:
        import re
        _cmdLineQuoteRe = re.compile(r'(\\*)"')
    if ' ' in s or '"' in s:
        return '"' + _cmdLineQuoteRe.sub(r'\1\1\\"', s) + '"'
    return s



def prompt(s):
    p = os.getcwd().replace(os.path.expanduser('~'), '~')
    return p + '$ ' + s



def warn(*a, **k):
    import warnings
    warnings.warn(*a, **k)



def commandString(args):
    """
    Format an argument list so it can be run with popen.

    @type args: sequence
    @param args: The argument list to format

    @rtype: C{str}
    @return: A quoted string which can be passed to a shell to run a
        command.
    """
    return ' '.join(map(_cmdLineQuote, args))



def runCommand(command):
    """
    Execute a command and return its standard output and exit code.

    @type command: C{str}
    @param command: A string suitable to be passed to popen.

    @return: a two-tuple of the standard output and exit code of the
        command.
    """
    pipe = os.popen(command)
    output = pipe.read()
    code = pipe.close() or 0
    return output, code



def runcmd(*args):
    """
    Execute a command, possibly prompting the user before doing so, and then
    display its output.
    """
    popenstr = commandString(args)
    print prompt(popenstr)

    output, code = runCommand(popenstr)

    print 'C: ' + '\nC: '.join(output.splitlines())
    return checkStatus(popenstr, output, code)



def checkStatus(popenstr, output, code):
    """
    Check the exit status of a command and return its output if it ran
    successfully or raise an exception if it exited abnormally.
    """
    if os.name == 'nt':
        # There is nothing we can possibly do with this error code.
        return output
    if os.WIFSIGNALED(code):
        raise ValueError("Command: %r exited with signal: %d" % (
            popenstr, os.WTERMSIG(code)))
    elif os.WIFEXITED(code):
        status = os.WEXITSTATUS(code)
        if status:
            raise ValueError("Command: %r exited with status: %d" % (
                popenstr, status))
        else:
            return output
    else:
        raise ValueError("Command: %r exited with unexpected code: %d" % (
            popenstr, code))



def subversionURLExists(url):
    """
    Return true if the given SVN URL exists, false otherwise.
    """
    command = commandString(['svn', 'ls', url, '2>/dev/null'])
    output, code = runCommand(command)
    try:
        checkStatus(command, output, code)
    except ValueError:
        return False
    else:
        return True



def parse(*a, **k):
    # We're in the critical path for sitecustomize, so let's not import
    # anything that we don't need to.
    from xml.dom.minidom import parse
    return parse(*a, **k)

    # Yes, I know I wrote microdom, but this is a stdlib feature and microdom
    # is not.  this module really can't use *anything* outside the stdlib,
    # because one of its primary purposes is managing the path of your Twisted
    # install!!



def childWithName(element, name):
    for child in element.childNodes:
        if child.localName == name:
            return child
    return None



def getText(element):
    text = []
    for child in element.childNodes:
        assert child.nodeType == child.TEXT_NODE
        text.append(child.data)
    return "".join(text)



def addSiteDir(fsPath, syspath):
    """
    Add C{fsPath} to C{syspath} and remove all preceding entries, if it's not
    already present.
    """
    if fsPath not in syspath:
        chop = len(syspath)
        xsite.addsitedir(fsPath, syspath)
        # Put everything at the beginning of the path (overriding the site
        # installation directory), since Python likes to put it at the end.
        spc = syspath[chop:]
        del syspath[chop:]
        syspath[0:0] = spc
    elif 0:                     # We SHOULD emit a warning here, but all kinds
                                # of tests set PYTHONPATH invalidly and cause
                                # havoc.
        warn("Duplicate path entry %r" % (fsPath,),
             UserWarning )


def inHiddenDirectory(dirpath):
    """
    @param dirpath: a filesystem path string.
    @return: whether C{dirpath} is within a dotfile directory.
    """
    for segment in os.path.normpath(dirpath).split(os.sep):
        if segment.startswith('.'):
            return True
    return False



def scriptsPresentIn(directory):
    """
    Collect all scripts present in C{directory}.
    @param directory: A filesystem path string.
    @return: An iterator of all scripts in C{directory}.
    """
    for dirpath, dirnames, filenames in os.walk(directory):
        if inHiddenDirectory(dirpath):
            # Don't descend into hidden directories, e.g. ".svn"
            continue
        for filename in filenames:
            if (filename not in ('cham.py', 'cham.bat')
                # let's skip these combinator-internal scripts.
                and not filename.startswith(".")):
                    # and hidden files
                yield filename



class BranchManager:
    def __init__(self, svnProjectsDir=None, sitePathsPath=None, syspath=None):
        """
        @param syspath: The list of paths this branch manager will modify.

        @param svnProjectsDir: a path to a group of SVN repositories arranged
        in the structure:

            <dir>/ProjectName/trunk/
            <dir>/ProjectName/branches/username/branchname/
            <dir>/ProjectName/branches/username/branch2/
            <dir>/Project2/trunk/
            <dir>/Project2/branches/username/branchname/
            <dir>/Project2/branches/username/branch2/

        Combinator will modify this directory by running SVN commands to check
        out new branches, run merges, and similar stuff.

        @param sitePathsPath: A path to a directory of files with this simple
        structure:

            <dir>/ProjectName.bch
            <dir>/Project2.bch

        .bch files in this context are text files which contain the branch name
        of the most current branch for a particular project.  A branch name, in
        this context, is a relative path from the project's SVN /branches
        directory.  For example, the branch path of
        'svn+ssh://example.com/svn/Foo/branches/quasimodo/your-branch/' is
        'quasimodo/your-branch'.

        'trunk' is a special branch path, which, obviously, points to
        'svn+ssh://example.com/svn/Foo/trunk/'


        The path pointing to each branch thus specified will be added not only
        to C{syspath}, but also as a site directory, so .pth files in it will be
        respected (so that multi-project repositories such as the Divmod
        repository can be activated).

        If the optional arguments are not provided, C{svnProjectsDir} and
        C{sitePathsPath} will be initialized from the C{COMBINATOR_PROJECTS},
        C{COMBINATOR_PATHS} environment variables respectively, or, if those
        are not set, using an heuristic to locate the relative position of the
        startup script assuming that it is part of a Divmod repository checkout
        in the canonical directory structure described above. If no argument is
        provided for C{syspath}, it will be initialized from C{sys.path}.
        """
        if syspath is None:
            syspath = sys.path
        if svnProjectsDir is None:
            svnProjectsDir = (os.getenv('COMBINATOR_PROJECTS') or
                              getDefaultPath())
        if sitePathsPath is None:
            sitePathsPath = (os.getenv('COMBINATOR_PATHS') or
                             os.path.join(svnProjectsDir, "combinator_paths"))
        self.syspath = syspath
        self.svnProjectsDir = os.path.abspath(svnProjectsDir)
        self.sitePathsPath = os.path.abspath(sitePathsPath)
        self.binCachePath = os.path.join(sitePathsPath, 'bincache')

    def projectBranchDir(self, projectName, branchPath='trunk'):
        """
        Return the absolute path to the given branch of the given project.
        """
        if branchPath == 'trunk':
            return os.path.abspath(
                os.path.join(self.svnProjectsDir, projectName, branchPath))
        return os.path.abspath(
            os.path.join(self.svnProjectsDir, projectName, 'branches',
                         branchPath))


    def addPaths(self):
        for fsp in self.getPaths():
            addSiteDir(fsp, self.syspath)


    def getCurrentBranches(self):
        if not os.path.isdir(self.sitePathsPath):
            return
        for yth in os.listdir(self.sitePathsPath):
            if yth.endswith('.bch'):
                yth = os.path.join(self.sitePathsPath, yth)
                projName = os.path.splitext(os.path.split(yth)[-1])[0]
                branchPath = file(yth).read().strip()
                yield projName, branchPath


    def getPaths(self):
        """
        Yield all .bch-file paths as well as a locally-installed directory.
        """
        for projName, branchPath in self.getCurrentBranches():
            fsPath = self.projectBranchDir(projName, branchPath)
            noTrunk = False
            if not os.path.exists(fsPath):
                if branchPath != 'trunk':
                    m = "branch %s:%s at %r does not exist, trying trunk" % (
                        projName, branchPath, fsPath)
                    warn(m, UserWarning)
                    trunkFsPath = self.projectBranchDir(projName)
            if os.path.isdir(fsPath):
                yield fsPath
            else:
                warn('Not even trunk existed for %r' % (projName,),
                     UserWarning )

        # platform-specific entry

        majorMinor = sys.version[0:3]
        if sys.platform.startswith('win'):
            yield (os.path.abspath(
                    os.path.expanduser("~/Python/Lib/site-packages")))
        else:
            userSitePackages = os.path.abspath(
                os.path.expanduser(
                    "~/.local/lib/python%s/site-packages" % (majorMinor,)))
            if os.path.exists(userSitePackages):
                yield userSitePackages


    def currentBranchFor(self, projectName):

        return file(os.path.join(self.sitePathsPath, projectName)+'.bch'
                    ).read().strip()


    def newProjectBranch(self, projectName, branchName):
        """
        Create a new branch of trunk of the given project.

        @type projectName: C{str}
        @param projectName: The name of the project, already known by this
            Combinator configuration, for which to create a branch.

        @type branchName: C{str}
        @param branchName: The new branch's name.
        """
        trunkURI = self.projectBranchURI(projectName, 'trunk')
        branchURI = self.projectBranchURI(projectName, branchName)
        if subversionURLExists(branchURI):
            raise DuplicateBranch(branchName)
        runcmd('svn', 'cp', trunkURI, branchURI, '-m',
               'Branching to %r' % (branchName,))
        self.changeProjectBranch(projectName, branchName, revert=False)


    def mergeProjectBranch(self, projectName, force=False):
        originalWorkingDirectory = os.getcwd()
        try:
            try:
                currentBranch = self.currentBranchFor(projectName)
            except IOError:
                raise MissingTrunkLocation(projectName)
            if currentBranch == "trunk":
                raise InvalidBranch()
            branchDir = self.projectBranchDir(projectName, currentBranch)
            os.chdir(branchDir)
            rev = None
            for node in parse(os.popen("svn log --stop-on-copy --xml")
                              ).documentElement.childNodes:
                if hasattr(node, 'getAttribute'):
                    rev = node.getAttribute("revision")
            if rev is None:
                raise MissingCreationRevision("No revision found")
            trunkDir = self.projectBranchDir(projectName)
            os.chdir(trunkDir)
            if not force:
                statusf = runcmd('svn', 'status', '--quiet')
                for line in statusf.splitlines():
                    if line[0] == 'M' or line[0] == 'A':
                        raise UncleanTrunkWorkingCopy()
            runcmd('svn', 'up')
            runcmd('svn', 'merge', '--non-interactive',
                   branchDir + "/@" + rev,
                   branchDir + "/@HEAD")
            self.changeProjectBranch(projectName, 'trunk')
        finally:
            os.chdir(originalWorkingDirectory)


    def changeProjectBranch(self, projectName, branchRelativePath,
                            branchURI=None, revert=True):
        """
        Swap which branch of a particular project we are 'working on'.  Adjust
        path files to note this difference.

        @type projectName: C{str}
        @param projectName: The name of the project for which to swap the
            active branch.

        @type branchRelativePath: C{str}
        @param branchRelativePath: The name of the branch to make active.

        @type branchURI: C{str} or C{NoneType}
        @param branchURI: The URI of the trunk branch for the given project.
            This must be provided if it has not previously been supplied.

        @type revert: C{bool}
        @param revert: A flag indicating whether to revert the copy of the
            trunk working-copy before switching it to the specified branch.

        @raise IOError: The project's trunk branch URI was not supplied and
            is not known.
        """
        branchURIWasNone = (branchURI is None)
        originalWorkingDirectory = os.getcwd()
        try:
            import shutil

            branchDirectory = self.projectBranchDir(projectName,
                                                    branchRelativePath)
            trunkDirectory = self.projectBranchDir(projectName)
            if (branchRelativePath == 'trunk' and not os.path.exists(
                    trunkDirectory)):
                if branchURI is None:
                    raise MissingTrunkLocation(projectName)
                runcmd("svn", "co", branchURI, trunkDirectory)

            if not os.path.exists(branchDirectory):
                if branchURI is None:
                    branchURI = self.projectBranchURI(
                        projectName, branchRelativePath)

                if not subversionURLExists(branchURI):
                    if branchURIWasNone:
                        raise NonExistentBranch(branchRelativePath)
                    else:
                        raise NonExistentBranch(branchURI)

                bchDir = os.path.join(self.svnProjectsDir, projectName, 'branches')

                if not os.path.exists(bchDir):
                    os.makedirs(bchDir)
                tempname = branchDirectory + ".TRUNK"
                ftd = os.path.dirname(tempname)
                if not os.path.exists(ftd):
                    os.makedirs(ftd)
                try:
                    shutil.copytree(trunkDirectory, tempname, True)
                except KeyboardInterrupt:
                    shutil.rmtree(tempname)
                    raise
                os.chdir(tempname)
                if revert:
                    runcmd("svn", "revert", ".", '-R')
                    # no really, revert
                    statusf = runcmd('svn','status','--no-ignore')
                    for line in statusf.splitlines():
                        if line[0] == '?' or line[0] == 'I':
                            unknownFile = line[7:].strip()
                            print 'removing unknown:', unknownFile
                            if os.path.isdir(unknownFile):
                                shutil.rmtree(unknownFile)
                            else:
                                os.remove(unknownFile)
                runcmd("svn", "switch", branchURI)
                os.chdir('..')
                os.rename(tempname, branchDirectory)

            if not os.path.exists(self.sitePathsPath):
                os.makedirs(self.sitePathsPath)

            f = file(os.path.join(self.sitePathsPath, projectName) + '.bch', 'w')
            f.write(branchRelativePath)
            f.close()
        finally:
            os.chdir(originalWorkingDirectory)


    def projectBranchURI(self, projectName, branchRelativePath):
        trunkDirectory = self.projectBranchDir(projectName)
        if not os.path.exists(trunkDirectory):
            raise MissingTrunkLocation(projectName)
        doc = parse(os.popen("svn info --xml " + trunkDirectory))
        info = doc.documentElement
        assert info.localName == "info", "root element is not <info>"
        entry = childWithName(info, "entry")
        url = childWithName(entry, "url")
        uri = getText(url).encode("utf-8")
        uri = "/".join(uri.split('/')[:-1])
        if branchRelativePath == 'trunk':
            branchURI = uri + '/trunk'
        else:
            branchURI = '/'.join([uri, 'branches', branchRelativePath])
        return branchURI


    def createExecutables(self, stream=sys.stderr):
        """
        Create scripts for executing files in the /bin subdirs of project
        branches found on C{syspath}. Report progress to C{stream}.

        @type stream: A file-like object.
        """
        if not os.path.isdir(self.binCachePath):
            os.makedirs(self.binCachePath)
        for ent in self.syspath:
            branchBinDir = os.path.join(ent, 'bin')
            if os.path.isdir(branchBinDir):
                for binary in scriptsPresentIn(branchBinDir):
                    dst = os.path.join(self.binCachePath,
                                       binary)
                    if os.name == 'nt':
                        dst += '.py'
                    src = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                       'bin', 'cham.py')
                    if not os.path.exists(dst):
                        stream.write('link: %r => %r\n <on account of %r>\n' %
                                     (dst, src, ent))
                        file(dst, 'w').write(file(src).read())
                        if os.name != 'nt':
                            os.chmod(dst, 0755)



def splitall(p):
    car, cdr = os.path.split(p)
    if not cdr:
        return [car]
    else:
        return splitall(car) + [cdr]



def getDefaultPath():
    # Am I somewhere I recognize?
    saf = splitall(__file__)
    if not saf[-5:-2] == ['Divmod', 'trunk', 'Combinator']:
        warn(
            'Combinator sitecustomize located outside of Combinator directory,'
            ' aborting (try passing --projects-dir)')
        return
    return os.path.join(*saf[:-5])



def _combinatorUsage(executable, info):
    """
    Exit with the given usage information.

    @type executable: C{str}
    @param executable: The name of the executable being exited.

    @type info: C{str}
    @param info: Information about how to correctly invoke this executable.

    @raise SystemExit: Always raised with a user-readable usage string.
    """
    raise SystemExit("Usage: %s %s" % (os.path.basename(executable), info))



def _combinatorMain(operation, *args):
    """
    Run a branch manager operation and handle expected errors by presenting
    them in a user-friendly manner and exiting.

    @param operation: A branch manager callable to invoke.
    @param *args: Positional arguments to pass to C{operation}.

    @return: Whatever is returned by C{operation(*args)}.

    @raise SystemExit: Raised if an exception of known type is raised by the
        branch manager operation.
    """
    try:
        return operation(*args)
    except MissingTrunkLocation, e:
        raise SystemExit(
            "The location of %r trunk is not known.  Specify a URI as the "
            "3rd argument to check out a branch (check out trunk to make "
            "this unnecessary)." % e.args)
    except NonExistentBranch, e:
        raise SystemExit(
            "No such branch: %r" % e.args)
    except DuplicateBranch, e:
        raise SystemExit(
            "Branch named %r exists already." % e.args)
    except UncleanTrunkWorkingCopy:
        raise SystemExit(
            "Can't unbranch while trunk working copy contains modifications.")
    except InvalidBranch, e:
        raise SystemExit("Cannot merge trunk.")



def chbranchMain(args):
    """
    Change the active branch of a project.  This is the main function for
    C{chbranch} command.

    @param args: A list of 3 or 4 elements:
      1. The name of the chbranch executable.
      2. The name of the project on which to operate.
      3. The name of the branch to which to change.
      4. The version control URI of the branch.  This is only required when
         changing to trunk for the first time.
    """
    if 3 <= len(args) <= 4:
        return _combinatorMain(theBranchManager.changeProjectBranch, *args[1:])
    _combinatorUsage(args[0], "<project> <branch name> [trunk url]")



def whbranchMain(args):
    """
    Display the active branch of a project.  This is the main function for
    C{whbranch} command.

    @param args: A list of one or two elements:
      1. The name of the whbranch executable.
      2. The name of a project.  If not specified, the active branch for all
         managed projects will be displayed.
    """
    if len(args) == 1:
        whichBranch = None
    elif len(args) == 2:
        whichBranch = args[1]
    else:
        _combinatorUsage(args[0], "[project]")

    for k, v in _combinatorMain(theBranchManager.getCurrentBranches):
        if whichBranch is not None:
            if k == whichBranch:
                print v
                break
        else:
            print k + ":", v



def unbranchMain(args):
    """
    Merge the active branch of a project into the trunk working copy of that
    project.  This is the main function for the C{unbranch} command.

    @param args: A list of two elements:
      1. The name of the unbranch executable.
      2. The name of the project for which to merge a branch.
    """
    force = False
    if "--force" in args:
        force = True
        args.remove("--force")
    if len(args) == 2:
        return _combinatorMain(theBranchManager.mergeProjectBranch,
                               args[1], force)
    _combinatorUsage(args[0], "[--force] <project>")



def mkbranchMain(args):
    """
    Create a new branch for a project and make it active.  This is the main
    function for the C{mkbranch} command.

    @param args: A list of three elements:
      1. The name of the mkbranch executable.
      2. The name of the project for which to create a new branch.
      3. The name to give to the newly created branch.
    """
    if len(args) == 3:
        return _combinatorMain(theBranchManager.newProjectBranch, *args[1:])
    _combinatorUsage(args[0], "<project> <branch name>")


theBranchManager = BranchManager()
