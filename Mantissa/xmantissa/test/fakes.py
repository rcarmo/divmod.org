# Copyright 2008 Divmod, Inc. See LICENSE file for details
# -*- test-case-name: xmantissa.test.test_webapp.AuthenticatedWebViewerTests,xmantissa.test.test_publicweb.AnonymousWebViewerTests -*-
"""
A collection of fake versions of various objects used in tests.

There are a lot of classes here because many of them have model/view
interactions that are expressed through adapter registrations, so having
additional types is helpful.
"""

from zope.interface import implements

from twisted.python.components import registerAdapter

from epsilon.structlike import record

from nevow.athena import LiveElement, LiveFragment
from nevow.page import Element
from nevow import rend, loaders
from nevow.inevow import IResource

from xmantissa.ixmantissa import INavigableFragment


class FakeLoader(record('name')):
    """
    A fake Nevow loader object.
    """



class FakeTheme(record('themeName loaders')):
    """
    A placeholder for theme lookup.

    @ivar loaders: A dict of strings to loader objects.

    @ivar themeName: A name that describes this theme.
    """

    def getDocFactory(self, name, default=None):
        """
        @param name: A loader name.
        """
        return self.loaders.get(name, default)



class FakeModel(object):
    """
    A simple 'model' object that does nothing, for the purposes of adaptation.
    """



class ResourceViewForFakeModel(rend.Page):
    """
    Implementor of L{IResource} for L{FakeModel}.
    """

registerAdapter(ResourceViewForFakeModel, FakeModel, IResource)



class _HasModel(object):
    """
    A mixin that provides a 'model' attribute for Element subclasses.

    This is a simple hack that attempts to cooperatively invoke __init__ so
    that its numerous subclasses don't have to define a constructor.  If you
    want to use it you should read its implementation.
    """
    def __init__(self, model):
        """
        Set the model attribute and delegate to the other subclass.
        """
        self.model = model
        self.__class__.__bases__[1].__init__(self)



class FakeElementModel(object):
    """
    A simple 'model' object that does nothing, for the purposes of adaptation.
    """



class ElementViewForFakeModel(_HasModel, Element):
    """
    L{Element} implementor of L{INavigableFragment} for L{FakeElementModel}.
    """
    implements(INavigableFragment)
    docFactory = loaders.stan('')

registerAdapter(ElementViewForFakeModel, FakeElementModel, INavigableFragment)



class FakeElementModelWithTheme(object):
    """
    A simple 'model' object that does nothing, for the purposes of adaptation
    to L{ElementViewForFakeModelWithTheme}.
    """



class ElementViewForFakeModelWithTheme(_HasModel, Element):
    """
    L{Element} implementor of L{INavigableFragment} for L{FakeElementModel}.
    """
    implements(INavigableFragment)
    fragmentName = 'awesome_page'

registerAdapter(ElementViewForFakeModelWithTheme, FakeElementModelWithTheme,
                INavigableFragment)



class FakeElementModelWithDocFactory(record('loader')):
    """
    A simple 'model' object that does nothing, for the purposes of adaptation
    to L{ElementViewForFakeModelWithDocFactory}.

    @ivar loader: A loader object (to be used as the view's docFactory).
    """



class ElementViewForFakeModelWithDocFactory(_HasModel, Element):
    """
    L{Element} implementor of L{INavigableFragment} for L{FakeElementModel}.
    """
    implements(INavigableFragment)

    def __init__(self, original):
        """
        Set docFactory and proceed as usual.
        """
        _HasModel.__init__(self, original)
        self.docFactory = original.loader



registerAdapter(ElementViewForFakeModelWithDocFactory, FakeElementModelWithDocFactory,
                INavigableFragment)



class FakeElementModelWithThemeAndDocFactory(record('fragmentName loader')):
    """
    A simple 'model' object that does nothing, for the purposes of adaptation
    to L{ElementViewForFakeModelWithThemeAndDocFactory}.
    """



class ElementViewForFakeModelWithThemeAndDocFactory(_HasModel, Element):
    """
    L{Element} implementor of L{INavigableFragment} for L{FakeElementModel}.
    """
    implements(INavigableFragment)

    def __init__(self, original):
        """
        Set docFactory and proceed as usual.
        """
        _HasModel.__init__(self, original)
        self.docFactory = original.loader
        self.fragmentName = original.fragmentName


registerAdapter(ElementViewForFakeModelWithThemeAndDocFactory,
                FakeElementModelWithThemeAndDocFactory,
                INavigableFragment)




class FakeFragmentModel(object):
    """
    A simple 'model' object that does nothing, for the purposes of adaptation.
    """



class FragmentViewForFakeModel(rend.Fragment):
    """
    L{Fragment} implementor of L{INavigableFragment} for L{FakeFragmentModel}.
    """
    implements(INavigableFragment)
    docFactory = loaders.stan('')

registerAdapter(FragmentViewForFakeModel, FakeFragmentModel, INavigableFragment)



class FakeLiveElementModel(object):
    """
    A simple 'model' object that does nothing, for the purposes of adaptation.
    """



class LiveElementViewForFakeModel(_HasModel, LiveElement):
    """
    L{LiveElement} Implementor of L{INavigableFragment} for
    L{FakeLiveElementModel}.
    """
    implements(INavigableFragment)
    docFactory = loaders.stan('')

registerAdapter(LiveElementViewForFakeModel, FakeLiveElementModel,
                INavigableFragment)



class FakeLiveFragmentModel(object):
    """
    A simple 'model' object that does nothing, for the purposes of adaptation.
    """



class LiveFragmentViewForFakeModel(LiveFragment):
    """
    L{LiveFragment} Implementor of L{INavigableFragment} for
    L{FakeLiveFragmentModel}.
    """
    implements(INavigableFragment)
    docFactory = loaders.stan('')

    @classmethod
    def wrap(cls, model):
        """
        Wrap the given model in this class.  Implement this as a method in this
        file so that the warning filename will match up...
        """
        return cls(model)

registerAdapter(LiveFragmentViewForFakeModel.wrap, FakeLiveFragmentModel,
                INavigableFragment)

class FakeElementModelWithLocateChildView(object):
    """
    A simple 'model' object that does nothing, for the purposes of adaptation.
    """
    def __init__(self, children, beLive):
        """
        @param children: an iterable of children to be returned from the view's
        locateChild.
        """
        self.childs = iter(children) # implemented this way because we want to
                                     # see an error if locateChild is called
                                     # too many times; often this will be a
                                     # sequence of length 1
        self.beLive = beLive


    def __conform__(self, interface):
        """
        @param interface: IResource (for which there is no adapter) or
        INavigableFragment (for which there is one, depending on this model's
        liveness).
        """
        if interface is not INavigableFragment:
            return None
        if self.beLive:
            return LiveElementViewForModelWithLocateChild(self)
        else:
            return ElementViewForFakeModelWithLocateChild(self)



class _HasLocateChild(_HasModel):
    """
    Has a locateChild that delegates to its model.
    """
    implements(INavigableFragment)
    docFactory = loaders.stan('')

    def locateChild(self, ctx, segments):
        """
        Stub implementation that merely records whether it was called.
        """
        return self.model.childs.next()



class LiveElementViewForModelWithLocateChild(_HasLocateChild, LiveElement):
    """
    Live element with a locateChild.
    """



class ElementViewForFakeModelWithLocateChild(_HasLocateChild, Element):
    """
    Non-live element with a locateChild.
    """


class FakeCustomizableElementModel(object):
    """
    A simple 'model' object that does nothing, for the purposes of adaptation.
    """
    username = None
    def custom(self, username):
        """
        Record the username our view was customized with.
        """
        self.username = username



class ElementViewForFakeCustomizableElementModel(_HasModel, Element):
    """
    An L{Element} that delegates C{customizeFor} calls to its model.
    """
    implements(INavigableFragment)
    docFactory = loaders.stan('')

    def customizeFor(self, username):
        """
        Delegate to model.
        """
        self.model.custom(username)
        return self

registerAdapter(ElementViewForFakeCustomizableElementModel,
                FakeCustomizableElementModel,
                INavigableFragment)


class FakeElementModelWithHead(record('head')):
    """
    A simple 'model' object that does nothing, for the purposes of adaptation.
    """

    def _head(self):
        return self.head


class ElementViewForFakeModelWithHead(_HasModel, Element):
    """
    L{Element} implementor of L{INavigableFragment} for L{FakeElementModel}.
    """
    implements(INavigableFragment)
    docFactory = loaders.stan('')

    def head(self):
        return self.model._head()

registerAdapter(ElementViewForFakeModelWithHead, FakeElementModelWithHead,
                INavigableFragment)
