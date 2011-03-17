from zope.interface import implements

from axiom.item import Item, declareLegacyItem, POWERUP_BEFORE
from axiom import attributes
from axiom.upgrade import (registerAttributeCopyingUpgrader,
                           registerUpgrader)
from axiom.dependency import dependsOn

from xmantissa import ixmantissa, prefs, webnav, fulltext

from xquotient import mail, spam, _mailsearchui
from xquotient.exmess import MessageDisplayPreferenceCollection
from xquotient.grabber import GrabberConfiguration


class MessageSearchProvider(Item):
    """
    Wrapper around an ISearchProvider which will hand back search results
    wrapped in a fragment that knows about Messages.
    """

    schemaVersion = 2

    indexer = dependsOn(fulltext.PyLuceneIndexer, doc="""
    The actual fulltext indexing implementation object which will perform
    searches.  The results it returns will be wrapped up in a fragment which
    knows how to display L{exmess.Message} instances.
    """)

    messageSource = dependsOn(mail.MessageSource)
    powerupInterfaces = (ixmantissa.ISearchProvider,)

    def installed(self):
        self.indexer.addSource(self.messageSource)
    def count(self, term):
        raise NotImplementedError("No one should ever call count, I think.")


    def search(self, *a, **k):
        if 'sortAscending' not in k:
            k['sortAscending'] = False
        d = self.indexer.search(*a, **k)
        d.addCallback(_mailsearchui.SearchAggregatorFragment, self.store)
        return d

declareLegacyItem(MessageSearchProvider.typeName, 1, dict(
    indexer=attributes.reference(),
    installedOn=attributes.reference()))

def _messageSearchProvider1to2(old):
    new = old.upgradeVersion(MessageSearchProvider.typeName, 1, 2,
                             indexer=old.indexer,
                             messageSource=old.store.findUnique(mail.MessageSource))
    return new
registerUpgrader(_messageSearchProvider1to2, MessageSearchProvider.typeName, 1, 2)

class QuotientBenefactor(Item):
    implements(ixmantissa.IBenefactor)

    typeName = 'quotient_benefactor'
    schemaVersion = 1

    endowed = attributes.integer(default=0)
    powerupNames = ["xquotient.inbox.Inbox"]

class ExtractBenefactor(Item):
    implements(ixmantissa.IBenefactor)

    endowed = attributes.integer(default=0)
    powerupNames = ["xquotient.extract.ExtractPowerup",
                    "xquotient.gallery.Gallery",
                    "xquotient.gallery.ThumbnailDisplayer"]

class QuotientPeopleBenefactor(Item):
    implements(ixmantissa.IBenefactor)

    endowed = attributes.integer(default=0)
    powerupNames = ["xquotient.qpeople.MessageLister"]

class IndexingBenefactor(Item):
    implements(ixmantissa.IBenefactor)

    endowed = attributes.integer(default=0)
    powerupNames = ["xquotient.quotientapp.MessageSearchProvider"]



class QuotientPreferenceCollection(Item, prefs.PreferenceCollectionMixin):
    """
    The core Quotient L{xmantissa.ixmantissa.IPreferenceCollection}.  Doesn't
    collect any preferences, but groups some quotient settings related fragments
    """
    implements(ixmantissa.IPreferenceCollection)

    typeName = 'quotient_preference_collection'
    schemaVersion = 3

    installedOn = attributes.reference()

    powerupInterfaces = (ixmantissa.IPreferenceCollection,)

    def getPreferenceParameters(self):
        return ()

    def getSections(self):
        # XXX This is wrong because it is backwards.  This class cannot be
        # responsible for looking for every item that might exist in the
        # database and want to provide configuration, because plugins make it
        # impossible for this class to ever have a complete list of such items.
        # Instead, items need to act as plugins for something so that there
        # mere existence in the database causes them to show up for
        # configuration.
        sections = []
        for cls in GrabberConfiguration, spam.Filter:
            item = self.store.findUnique(cls, default=None)
            if item is not None:
                sections.append(item)
        if sections:
            return sections
        return None

    def getTabs(self):
        return (webnav.Tab('Mail', self.storeID, 0.0),)

registerAttributeCopyingUpgrader(QuotientPreferenceCollection, 1, 2)

declareLegacyItem(QuotientPreferenceCollection.typeName, 2,
                  dict(installedOn=attributes.reference(),
                       preferredMimeType=attributes.text(),
                       preferredMessageDisplay=attributes.text(),
                       showRead=attributes.boolean(),
                       showMoreDetail=attributes.boolean()))

def quotientPreferenceCollection2To3(old):
    """
    Remove the preference attributes of
    L{xquotient.quotientapp.QuotientPreferenceCollection}, and install
    a L{xquotient.exmess.MessageDisplayPreferenceCollection}, because
    the attributes have either been moved there, or removed entirely
    """
    mdpc = MessageDisplayPreferenceCollection(
        store=old.store,
        preferredFormat=old.preferredMimeType)
    mdpc.installedOn = old.store
    old.store.powerUp(mdpc, ixmantissa.IPreferenceCollection, POWERUP_BEFORE)

    return old.upgradeVersion('quotient_preference_collection', 2, 3,
                              installedOn=old.installedOn)

registerUpgrader(quotientPreferenceCollection2To3, 'quotient_preference_collection', 2, 3)

