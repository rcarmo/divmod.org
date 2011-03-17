# -*- test-case-name: xmantissa.test.test_signup -*-

from twisted.python.filepath import FilePath
from twisted.mail.pop3 import IMailbox
from twisted.mail.smtp import IMessageDelivery

from axiom import iaxiom, scheduler, userbase

from xmantissa import website, offering

from xquotient.inbox import Inbox
from xquotient.compose import Composer
from xquotient.quotientapp import MessageSearchProvider
from xquotient.quotienttheme import QuotientTheme
from xquotient.grabber import GrabberConfiguration
from xquotient.extract import ExtractPowerup
from xquotient.popout import POP3Up
from xquotient.filter import MailingListFilteringPowerup, RuleFilteringPowerup, Focus
from xquotient.spam import SpambayesFilter
from xquotient.qpeople import MessageLister
from xquotient import mail,  popout
import xquotient


plugin = offering.Offering(
    name = u'Quotient',

    description = u'''
    A mail system with a web UI, supporting SMTP and POP3.
    ''',

    siteRequirements = (
        (userbase.IRealm, userbase.LoginSystem),
        (None, website.WebSite),
        (None, popout.POP3Listener),
        (None, mail.MailTransferAgent)),

    appPowerups = (),
    installablePowerups = ((u'quotient', u'Incoming SMTP, Address Book', Inbox),
                           (u'Extracts', u'Data-driven feature discovery, extraction, and presentation',ExtractPowerup),
                           (u'Indexing', u'Full-text email (and other stuff) indexing', MessageSearchProvider),
                           (u'Grabbers',  u'Remote message retrieval', GrabberConfiguration),
                           (u'Sending Mail', u'Allows message transmission', Composer),
                           (u'POP Server', u'Access to mail via POP3',POP3Up),
                           (u'Rule Filtering', u'User-customizable filtering of messages based on headers and such.',
                            RuleFilteringPowerup),
                           (u'Mailing List Filtering', u'Automatic filtering of messages sent by various mailing list managers.',
                            MailingListFilteringPowerup),
                           (u'Focus', u'Highly filtered message view.', Focus),
                           (u'Quotient People Plugins', u'Per-person Image/Extract/Picture lists', MessageLister),
                           (u'Spambayes-based trainable Ham/Spam Filtering',
                            u'Filtering of messages based on a bayesian classification with per-user training information.',
                            SpambayesFilter)),
    loginInterfaces = [(IMessageDelivery, "SMTP logins"),
                       (IMailbox, "POP3 logins")],
    themes = [QuotientTheme('base', 0)],
    version = xquotient.version,
    staticContentPath = FilePath(xquotient.__file__).sibling('static'))
