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
Gluon shim layer for handling etcd messages
"""

import etcd
import json
import logging

from Queue import Queue
from threading import Thread

from nuage.vm_split_activation import NUSplitActivation

client = None
prev_mod_index = 0
vm_status = {}
proton_etcd_dir = '/net-l3vpn/proton'

logger = logging.getLogger(__name__)

def notify_proton_vif(proton, uuid, vif_type):
    path = proton + '/controller/port/' + uuid
    data = {"status": vif_type}
    client.write(path, json.dumps(data))


def notify_proton_status(proton, uuid, status):
    path = proton + '/controller/host/' + uuid
    data = {"status": status}
    client.write(path, json.dumps(data))


def initialize_worker_thread(messages_queue):
    worker = Thread(target=process_queue, args=(messages_queue,))
    worker.setDaemon(True)
    worker.start()

    return worker


def compute_network_addr(ip, prefix):
    """
    return network address
    """

    addr = ip.split('.')
    prefix = int(prefix)

    mask = [0, 0, 0, 0]
    for i in range(prefix):
        mask[i / 8] += (1 << (7 - i % 8))

    net = []
    for i in range(4):
        net.append(int(addr[i]) & mask[i])

    return '.'.join(str(e) for e in net)


def compute_netmask(prefix):
    """
    return netmask
    :param prefix:
    :return:
    """
    prefix = int(prefix)

    mask = [0, 0, 0, 0]
    for i in range(prefix):
        mask[i / 8] += (1 << (7 - i % 8))

    return '.'.join(str(e) for e in mask)


def activate_vm(data, vpn_info):

    config = {
        'api_url': 'https://10.2.0.30:8443',
        'domain_name': 'GluonDomain',
        'enterprise': 'csp',
        'enterprise_name': 'GluonEnt',
        'netmask': compute_netmask(data.prefix),
        'network_address': compute_network_addr(data.ipaddress, data.prefix),
        'password': '',
        'route_distinguisher': vpn_info.route_distinguisher,
        'route_target': vpn_info.route_target,
        'subnet_name': 'Gluon_Subnet',
        'username': 'csproot',
        'vm_ip': data['ipaddress'],
        'vm_mac': data['mac_address'],
        'vm_name': data['vm_id'],  ## uuid of the VM
        'vm_uuid': data['vm_id'],
        'vport_name': 'vport1',
        'zone_name': 'GluonZone',
    }

    sa = NUSplitActivation(config)
    return sa.activate()


def get_vpn_info(client, uuid):
    vpn_info = {}

    try:
        vpn_port = json.loads(client.get(proton_etcd_dir + '/VPNPort/' + uuid).value)
        print vpn_port["vpn_instance"]

        if not vpn_port:
            logging.error("vpn port is empty for uuid %s" % uuid)
            return False

        else:
            vpn_instance = json.loads(client.get(proton_etcd_dir + '/VpnInstance/' + vpn_port['vpn_instance']).value)

            if vpn_instance:
                vpn_info['route_distinguisher'] = vpn_instance['route_distinguishers']

                vpn_afconfig = json.loads(client.get(proton_etcd_dir + '/VpnAfConfig/' + vpn_instance['ipv4_family']).value)

                if vpn_afconfig:
                    vpn_info['route_target'] = vpn_afconfig['vrf_rt_value']

                else:
                    logging.error("vpnafconfig is empty for uuid %s" % uuid)

            else:
                logging.error("vpn instance is empty for %s" % vpn_port['vpn_instance'])
                return False

    except etcd.EtcdKeyNotFound:
        return False

    return vpn_info


def process_port_model(message, uuid, proton_name):
    global client
    global vm_status
    action = message.action

    if action == 'set':
        pass

    elif action == 'update':
        if uuid in vm_status and vm_status[uuid] == 'pending':
            return

        notify_proton_status(proton_name, uuid, 'pending')

        vm_status[uuid] = 'pending'

        vpn_info = get_vpn_info(uuid)

        if activate_vm(json.loads(message.value), vpn_info):
            notify_proton_status(proton_name, uuid, 'up')
            vm_status[uuid] = 'up'
            return

        else:
            logger.error("failed activating vm")
            return

        if uuid in vm_status and vm_status[uuid] == 'unbound':
            notify_proton_status(proton_name, uuid, 'pending')
            pass

    elif action == 'delete':
        pass

    else:
        logger.error('unknown action %s' % action)


def process_queue(messages_queue):
    logger.info("processing queue")

    while True:
        item = messages_queue.get()
        process_message(item)
        messages_queue.task_done()


def process_message(message):

    path = message.key.split('/')

    if len(path) < 5:
        logger.error("unknown message %s, ignoring" % message)
        return

    proton_name = path[1]
    table = path[2]
    uuid = path[3]

    if table == 'ProtonBasePort':
        process_port_model(message, uuid, proton_name)

    else:
        logger.error('unrecognized table %s' % table)
        return


def main():
    global client
    messages_queue = Queue()
    initialize_worker_thread(messages_queue)
    client = etcd.Client()

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    logger.addHandler(ch)

    wait_index = 0

    while True:

        try:
            logger.info("watching %s" % proton_etcd_dir)

            if wait_index:
                message = client.read(proton_etcd_dir, recursive=True, wait=True, waitIndex=wait_index)

            else:
                message = client.read(proton_etcd_dir, recursive=True, wait=True)

            messages_queue.put(message.value)

            if (message.modifiedIndex - wait_index) > 1000:
                wait_index = 0

            else:
                wait_index = message.modifiedIndex + 1

        except etcd.EtcdException:
            logger.error("cannot connect to etcd, make sure that etcd is running")
            exit(1)

        except KeyboardInterrupt:
            logger.info("exiting on interrupt")
            exit(1)

        except:
            pass

if __name__ == '__main__':
    main()