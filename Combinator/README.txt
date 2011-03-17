
Purpose
=======

Combinator is a convenience utility for developers working on a large number of
Python projects simultaneously (like me).  The goal is that you can use
Combinator to easily set up a large number of projects on both Linux and
Windows environments.


Usage
=====

On UNIX, put this into your shell's startup file (currently only bash and zsh
are supported, patches for other shells accepted):

    eval `python .../your/projects/Divmod/trunk/Combinator/environment.py`


On Windows, path setup is less straighforward so Combinator is mainly concerned
with setting up your sys.path.  You can use it by setting your PYTHONPATH
environment variable to point to:
    .../your/projects/Divmod/trunk/Combinator/environment.py

It can then generate a batch file for you; in a cmd.exe shell, you can type
something like:

    C:\> python Y:\Divmod\trunk\Combinator\environment.py > paths.bat
    C:\> paths

to set both %PYTHONPATH% and %PATH% environment variables.  This will only
affect one shell, however.

To integrate with development tools such as Pythonwin, you will need to
(instead of running the previous commands) set your PYTHONPATH to point to
...\Divmod\trunk\Combinator\

On Windows, you will have to prefix commandlines with something like:

        "python c:\python24\python.exe Y:\Divmod\trunk\Combinator\bin\"

To use the various Divmod projects, when you are done with this
path-setup, you should run the following commands:

        % chbranch Divmod trunk
        % chbranch Twisted trunk svn://svn.twistedmatrix.com/svn/Twisted/trunk

Also, you will have to install platform versions of OpenSSL, PyOpenSSL
(0.6 or better), SQLite (3.0.8 or better) PySQLite (2.0 or better),
and, obviously, Python - using the appropriate Windows installers,
RPMs, Ubuntu packages or whatever.  Source installs can also be done
with 'setup.py install' of all the various dependencies after
installing Combinator, since Combinator's dependencies are extremely
light (Python only, basically) and they will be installed in ~/.local.
