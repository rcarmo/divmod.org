from zope.interface import implements

from nevow import inevow, athena
from nevow.taglibrary import tabbedPane

from xmantissa import ixmantissa

class PatternDictionary(object):
    def __init__(self, docFactory):
        self.docFactory = inevow.IQ(docFactory)
        self.patterns = dict()

    def __getitem__(self, i):
        if i not in self.patterns:
            self.patterns[i] = self.docFactory.patternGenerator(i)
        return self.patterns[i]

def dictFillSlots(tag, slotmap):
    for (k, v) in slotmap.iteritems():
        tag = tag.fillSlots(k, v)
    return tag

class FragmentCollector(athena.LiveFragment):
    implements(ixmantissa.INavigableFragment)

    fragmentName = None
    live = 'athena'
    title = None

    def __init__(self, translator, docFactory=None, collect=(), name='default'):
        self.name = name
        athena.LiveFragment.__init__(self, None, docFactory)

        tabs = []
        for frag in collect:
            if frag.docFactory is None:
                frag.docFactory = translator.getDocFactory(frag.fragmentName, None)
            tabs.append((frag.title, frag))
        self.tabs = tabs

    def head(self):
        for (tabTitle, fragment) in self.tabs:
            fragment.setFragmentParent(self)
            content = fragment.head()
            if content is not None:
                yield content

        yield tabbedPane.tabbedPaneGlue.inlineCSS

    def render_tabbedPane(self, ctx, data):
        tpf = tabbedPane.TabbedPaneFragment(self.tabs, name=self.name)
        tpf.setFragmentParent(self)
        return tpf
