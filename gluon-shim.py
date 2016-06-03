# -*- coding: utf-8 -*-
# Copyright (c) 2016, Nokia
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the names of its contributors
#       may be used to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
Skeleton code for Gluon Shim layer
"""

import etcd
import logging
import json

from Queue import Queue
from threading import Thread

from nuage.vm_split_activation import NUSplitActivation

client = None
prev_mod_index = 0
vm_status = {}
proton_etcd_dir = '/net-l3vpn/proton'


def notify_proton_vif(proton, uuid, vif_type):
    path = proton + '/controller/port/' + uuid
    data = {"status": vif_type}
    client.write(path, json.dumps(data))


def notify_proton_status(proton, uuid, status):
    path = proton + '/controller/host/' + uuid
    data = {"status": status}
    client.write(path, json.dumps(data))


def initialize_worker_thread(messages_queue):
    worker = Thread(target=read_message_queue, args=(messages_queue,))
    worker.setDaemon(True)
    worker.start()

    return worker


def process_port_model(message, uuid, proton_name):
    """
    populate this function
    """
    global vm_status
    action = message.action

    if action == 'set':
        pass

    elif action == 'update':
        if uuid in vm_status and vm_status[uuid] == 'pending':
            return

        value = json.loads(message.value)
        notify_proton_status(proton_name, uuid, 'pending')

        vm_status[uuid] = 'pending'

        if uuid in vm_status and vm_status[uuid] == 'unbound':
            notify_proton_status(proton_name, uuid, 'pending')
            pass

        value = json.loads(message.value)

    elif action == 'delete':
        pass

    else:
        logging.error('unknown action %s' % action)


def read_message_queue(messages_queue):
    logging.info("processing message queue")

    while True:
        item = messages_queue.get()
        logging.info("message retrieved from queue")
        process_message(item)
        messages_queue.task_done()


def process_message(message):

    global prev_mod_index, vm_status
    path = message.key.split('/')

    if len(path) < 5:
        logging.error("unknown message %s, ignoring" % message)
        return

    proton_name = path[1]
    table = path[2]
    uuid = path[3]

    if table == 'ProtonBasePort':
        process_port_model(message, uuid, proton_name)

    else:
        logging.error('unrecognized table %s' % table)
        return


def main():
    global client
    client = etcd.Client()
    messages_queue = Queue()
    initialize_worker_thread(messages_queue)

    wait_index = 0

    while True:

        try:
            if wait_index:
                message = client.read(proton_etcd_dir, recursive=True, wait=True, waitIndex=wait_index)

            else:
                message = client.read(proton_etcd_dir, recursive=True, wait=True)

            messages_queue.put(message)

        except KeyboardInterrupt:
            logging.info("exiting on interrupt")
            exit(1)

        except:
            pass

        if (message.modifiedIndex - wait_index) > 1000:
            wait_index = 0

        else:
            wait_index = message.modifiedIndex + 1

if __name__ == '__main__':
    main()