#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# export.py - Exports enumerated data for reachable nodes into a JSON file.
#
# Copyright (c) 2013 Addy Yeow Chin Heng <ayeowch@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Exports enumerated data for reachable nodes into a JSON file.
"""

import json
import logging
import os
import redis
import sys
import time

# Global instance of Redis connection
REDIS_CONN = redis.StrictRedis()


def get_row(node):
    """
    Returns enumerated row data from Redis for the specified node.
    """
    # address, port, version, user_agent, timestamp
    node = eval(node)
    address = node[0]
    port = node[1]

    start_height = REDIS_CONN.get('start_height:{}-{}'.format(address, port))
    start_height = (int(start_height),)

    hostname = REDIS_CONN.hget('resolve:{}'.format(address), 'hostname')
    hostname = (hostname,)

    geoip = REDIS_CONN.hget('resolve:{}'.format(address), 'geoip')
    if geoip is None:
        # city, country, latitude, longitude, timezone, asn, org
        geoip = (None, None, None, None, None, None, None)
    else:
        geoip = eval(geoip)

    return node + start_height + hostname + geoip


def export_nodes(nodes, timestamp):
    """
    Merges enumerated data for the specified nodes and exports them into
    timestamp-prefixed JSON file.
    """
    rows = []
    start = time.time()
    for node in nodes:
        row = get_row(node)
        rows.append(row)
    end = time.time()
    elapsed = end - start
    logging.info("Elapsed: {}".format(elapsed))

    export_dir = "data/export"
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)

    dump = os.path.join(export_dir, "{}.json".format(timestamp))
    open(dump, 'w').write(json.dumps(rows, encoding="latin-1"))
    logging.info("Wrote {}".format(dump))


def main():
    logfile = os.path.basename(__file__).replace(".py", ".log")
    loglevel = logging.INFO
    logformat = ("%(asctime)s,%(msecs)05.1f %(levelname)s (%(funcName)s) "
                 "%(message)s")
    logging.basicConfig(level=loglevel,
                        format=logformat,
                        filename=logfile,
                        filemode='w')
    print("Writing output to {}, press CTRL+C to terminate..".format(logfile))

    pubsub = REDIS_CONN.pubsub()
    pubsub.subscribe('resolve')
    for msg in pubsub.listen():
        # 'resolve' message is published by resolve.py after resolving hostname
        # and GeoIP data for all reachable nodes.
        if msg['channel'] == 'resolve' and msg['type'] == 'message':
            timestamp = int(msg['data'])  # From ping.py's 'snapshot' message
            logging.info("Timestamp: {}".format(timestamp))
            nodes = REDIS_CONN.smembers('opendata')
            logging.info("Nodes: {}".format(len(nodes)))
            export_nodes(nodes, timestamp)

    return 0


if __name__ == '__main__':
    sys.exit(main())