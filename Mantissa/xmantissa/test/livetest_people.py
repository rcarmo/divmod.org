import sys

from nevow import tags
from nevow.livetrial.testcase import TestCase

from axiom.store import Store
from axiom.dependency import installOn

from xmantissa import people, ixmantissa
from xmantissa.liveform import FORM_INPUT
from xmantissa.webtheme import getLoader
from xmantissa.webapp import PrivateApplication

class AddPersonTestBase(people.AddPersonFragment):
    jsClass = None

    def __init__(self):
        self.store = Store()
        organizer = people.Organizer(store=self.store)
        installOn(organizer, self.store)
        people.AddPersonFragment.__init__(self, organizer)


    def getWidgetDocument(self):
        return tags.invisible(render=tags.directive('addPersonForm'))


    def mangleDefaults(self, params):
        """
        Called before rendering the form to give tests an opportunity to
        modify the defaults for the parameters being used.

        @type params: L{list} of liveform parameters
        @param params: The parameters which will be used by the liveform
            being rendered.
        """


    def checkResult(self, positional, keyword):
        """
        Verify that the given arguments are the ones which were expected by
        the form submission.  Override this in a subclass.

        @type positional: L{tuple}
        @param positional: The positional arguments submitted by the form.

        @type keyword: L{dict}
        @param keyword: The keyword arguments submitted by the form.
        """
        raise NotImplementedError()


    def addPerson(self, *a, **k):
        """
        Override form handler to just check the arguments given without
        trying to modify any database state.
        """
        self.checkResult(a, k)


    def render_addPersonForm(self, ctx, data):
        liveform = super(AddPersonTestBase, self).render_addPersonForm(ctx, data)

        # XXX This is a pretty terrible hack.  The client-side of these tests
        # just submit the form.  In order for the assertions to succeed, that
        # means the form needs to be rendered with some values in it already.
        # There's no actual API for putting values into the form here, though.
        # So instead, we'll grovel over all the parameters and try to change
        # them to reflect what we want.  Since this relies on there being no
        # conflictingly named parameters anywhere in the form and since it
        # relies on the parameters being traversable in order to find them all,
        # this is rather fragile.  The tests should most likely just put values
        # in on the client or something along those lines (it's not really
        # clear what the intent of these tests are, anyway, so it's not clear
        # what alternate approach would satisfy that intent).
        params = []
        remaining = liveform.parameters[:]
        while remaining:
            p = remaining.pop()
            if p.type == FORM_INPUT:
                remaining.extend(p.coercer.parameters)
            else:
                params.append((p.name, p))
        self.mangleDefaults(dict(params))
        return liveform



class OnlyNick(AddPersonTestBase, TestCase):
    jsClass = u'Mantissa.Test.OnlyNick'

    def mangleDefaults(self, params):
        """
        Set the nickname in the form to a particular value for
        L{checkResult} to verify when the form is submitted.
        """
        params['nickname'].default = u'everybody'


    def checkResult(self, positional, keyword):
        """
        There should be no positional arguments but there should be keyword
        arguments for each of the two attributes of L{Person} and three more
        for the basic contact items.  Only the nickname should have a value.
        """
        self.assertEqual(positional, ())
        self.assertEqual(
            keyword,
            {'nickname': u'everybody',
             'vip': False,
             'xmantissa.people.PostalContactType': [{'address': u''}],
             'xmantissa.people.EmailContactType': [{'email': u''}]})



class NickNameAndEmailAddress(AddPersonTestBase, TestCase):
    jsClass = u'Mantissa.Test.NickNameAndEmailAddress'

    def mangleDefaults(self, params):
        """
        Set the nickname and email address to values which L{checkResult}
        can verify.
        """
        params['nickname'].default = u'NICK!!!'
        params['xmantissa.people.EmailContactType'].parameters[0].default = u'a@b.c'


    def checkResult(self, positional, keyword):
        """
        Verify that the nickname and email address set in L{mangleDefaults}
        are submitted.
        """
        self.assertEqual(positional, ())
        self.assertEqual(
            keyword,
            {'nickname': u'NICK!!!',
             'vip': False,
             'xmantissa.people.PostalContactType': [{'address': u''}],
             'xmantissa.people.EmailContactType': [{'email': u'a@b.c'}]})
