from xmantissa import stats
from twisted.application import internet, service
from vertex import juice
f = juice.JuiceServerFactory()
f.log = open("stats.log",'a')
f.protocol = stats.SimpleRemoteStatsCollector

application = service.Application("statcollector")
internet.TCPServer(8787, f).setServiceParent(application)
