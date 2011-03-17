# -*- test-case-name: xmantissa.test.test_stats -*-
# Copyright 2008 Divmod, Inc.  See LICENSE file for details

"""
Statistics collection and recording facility.

This is a system for sending locally recorded stats data to remote observers
for further processing or storage.

Example::
  twisted.python.log.msg(interface=axiom.iaxiom.IStatEvent, foo=1, bar=2, ...)
"""

from zope.interface import implements

from twisted.application import service
from twisted.protocols import policies
from twisted.python import log
from twisted.protocols.amp import AMP, Command, AmpList, Unicode

from axiom import iaxiom, item, attributes, upgrade

from xmantissa.ixmantissa import IBoxReceiverFactory


class StatUpdate(Command):
    """
    L{StatUpdate} is sent by the server to clients connected to it each time a
    stat log event is observed.  The command contains the information from the
    event.
    """
    requiresAnswer = False

    arguments = [
        ('data', AmpList([("key", Unicode()), ("value", Unicode())])),
        ]



class RemoteStatsCollectorFactory(item.Item):
    """
    A collector of stats for things that are remote (factory).
    """
    powerupInterfaces = (IBoxReceiverFactory,)
    implements(*powerupInterfaces)

    protocol = u"http://divmod.org/ns/mantissa-stats"

    _unused = attributes.integer(
        doc="""
        meaningless attribute, only here to satisfy Axiom requirement for at
        least one attribute.
        """)

    def getBoxReceiver(self):
        """
        Create a new AMP protocol for delivering stats information to a remote
        process.
        """
        return RemoteStatsCollector()



class RemoteStatsCollector(AMP):
    """
    An AMP protocol for sending stats to remote observers.
    """
    def startReceivingBoxes(self, sender):
        """
        Start observing log events for stat events to send.
        """
        AMP.startReceivingBoxes(self, sender)
        log.addObserver(self._emit)


    def stopReceivingBoxes(self, reason):
        """
        Stop observing log events.
        """
        AMP.stopReceivingBoxes(self, reason)
        log.removeObserver(self._emit)


    def _emit(self, event):
        """
        If the given event is a stat event, send a I{StatUpdate} command.
        """
        if (event.get('interface') is not iaxiom.IStatEvent and
            'athena_send_messages' not in event and
            'athena_received_messages' not in event):
            return

        out = []
        for k, v in event.iteritems():
            if k in ('system', 'message', 'interface', 'isError'):
                continue
            if not isinstance(v, unicode):
                v = str(v).decode('ascii')
            out.append(dict(key=k.decode('ascii'), value=v))
        self.callRemote(StatUpdate, data=out)



class BandwidthMeasuringProtocol(policies.ProtocolWrapper):
    """
    Wraps a Protocol and sends bandwidth stats to a BandwidthMeasuringFactory.
    """

    def write(self, data):
        self.factory.registerWritten(len(data))
        policies.ProtocolWrapper.write(self, data)


    def writeSequence(self, seq):
        self.factory.registerWritten(sum(map(len, seq)))
        policies.ProtocolWrapper.writeSequence(self, seq)


    def dataReceived(self, data):
        self.factory.registerRead(len(data))
        policies.ProtocolWrapper.dataReceived(self, data)



class BandwidthMeasuringFactory(policies.WrappingFactory):
    """
    Collects stats on the number of bytes written and read by protocol
    instances from the wrapped factory.
    """

    protocol = BandwidthMeasuringProtocol

    def __init__(self, wrappedFactory, protocolName):
        policies.WrappingFactory.__init__(self, wrappedFactory)
        self.name = protocolName


    def registerWritten(self, length):
        log.msg(interface=iaxiom.IStatEvent, **{"stat_bandwidth_" + self.name + "_up": length})


    def registerRead(self, length):
        log.msg(interface=iaxiom.IStatEvent, **{"stat_bandwidth_" + self.name + "_down": length})


__all__ = [
    'StatUpdate', 'RemoteStatsCollectorFactory', 'RemoteStatsCollector',
    ]

# Older stuff, mostly deprecated or not useful, you probably don't want to look
# below here. -exarkun

statDescriptions = {
    "page_renders": "Nevow page renders per minute",
    "messages_grabbed": "POP3 messages grabbed per minute",
    "messagesSent": "SMTP messages sent per minute",
    "messagesReceived": "SMTP messages received per minute",
    "mimePartsCreated": "MIME parts created per minute",
    "cache_hits": "Axiom cache hits per minute",
    "cursor_execute_time": "Seconds spent in cursor.execute per minute",
    "cursor_blocked_time": ("Seconds spent waiting for the database lock per "
                            "minute"),
    "commits": "Axiom commits per minute",
    "cache_misses": "Axiom cache misses per minute",
    "autocommits": "Axiom autocommits per minute",
    "athena_messages_sent": "Athena messages sent per minute",
    "athena_messages_received": "Athena messages received per minute",

    "actionDuration": "Seconds/Minute spent executing Imaginary Commands",
    "actionExecuted": "Imaginary Commands/Minute executed",

    "bandwidth_http_up": "HTTP KB/sec received",
    "bandwidth_http_down": "HTTP KB/sec sent",
    "bandwidth_https_up": "HTTPS KB/sec sent",
    "bandwidth_https_down": "HTTPS KB/sec received",
    "bandwidth_pop3_up": "POP3 server KB/sec sent",
    "bandwidth_pop3_down":"POP3 server KB/sec received",
    "bandwidth_pop3s_up":"POP3S server KB/sec sent",
    "bandwidth_pop3s_down": "POP3S server KB/sec received",
    "bandwidth_smtp_up": "SMTP server KB/sec sent",
    "bandwidth_smtp_down": "SMTP server KB/sec received",
    "bandwidth_smtps_up": "SMTPS server KB/sec sent",
    "bandwidth_smtps_down": "SMTPS server KB/sec received",
    "bandwidth_pop3-grabber_up": "POP3 grabber KB/sec sent",
    "bandwidth_pop3-grabber_down": "POP3 grabber KB/sec received",
    "bandwidth_sip_up": "SIP KB/sec sent",
    "bandwidth_sip_down": "SIP KB/sec received",
    "bandwidth_telnet_up": "Telnet KB/sec sent",
    "bandwidth_telnet_down": "Telnet KB/sec received",
    "bandwidth_ssh_up": "SSH KB/sec sent",
    "bandwidth_ssh_down": "SSH KB/sec received",

    "Imaginary logins": "Imaginary Logins/Minute",
    "Web logins": "Web Logins/Minute",
    "SMTP logins": "SMTP Logins/Minute",
    "POP3 logins": "POP3 Logins/Minute",
    }


class StatBucket(item.Item):
    """
    Obsolete.  Only present for schema compatibility.  Do not use.
    """
    schemaVersion = 2
    type = attributes.text(doc="A stat name, such as 'messagesReceived'")
    value = attributes.ieee754_double(default=0.0, doc='Total number of events for this time period')
    interval = attributes.text(doc='A time period, e.g. "quarter-hour" or "minute" or "day"')
    index = attributes.integer(doc='The position in the round-robin list for non-daily stats')
    time = attributes.timestamp(doc='When this bucket was last updated')
    attributes.compoundIndex(interval, type, index)
    attributes.compoundIndex(index, interval)


class QueryStatBucket(item.Item):
    """
    Obsolete.  Only present for schema compatibility.  Do not use.
    """
    type = attributes.text("the SQL query string")
    value = attributes.ieee754_double(default=0.0, doc='Total number of events for this time period')
    interval = attributes.text(doc='A time period, e.g. "quarter-hour" or "minute" or "day"')
    index = attributes.integer(doc='The position in the round-robin list for non-daily stats')
    time = attributes.timestamp(doc='When this bucket was last updated')
    attributes.compoundIndex(interval, type, index)


class StatSampler(item.Item):
    """
    Obsolete.  Only present for schema compatibility.  Do not use.
    """
    service = attributes.reference()

    def run(self):
        """
        Obsolete.  Only present to prevent errors in existing systems.  Do not
        use.
        """



class StatsService(item.Item, service.Service):
    """
    Obsolete.  Only present for schema compatibility.  Do not use.
    """
    installedOn = attributes.reference()
    parent = attributes.inmemory()
    running = attributes.inmemory()
    name = attributes.inmemory()
    statoscope = attributes.inmemory()
    queryStatoscope = attributes.inmemory()
    statTypes = attributes.inmemory()
    currentMinuteBucket = attributes.integer(default=0)
    currentQuarterHourBucket = attributes.integer(default=0)
    observers = attributes.inmemory()
    loginInterfaces = attributes.inmemory()
    userStats = attributes.inmemory()

    powerupInterfaces = (service.IService,)



class RemoteStatsObserver(item.Item):
    """
    Obsolete.  Only present for schema compatibility.  Do not use.
    """

    hostname = attributes.bytes(doc="A host to send stat updates to")
    port = attributes.integer(doc="The port to send stat updates to")
    protocol = attributes.inmemory(doc="The juice protocol instance to send stat updates over")



def upgradeStatBucket1to2(bucket):
    bucket.deleteFromStore()
upgrade.registerUpgrader(upgradeStatBucket1to2, 'xmantissa_stats_statbucket', 1, 2)
