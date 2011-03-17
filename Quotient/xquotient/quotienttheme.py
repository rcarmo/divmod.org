# -*- test-case-name: xquotient.test.test_theme -*-

from xmantissa.webtheme import XHTMLDirectoryTheme

class QuotientTheme(XHTMLDirectoryTheme):
    """
    Quotient's style information, which resides in the 'static' directory.
    """
    stylesheetLocation = ['static', 'Quotient', 'quotient.css']
