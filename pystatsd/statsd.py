# statsd.py

# Steve Ivy <steveivy@gmail.com>
# http://monkinetic.com

import logging
import socket
import random
import time


# Sends statistics to the stats daemon over UDP
class Client(object):

    def __init__(self, host='localhost', port=8125, prefix=None):
        """
        Create a new Statsd client.
        * host: the host where statsd is listening, defaults to localhost
        * port: the port where statsd is listening, defaults to 8125

        >>> from pystatsd import statsd
        >>> stats_client = statsd.Statsd(host, port)
        """
        self.host = host
        self.port = int(port)
        self.prefix = prefix
        self.log = logging.getLogger("pystatsd.client")
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def timing_since(self, stat, start, sample_rate=1):
        """
        Log timing information as the number of microseconds since the provided time float
        >>> start = time.time()
        >>> # do stuff
        >>> statsd_client.timing_since('some.time', start)
        """
        self.timing(stat, int((time.time() - start) * 1000000), sample_rate)

    def timing(self, stat, time, sample_rate=1):
        """
        Log timing information for a single stat
        >>> statsd_client.timing('some.time',500)
        """
        stats = {stat: "%f|ms" % time}
        self.send(stats, sample_rate)

    def increment(self, stats, sample_rate=1):
        """
        Increments one or more stats counters
        >>> statsd_client.increment('some.int')
        >>> statsd_client.increment('some.int',0.5)
        """
        self.update_stats(stats, 1, sample_rate=sample_rate)

    def decrement(self, stats, sample_rate=1):
        """
        Decrements one or more stats counters
        >>> statsd_client.decrement('some.int')
        """
        self.update_stats(stats, -1, sample_rate=sample_rate)

    def update_stats(self, stats, delta, sample_rate=1):
        """
        Updates one or more stats counters by arbitrary amounts
        >>> statsd_client.update_stats('some.int',10)
        """
        if not isinstance(stats, list):
            stats = [stats]

        data = dict((stat, "%s|c" % delta) for stat in stats)
        self.send(data, sample_rate)

    def absolute_counter(self, stats, value):
        """
        Updates one or more absolute counter to a set value

        (the difference from previous value is stored in graphite)
        >>> statsd_client.absolute_counter('some.counter',1000)
        """
        if not isinstance(stats, list):
            stats = [stats]

        data = dict((stat, "%s|abs" % value) for stat in stats)
        self.send(data, sample_rate=1)

    def gauge(self, stats, value, hold=False):
        """
        Updates one or more gauge to a set value, stored directly
        in graphite

        If hold==True, don't expire the value when there are no updates
        (for infrequently updated values)
        >>> statsd_client.gauge('gauge',1000)
        """
        if not isinstance(stats, list):
            stats = [stats]

        if hold:
            tag = 'gh'
        else:
            tag = 'g'

        data = dict((stat, "%s|%s" % (value, tag)) for stat in stats)
        self.send(data, sample_rate=1)

    def cancel_stat(self, stats):
        """
        Don't publish a stat any more if no new values come
        (otherwise we get a stream of zeros)
        >>> statsd_client.cancel_stat('some.counter')
        """
        if not isinstance(stats, list):
            stats = [stats]

        data = dict((stat, "0|dc") for stat in stats)
        self.send(data, sample_rate=1)

    def send(self, data, sample_rate=1):
        """
        Squirt the metrics over UDP
        """
        addr = (self.host, self.port)

        if self.prefix:
            data = dict((".".join((self.prefix, stat)), value) for stat, value in data.iteritems())

        if sample_rate < 1:
            if random.random() > sample_rate:
                return
            sampled_data = dict((stat, "%s|@%s" % (value, sample_rate)) for stat, value in data.iteritems())
        else:
            sampled_data = data

        try:
            [self.udp_sock.sendto("%s:%s" % (stat, value), addr) for stat, value in sampled_data.iteritems()]
        except:
            self.log.exception("unexpected error")
