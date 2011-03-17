
"""
Tests for Quotient's theme.
"""

from twisted.trial.unittest import TestCase

from xmantissa.test.validation import XHTMLDirectoryThemeTestsMixin
from xmantissa.plugins.hyperbolaoff import plugin as hyperbolaOffering

from hyperbola.hyperbola_theme import HyperbolaTheme


class HyperbolaThemeTests(TestCase, XHTMLDirectoryThemeTestsMixin):
    """
    Stock L{XHTMLDirectoryTheme} tests applied to the Hyperbola offering and its
    theme.
    """
    theme = HyperbolaTheme('')
    offering = hyperbolaOffering
