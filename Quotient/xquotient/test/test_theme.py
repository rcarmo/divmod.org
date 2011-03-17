
"""
Tests for Quotient's theme.
"""

from twisted.trial.unittest import TestCase

from xmantissa.test.validation import XHTMLDirectoryThemeTestsMixin
from xmantissa.plugins.mailoff import plugin as quotientOffering

from xquotient.quotienttheme import QuotientTheme


class QuotientThemeTests(TestCase, XHTMLDirectoryThemeTestsMixin):
    """
    Stock L{XHTMLDirectoryTheme} tests applied to the Quotient offering and its
    theme.
    """
    theme = QuotientTheme('')
    offering = quotientOffering
