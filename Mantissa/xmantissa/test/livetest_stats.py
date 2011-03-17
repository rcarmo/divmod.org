import datetime

from nevow.livetrial import testcase
from nevow import loaders, tags, athena

from epsilon import extime

from xmantissa import webadmin


class AdminStatsTestBase(webadmin.AdminStatsFragment):
    docFactory = loaders.stan(tags.div(render=tags.directive('liveElement')))

    def _initializeObserver(self):
        pass


    def getGraphNames(self):
        return [(u"graph1", u"graph 1"), (u"graph2", u"graph 2")]
    athena.expose(getGraphNames)


    def fetchLastHour(self, name):
        t = extime.Time()
        return ([unicode((t + datetime.timedelta(minutes=i)).asHumanly())
                 for i in range(60)],
                [24, 28, 41, 37, 39, 25, 44, 32, 41, 45, 44, 47, 24, 28,
                 29, 49, 43, 56, 28, 35, 66, 43, 72, 65, 62, 56, 84, 52,
                 74, 73, 74, 77, 71, 46, 70, 55, 65, 51, 42, 55, 19, 30,
                 25, 24, 20, 16, 39, 22, 39, 29, 29, 18, 39, 19, 21, 12,
                 25, 25, 25, 29])


    def buildPie(self):
        self.queryStats = {u'beans': 10, u'enchiladas': 27, u'salsa': 3,
                           u'fajitas': 48}
        self.pieSlices()
    athena.expose(buildPie)



class StatsTestCase(testcase.TestCase):
    jsClass = u'Mantissa.Test.StatsTest'
    docFactory = loaders.stan(
        tags.div(render=tags.directive('liveTest'))[
            tags.invisible(render=tags.directive('start'))])


    def render_start(self, ctx, data):
        self.testfragment = AdminStatsTestBase()
        self.testfragment.setFragmentParent(self)
        return self.testfragment


    def run(self):
        self.testfragment.statUpdate(extime.Time(), [(u'graph1', 43)])
        self.testfragment.queryStatUpdate(extime.Time(), [(u'beans', 2)])
    athena.expose(run)
