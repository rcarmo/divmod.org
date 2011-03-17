# -*- test-case-name: hyperbola.test.test_theme -*-

"""
This module contains a Mantissa web theme plugin which includes Hyperbola's
style information.
"""

from xmantissa.webtheme import XHTMLDirectoryTheme


class HyperbolaTheme(XHTMLDirectoryTheme):
    """
    Hyperbola's style information, which resides in the 'static' directory.
    """
    stylesheetLocation = ['static', 'Hyperbola', 'hyperbola.css']
