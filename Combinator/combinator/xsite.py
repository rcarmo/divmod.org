# -*- test-case-name: combinator.test.test_xsite -*-
"""
Some functions copied from site.py and improved to not modify sys.path
directly.
"""
import os
try:
    set
except NameError:
    from sets import Set as set
from site import makepath


def _init_pathinfo(syspath):
    """
    Return a set containing all existing directory entries from C{syspath}.

    @param syspath: A list of filesystem path strings to directories containing
    Python packages and modules.
    """
    d = set()
    for dir in syspath:
        try:
            if os.path.isdir(dir):
                dir, dircase = makepath(dir)
                d.add(dircase)
        except TypeError:
            continue
    return d



def addsitedir(sitedir, syspath):
    """
    Add C{sitedir} argument to C{syspath} argument if missing and handle .pth
    files in C{sitedir}.

    @return: A list of filesystem path strings.
    """
    known_paths = _init_pathinfo(syspath)
    reset = 1
    sitedir, sitedircase = makepath(sitedir)
    if not sitedircase in known_paths:
        syspath.append(sitedir)        # Add path component
    names = os.listdir(sitedir)
    names.sort()
    for name in names:
        if name.endswith(os.extsep + "pth"):
            addpackage(sitedir, name, known_paths, syspath)
    if reset:
        known_paths = None
    return known_paths



def addpackage(sitedir, name, known_paths, syspath):
    """
    Add a new path to C{known_paths} by combining C{sitedir} and C{name} or
    execute C{sitedir} if it starts with 'import'.

    @return: C{known_paths}, or None if the given new path does not exist.
    """
    fullname = os.path.join(sitedir, name)
    f = open(fullname, "rU")
    try:
        for line in f:
            if line.startswith("#"):
                continue
            if line.startswith("import"):
                exec line
                continue
            line = line.rstrip()
            dir, dircase = makepath(sitedir, line)
            if not dircase in known_paths and os.path.exists(dir):
                syspath.append(dir)
                known_paths.add(dircase)
    finally:
        f.close()
    return known_paths
