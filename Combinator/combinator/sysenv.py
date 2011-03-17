# -*- test-case-name: combinator.test.test_sysenv -*-

import sys
import os

PATHVARS = 'PYTHONPATH', 'PATH', 'LD_LIBRARY_PATH', 'PATHEXT'

def uniq(l):
    tmpd = {}
    nl = []
    for x in l:
        if not tmpd.has_key(x):
            nl.append(x)
            tmpd[x] = 1
    return nl

class Env:
    """
    This object represents a set of modifications to a program's environment,
    and specifically, modifications to a set of paths in that environment.
    """
    def __init__(self, stream=sys.stdout, environ=os.environ):
        """
        Create an environment manipulator.

        @param stream: a writable file-like object, defaulting to stdout, where
        changes will be serialized.

        @param environ: a mapping of strings to strings representing the base
        environment that this object will emit changes to.
        """
        self._d = {}
        self.stream = stream
        for k, v in environ.items():
            if k in PATHVARS:
                v = [(0, x) for x in uniq(v.split(os.pathsep)) if x]
            self._d[k] = v
        self.d = {}

    def __setitem__(self, k, v):
        self.d[k] = v

    def setupList(self, k):
        if not self.d.has_key(k):
            if self._d.has_key(k):
                self.d[k] = self._d[k]
            else:
                self.d[k] = []

    def prePath(self, k, *paths):
        self.setupList(k)
        for path in paths:
            self.d[k].insert(0, (-1, path))

    def postPath(self, k, *paths):
        self.setupList(k)
        for path in paths:
            self.d[k].append((1, path))

    def export(self, how):
        """
        Write a set of appropriate environment-modification statements to my
        output stream.  For example, for a bourne-style shell, a set of export
        X="Y" statements, or for Emacs, a set of (setenv "X" "Y") expressions.

        @param how: the short name of the program which describes how the
        changes should be serialized.  Should be one of: emacs, tcsh, bat, msh,
        zsh, bash.  If it is not one of those, changes will be written in the
        style of a POSIX shell with no special features.  For bash and zsh,
        extra code will also be written that initialize combinator's
        interactive completion support.

        @return: None
        """
        z = self.d.items()
        z.sort()                # output the variables in a consistent order,
                                # for easy viewing with 'diff' etc.
        if how == 'emacs':
            fstr = '(setenv "%s" "%s")'
            ffunc = lambda x: x.replace("\\", "\\\\").replace('"', '\\"')
        else:
            ffunc = repr
            if how == 'tcsh':
                fstr = 'setenv %s %s ;'
            elif how == 'bat':
                ffunc = lambda x: x # Windows does not like quoting in SET
                                    # lines at *all*
                fstr = 'set %s=%s'
            elif how == 'msh':
                fstr = '$env:%s=%s'
            else:
                fstr = 'export %s=%s;'
        fstr += '\n'
        for k, v in z:
            if isinstance(v, list):
                v = os.pathsep.join(uniq([x[1] for x in v]))
            self.stream.write(fstr % (k, ffunc(v)))

        combinator = os.path.split(os.path.split(__file__)[0])[0]

        if how == 'zsh':
            self.stream.write("""
            fpath=($fpath %s)
            """ % os.path.join(combinator, "zsh"))
        elif how == 'bash':
            self.stream.write(
                ". " + os.path.join(combinator, "bash", "completion") + "\n")


def generatePythonPathVariable(nv):
    """
    Generate a PYTHONPATH environment variable and modify an environment object
    accordingly.

    @param nv: an L{Env} object, the environment to be modified.
    """
    nv.prePath('PYTHONPATH', os.path.split(os.path.split(__file__)[0])[0])


def generatePathVariable(nv, svnProjectsDir=None, sitePathsPath=None,
                         stream=sys.stderr, syspath=None):
    """
    Generate various path environment variables to point at Combinator-managed
    and user-local installation locations (PATH, PATHEXT on Windows,
    LD_LIBRARY_PATH on Unix) and modify an environment object accordingly, as
    well as generating a cache of script files for commands in
    Combinator-managed projects.  If the directories which these environment
    variables would point at do not exist, create them.

    @param nv: an L{Env} object, the environment to be modified.

    @param syspath: The list of paths to modify.

    @param svnProjectsDir: the pathname of the "Projects" directory, where
    everything is kept.  If unspecified, I will try to guess according to the
    current environment and the path of this module.

    @type svnProjectsDir: L{str}

    @param sitePathsPath: the pathname of the "combinator_paths" directory,
    where state-tracking information will be kept (the names of current
    branches, and the runnable scripts).
    @type sitePathsPath: L{str}

    @param stream: a file-like object to write notifications of filesystem
    manipulations to.  Defaults to stderr.

    @return: The branch manager representing the new environment.
    """
    from combinator import branchmgr
    # We instantiate a new branch manager here rather than using
    # theBranchManager because this is invoked by the 'environment' script,
    # which takes arguments to explicitly set these values.  theBranchManager
    # in this case represents the environment we were launched in, whereas this
    # new branch manager represents the environment of python processes run
    # under shells that read the environment this script produces.
    m = branchmgr.BranchManager(svnProjectsDir, sitePathsPath, syspath)

    nv.prePath('PATH', m.binCachePath)
    if os.name == 'nt':
        nv.postPath('PATHEXT', '.PY')
    userBinPath = os.path.abspath(
        os.path.expanduser("~/.local/bin"))
    userLibPath = os.path.abspath(
        os.path.expanduser("~/.local/lib"))
    if os.path.exists(userBinPath):
        nv.prePath("PATH", userBinPath)
    if os.path.exists(userLibPath):
        nv.prePath("LD_LIBRARY_PATH", userLibPath)

    nv.d['COMBINATOR_PROJECTS'] = m.svnProjectsDir
    nv.d['COMBINATOR_PATHS'] = m.sitePathsPath
    return m

userShell = os.environ.get('SHELL', '')

def gethow():
    if len(sys.argv) > 1:
        return sys.argv[1]
    if sys.platform == 'win32':
        return 'bat'
    elif 'zsh' in userShell:
        return 'zsh'
    elif 'bash' in userShell:
        return 'bash'
    else:
        return 'sh'

def export(svnProjectsDir=None, sitePathsPath=None):
    e = Env()
    generatePythonPathVariable(e)
    m = generatePathVariable(e, svnProjectsDir, sitePathsPath)
    m.addPaths()
    how = gethow()
    e.export(how)
    m.createExecutables()
