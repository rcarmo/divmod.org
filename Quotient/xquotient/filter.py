# -*- test-case-name: xquotient.test.test_filter -*-

"""
Defines simple, customizable rule-based Message filtering.
"""

import re

from zope.interface import implements

from twisted.python import reflect, components

from nevow import inevow, athena

from axiom import item, attributes
from axiom.iaxiom import IReliableListener
from axiom.item import Item
from axiom.tags import Catalog
from axiom.dependency import dependsOn
from axiom.upgrade import registerUpgrader

from xmantissa import ixmantissa, webnav, webtheme, liveform

from xquotient import iquotient, mail
from xquotient.mail import MessageSource
from xquotient.equotient import NoSuchHeader
from xquotient.exmess import (
    DRAFT_STATUS, OUTBOX_STATUS, BOUNCED_STATUS, SENT_STATUS)


class RuleFilteringPowerup(item.Item):
    """
    Filters messages according to a set of user-defined filtering
    rules.
    """
    typeName = 'xquotient_filter_filteringpowerup'
    schemaVersion = 2

    tagCatalog = dependsOn(Catalog, doc="""
    The catalog in which to tag items to which this action is applied.
    """)
    messageSource = dependsOn(mail.MessageSource)

    filters = attributes.inmemory()

    powerupInterfaces = (ixmantissa.INavigableElement,)
    def activate(self):
        self.filters = None

    def installed(self):
        self.messageSource.addReliableListener(self)

    def getTabs(self):
        return [webnav.Tab('Mail', self.storeID, 0.2, children=
                    [webnav.Tab('Filtering', self.storeID, 0.1)],
                authoritative=False)]


    def processItem(self, item):
        if self.filters is None:
            self.filters = list(self.powerupsFor(iquotient.IFilteringRule))
        for f in self.filters:
            matched, proceed, extraData = f.applyTo(item)
            if matched:
                f.getAction().actOn(self, f, item, extraData)
            if not proceed:
                break

def ruleFilter1to2(old):
    """
    Add messageSource field since RuleFilteringPowerup depends on
    it. Remove installedOn.
    """
    return old.upgradeVersion(RuleFilteringPowerup.typeName, 1, 2,
                              tagCatalog = old.tagCatalog,
                              messageSource = old.store.findUnique(
                                                 mail.MessageSource))

registerUpgrader(ruleFilter1to2, RuleFilteringPowerup.typeName, 1, 2)


class RuleFilterBenefactor(item.Item):
    """
    Endows users with RuleFilteringPowerup.
    """

    typeName = 'xquotient_filter_filterbenefactor'
    implements(ixmantissa.IBenefactor)
    powerupNames = ["xquotient.filter.RuleFilteringPowerup"]

    installedOn = attributes.reference()
    endowed = attributes.integer(default=0)

class MailingListFilterBenefactor(item.Item):
    """
    Endows users with MailingListFilteringPowerup.
    """
    implements(ixmantissa.IBenefactor)
    powerupNames = ["xquotient.filter.MailingListFilteringPowerup"]
    installedOn = attributes.reference()
    endowed = attributes.integer(default=0)


class FixedTagAction(item.Item):
    implements(iquotient.IFilteringAction)

    tagName = attributes.text(doc="""
    The tag to apply to items to which this action is applied.
    """)

    def __repr__(self):
        return '<FixedTagAction %r>' % (self.tagName,)


    def actOn(self, pup, rule, item, extraData):
        pup.tagCatalog.tag(item, self.tagName, rule)



class VariableTagAction(item.Item):
    implements(iquotient.IFilteringAction)

    def __repr__(self):
        return '<VariableTagAction>'


    def actOn(self, pup, rule, item, extraData):
        pup.tagCatalog.tag(item, extraData['tagName'], rule)



class MailingListTagAction(object):
    def actOn(self, pup, rule, item, extraData):
        pup.tagCatalog.tag(item, extraData['mailingListName'], rule)



EQUALS, STARTSWITH, ENDSWITH, CONTAINS = range(4)
_opsToFunctions = [
    lambda a, b: a == b,
    unicode.startswith,
    unicode.endswith,
    unicode.__contains__,
    ]
_namesToOps = {
    'equals': EQUALS,
    'startswith': STARTSWITH,
    'endswith': ENDSWITH,
    'contains': CONTAINS,
    }
_opsToNames = {
    EQUALS: 'equals',
    STARTSWITH: 'startswith',
    ENDSWITH: 'endswith',
    CONTAINS: 'contains',
    }



class HeaderRule(item.Item):
    implements(iquotient.IFilteringRule)

    headerName = attributes.text(doc="""
    Name of the header to which this rule applies.
    """, allowNone=False)

    negate = attributes.boolean(doc="""
    Take the opposite of the operation's result.
    """, default=False, allowNone=False)

    operation = attributes.integer(doc="""
    One of EQUALS, STARTSWITH, ENDSWITH, or CONTAINS.
    """, allowNone=False)

    value = attributes.text(doc="""
    Text which will be used in applying this rule.
    """, allowNone=False)

    shortCircuit = attributes.boolean(doc="""
    Stop all further processing if this rule matches.
    """, default=False, allowNone=False)

    caseSensitive = attributes.boolean(doc="""
    Consider case when applying this rule.
    """, default=False, allowNone=False)

    action = attributes.reference(doc="""
    The L{iquotient.IFilteringAction} to take when this rule matches.
    """)

    def __repr__(self):
        return '<HeaderRule on %r %s%s %r (%s%s)>' % (
            self.headerName,
            self.negate and '!' or '',
            _opsToNames[self.operation],
            self.value,
            self.caseSensitive and 'case-sensitive' or 'case-insensitive',
            self.shortCircuit and ', short-circuit' or '')


    def getAction(self):
        return self.action


    def applyToHeaders(self, headers):
        if self.caseSensitive:
            value = self.value
        else:
            value = self.value.lower()
        for hdr in headers:
            if self.caseSensitive:
                hdrval = hdr.value
            else:
                hdrval = hdr.value.lower()
            if _opsToFunctions[self.operation](hdrval, value):
                if self.negate:
                    break
                else:
                    return (True, not self.shortCircuit, None)
            else:
                if self.negate:
                    return (True, not self.shortCircuit, None)
        return (False, True, None)


    def applyTo(self, item):
        return self.applyToHeaders(item.impl.getHeaders(self.headerName))

class MailingListRule(item.Item):
    implements(iquotient.IFilteringRule)

    matchedMessages = attributes.integer(doc="""
    Keeps track of the number of messages that have been matched as mailing
    list posts.
    """, default=0)

    def __repr__(self):
        return '<MailingListRule>'


    def match_ecartis(self, headers):
        sender = headers.get('sender', [None])[0]
        xlist = headers.get('x-list', [None])[0]
        version = headers.get('x-ecartis-version', [None])[0]

        if sender and xlist:
            domain = sender.rfind('@')
            if domain != -1 and version is not None:
                return xlist + u'.' + sender[domain + 1:]


    def match_yahooGroups(self, headers, listExpr = re.compile(r'''list (?P<listId>[^;]+)''')):
        """Match messages from Yahoo Groups.

        It seems the groups which were eGroups match the Ecartis filter,
        but some groups do not.  This filter matches both the Ecartis
        yahoogroups and the others.
        """
        # Example header:
        #   Mailing-List: list nslu2-linux@yahoogroups.com; contact nslu2-linux-owner@yahoogroups.com

        # Note:
        #   ezmlm also has a "Mailing-List" header, but it provides the "help"
        #   contact address only, not the list address:
        #     Mailing-List: contact dev-help@subversion.tigris.org; run by ezmlm
        #   I don't match the ezmlm lists.  (For that, see svn rev 4561
        #   branches/glyph/ezmlm-filtering.  It matches "list-post", as appears
        #   in both ezmlm and mailman.)
        mlist = headers.get('mailing-list', [None])[0]
        if mlist is not None:
            m = listExpr.search(mlist)
            if m is not None:
                listId = m.group('listId')
                return listId.replace('@', '.')


    def match_mailman(self, headers, listExpr = re.compile(r'''<(?P<listId>[^>]*)>'''), versionHeader = 'x-mailman-version'):
        if versionHeader in headers:
            listId = headers.get('list-id', [None])[0]
            if listId is not None:
                m = listExpr.search(listId)
                if m is not None:
                    return m.group('listId')
                return listId

    def match_majorDomo(self, headers, listExpr = re.compile(r'''<(?P<listId>[^>]*)>''')):
        listId = headers.get('x-mailing-list', [None])[0]
        if listId is not None:
            m = listExpr.search(listId)
            if m is not None:
                return m.group('listId').replace(u'@', u'.')
            return listId.replace(u'@', u'.')


    def match_lyris(self, headers, listExpr = re.compile(r"""<mailto:leave-(?P<listname>.*)-.*@(?P<domain>.*)>""")):
        msgid = headers.get('message-id', [None])[0]
        unsub = headers.get('list-unsubscribe', [None])[0]
        if msgid is not None and u"LYRIS" in msgid and unsub is not None:
            m = listExpr.search(unsub)
            if m is not None:
                return u"%s.%s" % (m.group('listname'), m.group('domain'))


    def match_requestTracker(self, headers):
        ticket = headers.get('rt-ticket', [None])[0]
        managedby = headers.get('managed-by', [None])[0]
        if ticket is not None and managedby is not None:
            if managedby.startswith(u"RT"):
                return u"request-tracker"


    def match_EZMLM(self, headers, mailtoExpr = re.compile("<mailto:(.*)>")):
        # Actually, this seems to be more of a 'catch-all' filter than just
        # ezmlm; the information in the List-Id header for mailman is
        # replicated (sort of: I imagine the semantics are slightly different)
        # in the list-post header.
        lp = headers.get('list-post', [None])[0]
        if lp is not None:
            postAddress = mailtoExpr.findall(lp)
            if postAddress:
                postAddress = postAddress[0]
                return postAddress.replace(u"@", u".")


    def getAction(self):
        return MailingListTagAction()


    def applyTo(self, item):
        headers = {}
        for hdr in item.impl.getAllHeaders():
            headers.setdefault(hdr.name, []).append(hdr.value)
        matchers = reflect.prefixedMethodNames(self.__class__, 'match_')
        for m in matchers:
            tag = getattr(self, 'match_' + m)(headers)
            if tag is not None:
                self.matchedMessages += 1
                assert type(tag) is unicode, "%r was not unicode, came from %r" % (tag, m)
                return True, True, {"mailingListName": tag}
        return False, True, None


class MailingListFilteringPowerup(item.Item):
    """
    Filters mail according to the mailing list it was sent from.
    """
    schemaVersion = 2
    tagCatalog = dependsOn(Catalog, doc="""
    The catalog in which to tag items to which this action is applied.
    """)

    mailingListRule = dependsOn(MailingListRule, doc="""
    The mailing list filter used by this powerup.
    """)
    messageSource = dependsOn(mail.MessageSource)
    def installed(self):
        self.messageSource.addReliableListener(self)

    def processItem(self, item):
        matched, proceed, extraData = self.mailingListRule.applyTo(item)
        if matched:
            self.mailingListRule.getAction().actOn(self, self.mailingListRule,
                                                   item, extraData)



def mailingListFilter1to2(old):
    """
    Add messageSource field since MailingListFilteringPowerup depends
    on it. Remove installedOn.
    """
    return old.upgradeVersion(MailingListFilteringPowerup.typeName, 1, 2,
                              tagCatalog = old.tagCatalog,
                              mailingListRule = old.mailingListRule,
                              messageSource = old.store.findUnique(
                                                 mail.MessageSource))

registerUpgrader(mailingListFilter1to2, MailingListFilteringPowerup.typeName, 1, 2)


class FilteringConfigurationFragment(athena.LiveFragment):
    implements(ixmantissa.INavigableFragment)

    fragmentName = 'filtering-configuration'

    live = 'athena'

    def head(self):
        pass


    def render_existingRules(self, ctx, data):
        rule = inevow.IQ(ctx.tag).patternGenerator('rule')
        for hdrrule in self.original.store.query(HeaderRule):
            ctx.tag[rule().fillSlots(
                'headerName', hdrrule.headerName).fillSlots(
                'negate', hdrrule.negate).fillSlots(
                'operation', _opsToNames[hdrrule.operation]).fillSlots(
                'value', hdrrule.value).fillSlots(
                'shortCircuit', hdrrule.shortCircuit).fillSlots(
                'caseSensitive', hdrrule.caseSensitive).fillSlots(
                'tagName', hdrrule.action.tagName)]
        return ctx.tag


    # This stuff is just provisional.  It provides a lot of functionality in a
    # really simple way.  Later on we're going to want something a lot more
    # flexible which exposes all the stuff the model is actually capable of.
    def render_addRule(self, ctx, data):
        f = liveform.LiveForm(
            self.addRule,
            [liveform.Parameter('headerName', None, lambda s: s.strip().lower()),
             liveform.Parameter('negate', None, lambda s: bool([u"does", u"doesn't"].index(s))),
             liveform.Parameter('operation', None, _namesToOps.__getitem__),
             liveform.Parameter('value', None, unicode),
             liveform.Parameter('shortCircuit', None, bool),
             liveform.Parameter('caseSensitive', None, bool),
             liveform.Parameter('tagName', None, unicode)])
        f.jsClass = u'Quotient.Filter.RuleWidget'
        f.docFactory = webtheme.getLoader('add-filtering-rule')
        f.setFragmentParent(self)
        return ctx.tag[f]


    def addRule(self, headerName, negate, operation, value, shortCircuit, caseSensitive, tagName):
        action = self.original.store.findOrCreate(FixedTagAction, tagName=tagName)
        rule = HeaderRule(
            store=self.original.store,
            headerName=headerName,
            negate=negate,
            operation=operation,
            value=value,
            shortCircuit=shortCircuit,
            caseSensitive=caseSensitive,
            action=action)
        self.original.powerUp(rule, iquotient.IFilteringRule)

components.registerAdapter(FilteringConfigurationFragment, RuleFilteringPowerup, ixmantissa.INavigableFragment)


class Focus(Item):
    """
    Implement the rules which determine whether a message gets the focused
    status or not.
    """
    implements(IReliableListener)

    messageSource = dependsOn(MessageSource)

    def installed(self):
        self.messageSource.addReliableListener(self)


    def processItem(self, item):
        """
        Apply the focus status to any incoming message which is probably not a
        mailing list message.
        """
        for s in item.iterStatuses():
            if s in [DRAFT_STATUS, OUTBOX_STATUS, BOUNCED_STATUS, SENT_STATUS]:
                return
        part = item.impl
        try:
            getHeader = part.getHeader
        except AttributeError:
            pass
        else:
            try:
                precedence = getHeader(u'precedence')
            except NoSuchHeader:
                item.focus()
            else:
                if precedence.lower() not in (u'list', u'bulk'):
                    item.focus()


    def suspend(self):
        """
        Called when this listener is suspended.

        There is no ephemeral state for this listener so this function does
        nothing.
        """


    def resume(self):
        """
        Call when this listener is no longer suspended.

        There is no ephemeral state for this listener so this function does
        nothing.
        """
