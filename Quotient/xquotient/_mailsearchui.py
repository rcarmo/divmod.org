
from zope.interface import implements

from nevow.page import renderer
from nevow import tags

from xmantissa import ixmantissa, scrolltable, webtheme

from xquotient import exmess


class SearchAggregatorFragment(webtheme.ThemedElement):
    implements(ixmantissa.INavigableFragment)

    jsClass = u'Mantissa.Search.Search'

    fragmentName = 'search'


    def __init__(self, searchResults, store):
        super(SearchAggregatorFragment, self).__init__()
        self.searchResults = searchResults
        self.store = store


    def head(self):
        return None


    def search(self, ctx, data):
        if self.searchResults:
            f = scrolltable.SearchResultScrollingFragment(
                self.store,
                self.searchResults,
                (scrolltable.UnsortableColumn(
                    exmess.Message.senderDisplay),
                 scrolltable.UnsortableColumn(
                     exmess.Message.subject),
                 scrolltable.UnsortableColumnWrapper(
                     scrolltable.TimestampAttributeColumn(
                        exmess.Message.sentWhen)),
                 scrolltable.UnsortableColumn(
                     exmess.Message.read)))
            f.jsClass = u'Quotient.Search.SearchResults'
            f.setFragmentParent(self)
            f.docFactory = webtheme.getLoader(f.fragmentName)
            return f
        return tags.h2['No results']
    renderer(search)
