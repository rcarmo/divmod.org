"""Really Simple Syndication.

Provides a Page subclass which renders an RSS 2.0 feed for a given channel.
"""

from nevow import inevow, loaders, rend, tags
from zope.interface import implements

_RSS_TAGS = (
    'rss', 'channel', 'link', 'title', 'copyright', 'description',
    'item', 'author', 'pubDate', 'guid', 'language', 'lastBuildDate')
RSS = type(
    'RSS',
    (object,),
    dict([(k, tags.Proto(k)) for k in _RSS_TAGS]))

class Feed(rend.Page):
    implements(inevow.IResource)
    """
    @type original: A L{hyperbola.hyperblurb.Blurb}.
    @ivar original: The item whose children are to be rendered.

    @type title: C{unicode}
    @ivar title: This channel's title

    @type link: C{str}
    @ivar link: The URL associated with this channel

    @type description: C{str}
    @ivar description: A summary of the purpose of this channel

    @type copyright: C{str}
    @ivar copyright: An implement of the power structure employed towards
    the oppression of the working class.

    @type language: C{str}
    @ivar language: The language of this channel, eg C{"en-us"}

    @type timestamp: L{epsilon.extime.Time}
    @ivar timestamp: The time and date at which this channel last changed.
    """
    def __init__(self, parent):
        rend.Page.__init__(self, parent)
        self.title = parent.original.title
        self.link = parent._absoluteURL()
        self.description = parent.original.body
        self.copyright = ""
        self.language = "en-us"
        self.timestamp = (parent.original.dateLastEdited or
                          parent.original.dateCreated or
                          Time())

    def renderHTTP(self, ctx):
        inevow.IRequest(ctx).setHeader('content-type', 'text/xml')
        return rend.Page.renderHTTP(self, ctx)

    def render_channelInfo(self, ctx, data):
        yield RSS.title[self.title]
        yield RSS.link[self.link]
        yield RSS.description[self.description]
        yield RSS.copyright[self.copyright]
        yield RSS.language[self.language]
        yield RSS.lastBuildDate[self.timestamp.asRFC2822()]

    def render_items(self, ctx, data):
        request = inevow.IRequest(ctx)
        for item in self.original._getChildBlurbViews(
            self.original._getChildBlurbs(request)):
            yield RSS.item[
                RSS.title[item.original.title],
                RSS.link[item._absoluteURL()],
                RSS.description[item.original.body],
                RSS.author[item.original.author.externalID],
                RSS.pubDate[(item.original.dateLastEdited or
                            item.original.dateCreated or
                            Time()).asRFC2822()]]

    docFactory = loaders.stan(RSS.rss(version="2.0")[
        RSS.channel[
            render_channelInfo,
            render_items]])
