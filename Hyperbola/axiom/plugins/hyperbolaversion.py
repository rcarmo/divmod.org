# Copyright 2008 Divmod, Inc.
# See LICENSE file for details

"""
Register an Axiom version plugin for Hyperbola.
"""

from zope.interface import directlyProvides
from twisted.plugin import IPlugin
from axiom.iaxiom import IVersion
from hyperbola import version
directlyProvides(version, IPlugin, IVersion)
