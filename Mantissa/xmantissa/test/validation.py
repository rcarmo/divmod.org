
"""
Test utilities providing coverage for implementations of Mantissa interfaces.
"""

from epsilon.descriptor import requiredAttribute

from xmantissa.webtheme import XHTMLDirectoryTheme


class XHTMLDirectoryThemeTestsMixin:
    """
    Mixin defining tests for themes based on L{XHTMLDirectoryTheme}.

    Mix this in to a L{twisted.trial.unittest.TestCase} and set C{theme} and
    C{offering}.

    @ivar theme: An instance of the theme to be tested.  Set this.
    @ivar offering: The offering which includes the theme.  Set this.
    """
    theme = requiredAttribute('theme')
    offering = requiredAttribute('offering')

    def test_stylesheet(self):
        """
        The C{stylesheetLocation} of the theme being tested identifies an
        existing file beneath the offering's static content path.
        """
        self.assertTrue(isinstance(self.theme, XHTMLDirectoryTheme))
        self.assertEqual(self.theme.stylesheetLocation[0], 'static')
        self.assertEqual(self.theme.stylesheetLocation[1], self.offering.name)
        path = self.offering.staticContentPath
        for segment in self.theme.stylesheetLocation[2:]:
            path = path.child(segment)
        self.assertTrue(path.exists(),
                        "Indicated stylesheet %r does not exist" % (path,))



