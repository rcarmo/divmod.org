# Copyright (c) 2006 Divmod.
# See LICENSE for details.

"""
Runs mantissa javascript tests as part of the mantissa python tests
"""

from nevow.testutil import JavaScriptTestCase

class MantissaJavaScriptTestCase(JavaScriptTestCase):
    """
    Run all the mantissa javascript test
    """

    def test_scrollmodel(self):
        """
        Test the model object which tracks most client-side state for any
        ScrollTable.
        """
        return 'Mantissa.Test.TestScrollModel'


    def test_placeholders(self):
        """
        Test the model objects which track placeholder nodes in the message
        scrolltable.
        """
        return 'Mantissa.Test.TestPlaceholder'


    def test_autocomplete(self):
        """
        Tests the model object which tracks client-side autocomplete state
        """
        return 'Mantissa.Test.TestAutoComplete'


    def test_region(self):
        """
        Test the model objects which track placeholder nodes in the message
        scrolltable.
        """
        return 'Mantissa.Test.TestRegionModel'


    def test_people(self):
        """
        Tests the model objects which deal with the address book and person
        objects.
        """
        return 'Mantissa.Test.TestPeople'


    def test_validate(self):
        """
        Test the class which validates input on the signup page and posts it to
        the server.
        """
        return 'Mantissa.Test.TestValidate'


    def test_liveform(self):
        """
        Test the LiveForm widgets.
        """
        return 'Mantissa.Test.TestLiveForm'


    def test_domReplace(self):
        """
        Test the stuff which replaces things in the DOM.
        """
        return 'Mantissa.Test.TestDOMReplace'


    def test_offering(self):
        """
        Tests for the offering administration interface.
        """
        return 'Mantissa.Test.TestOffering'
