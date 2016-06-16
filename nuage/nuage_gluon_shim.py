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
import os
import json
import argparse
import time
import string

import logging

from Queue import Queue
from threading import Thread

from nuage.vm_split_activation import NUSplitActivation

vsd_api_url = 'https://127.0.0.1:8443'
etcd_default_port = 2379

client = None
prev_mod_index = 0
vm_status = {}

valid_host_ids = ('cbserver5', 'node-23.opnfvericsson.ca')

proton_etcd_dir = '/net-l3vpn/proton'


def notify_proton_vif(proton, uuid, vif_type):
    path = proton + '/controller/host/' + uuid
    data = {"status": vif_type}
    client.write(path, json.dumps(data))


def notify_proton_status(proton, uuid, status):
    path = proton + '/controller/port/' + uuid
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

    ret = '.'.join(str(e) for e in mask)
    print('Calculated mask = %s' % ret)
    return  ret


def bind_vm(data, vpn_info):

    subnet_name =  'Subnet' + str(time.clock())
    subnet_name = string.replace(subnet_name, '.', '-')

    prefix = data.get('subnet_prefix', '32')
    print('prefix = %s' % prefix)

    config = {
        'api_url': vsd_api_url,
        'domain_name': vpn_info['name'],
        'enterprise': 'csp',
        'enterprise_name': 'Gluon',
        'netmask': compute_netmask(prefix),
        'network_address': compute_network_addr(data.get('ipaddress', ''), prefix),
        'password': 'csproot',
        'route_distinguisher': vpn_info["route_distinguisher"],
        'route_target': vpn_info["route_target"],
        'subnet_name': subnet_name,
        'username': 'csproot',
        'vm_ip': data.get('ipaddress', ''),
        'vm_mac': data.get('mac_address', ''),
        'vm_name': data.get('device_id', ''),  ## uuid of the VM
        'vm_uuid': data.get('device_id',''),
        'vport_name': data.get('id', ''),
        'zone_name': 'Zone0',
        'tunnel_type': 'GRE',
        'domain_template_name': 'GluonDomainTemplate'
    }

    sa = NUSplitActivation(config)
    return sa.activate()


def unbind_vm(data, vpn_info):

    config = {
        'api_url': vsd_api_url,
        'domain_name': vpn_info['name'],
        'enterprise': 'csp',
        'enterprise_name': 'Gluon',
        'username': 'csproot',
        'password': 'csproot',
        'vm_uuid': data.get('device_id', ''),
        'vport_name': data.get('id', '')
    }

    sa = NUSplitActivation(config)
    return sa.deactivate()


def get_vpn_info(client, uuid):
    vpn_info = {}

    try:
        vpn_port = json.loads(client.get(proton_etcd_dir + '/VPNPort/' + uuid).value)

        if not vpn_port:
            logging.error("vpn port is empty for uuid %s" % uuid)
            return False

        else:
            vpn_instance = json.loads(client.get(proton_etcd_dir + '/VpnInstance/' + vpn_port['vpn_instance']).value)

            if vpn_instance:
                vpn_info['route_distinguisher'] = vpn_instance['route_distinguishers']
                vpn_info['name'] = vpn_instance['vpn_instance_name']

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


def process_base_port_model(message, uuid, proton_name):
    global client
    global vm_status
    global valid_host_ids

    action = message.action

    if action == 'set' or action == 'update':
        message_value = json.loads(message.value)

        if message_value['host_id'] is None or message_value['host_id'] == '':
            logging.info("host id is empty")

            if vm_status.get(uuid, '') == 'up':
                logging.info("Port is bound,  need to unbind: TODO")

                if not hasattr(message, '_prev_node'):
                    logging.info("_prev_node is not available")
                    return
                vpn_info = get_vpn_info(client, uuid)
                unbind_vm(json.loads(message._prev_node.value), vpn_info)
                del vm_status[uuid]
                return

        if not message_value['host_id'] in valid_host_ids:
            logging.info("host id %s is not recognized", message_value['host_id'])
            return

        if uuid in vm_status and vm_status[uuid] == 'pending':
            return

        notify_proton_status(proton_name, uuid, 'pending')

        vm_status[uuid] = 'pending'

        vpn_info = get_vpn_info(client, uuid)

        if bind_vm(json.loads(message.value), vpn_info):
            notify_proton_status(proton_name, uuid, 'up')
            vm_status[uuid] = 'up'
            return

        else:
            logging.error("failed activating vm")
            return

        # check if need this
        if uuid in vm_status and vm_status[uuid] == 'unbound':
            notify_proton_status(proton_name, uuid, 'pending')
            pass

    elif action == 'delete':
        if (vm_status[uuid] == 'up'):
            vpn_info = get_vpn_info(client, uuid)
            unbind_vm(json.loads(message.value), vpn_info)
            return

    else:
        logging.error('unknown action %s' % action)


def process_queue(messages_queue):
    logging.info("processing queue")

    while True:
        item = messages_queue.get()
        process_message(item)
        messages_queue.task_done()


def process_message(message):

    logging.info("msg =  %s" % message)
    #logging.info("msg.key =  %s" % message.key)
    #logging.info("msg.value =  %s" % message.value)
    #logging.info("msg.action =  %s" % message.action)

    path = message.key.split('/')

    if len(path) < 5:
        logging.error("unknown message %s, ignoring" % message)
        return

    proton_name = path[1]
    table = path[3]
    uuid = path[4]

    if table == 'ProtonBasePort':
        process_base_port_model(message, uuid, proton_name)

    else:
        logging.error('unrecognized table %s' % table)
        return


def getargs():
    parser = argparse.ArgumentParser(description='Start Shim Layer')

    parser.add_argument('-d', '--debug', required=False, help='Enable debug output', dest='debug',
                        action='store_true')
    parser.add_argument('-H', '--host-name', required=False, help='etcd hostname or ip, default to localhost',
                        dest='etcd_host', type=str)
    parser.add_argument('-p', '--port', required=False, help='etcd port number, default to 2379', dest='etcd_port',
                        type=str)
    parser.add_argument('-v', '--vsd-ip', required=False, help='Nuage vsd ip address, default to 127.0.0.1', dest='vsd_ip',
                        type=str)

    args = parser.parse_args()
    return args


def main():
    global client, vsd_api_url
    logging.basicConfig(level=logging.DEBUG)
    logging.info('Starting server in PID %s' % os.getpid())

    args = getargs()

    if args.etcd_host:
        etcd_host = args.etcd_host

    else:
        etcd_host = 'localhost'

    if args.etcd_host:
        etcd_port = int(args.etcd_port)

    else:
        etcd_port = etcd_default_port

    if args.vsd_ip:
        vsd_api_url = 'https://' + args.vsd_ip + ':8443'

    messages_queue = Queue()
    initialize_worker_thread(messages_queue)
    client = etcd.Client(host=etcd_host, port=etcd_port)

    wait_index = 0

    while True:

        try:
            logging.info("watching %s" % proton_etcd_dir)

            if wait_index:
                message = client.read(proton_etcd_dir, recursive=True, wait=True, waitIndex=wait_index)

            else:
                message = client.read(proton_etcd_dir, recursive=True, wait=True)

            messages_queue.put(message)

            if (message.modifiedIndex - wait_index) > 1000:
                wait_index = 0

            else:
                wait_index = message.modifiedIndex + 1

        except etcd.EtcdWatchTimedOut:
            logging.info("timeout")
            pass

        except etcd.EtcdException:
            logging.error("cannot connect to etcd, make sure that etcd is running")
            exit(1)

        except KeyboardInterrupt:
            logging.info("exiting on interrupt")
            exit(1)

        except:
            pass

if __name__ == '__main__':
    main()
