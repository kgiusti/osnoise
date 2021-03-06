#!/usr/bin/env python

# Copyright 2016 Orange
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from osnoise.common import logger as logging
import threading
import time

LOG = logging.getLogger(__name__)


def do_thread(function):
    def wrapper(*args, **kwargs):
        t = threading.Thread(target=function, args=args, kwargs=kwargs)
        # Not daemonizing the thread makes publication slow. When try to
        # publish too many messages, the rate will decrease eventually..
        # JFP when a daemon, it will end the threads at the end of program exec, so make normal threads
        t.daemon = False
        t.start()
    return wrapper

class Publisher(object):
    """The publisher class"""

    def __init__(self, pub_id=None, duration=None, publish_rate=None,
                 connection=None, channel=None, exchange=None,
                 routing_key=None, body=None, properties=None):
        # init stop event
        self._run_event = threading.Event()
        self._run_event.set()

        # init publisher args
        self.pub_id             = pub_id
        self.duration           = duration
        self.publish_rate       = publish_rate
        self.connection         = connection
        self.channel            = channel
        self.exchange_name      = exchange
        self.routing_key        = routing_key
        self.message_payload    = body
        self.message_properties = properties

        # init clock thread interval
        self.interval = 0

    @do_thread
    def _update_interval(self, current_time):
        while self._run_event.is_set():
            #time.sleep(1)
            if current_time - self.interval >= 1000:
                # add new one second interval
                self.interval += 1000

    def _delay_publish(self, message_count, interval):
        elapsed_time = int(round(time.time() * 1000)) - interval
        pause_time = message_count * 1000 / self.publish_rate - \
                     elapsed_time if self.publish_rate != 0 else 0

        if pause_time > 0:
            try:
                time.sleep(pause_time/1000)
            except Exception:
                LOG.error('Caught exception when trying to sleep..')

    @do_thread
    def do_publish(self):
        LOG.info('Start publishing..')
        start_time = current_time = interval = int(round(time.time() * 1000))
        self.interval = interval
        message_count = 0

        try:
            while (self._run_event.is_set() and
                       (self.duration == 0 or current_time < start_time +
                               self.duration*1000)):
                #keep up with the publish rate
                #JFP
		#self._delay_publish(message_count=message_count,
                                    #interval=interval)
                #publish a message
                self.channel.basic_publish(exchange=self.exchange_name,
                                           routing_key=self.routing_key,
                                           body=self.message_payload,
                                           properties=self.message_properties
                                           )
                message_count += 1
                current_time = int(round(time.time() * 1000))
                LOG.debug('[message %s] Published to: %s' %(message_count,
                                                            self.exchange_name))
            LOG.info('Total messages %s' %(message_count-1))
            self._do_stop()
        except IOError as ex:
            LOG.error('I/O error({0}): {1}'.format(ex.errno, ex.strerror))
            self._do_stop()
        finally:
            LOG.info('Stop publishing..')
            self._do_stop()

    def _do_stop(self):
        self._run_event.clear()
        # JFP not closing
        #self._close_connection()


    def _close_connection(self):
        if not self.channel.is_closed:
            # JFP don't close channel
            LOG.debug('NOT Closing channel..')
            #self.channel.close(reply_code=200, reply_text='Normal shutdown')
        else:
            LOG.debug('Channel is already closed..')
        if not self.connection.is_closed:
            # JFP don't close connection
            LOG.debug('NOT Closing connection..')
            #self.connection.close(reply_code=200, reply_text='Normal shutdown')
        else:
            LOG.debug('Connection is already closed..')
