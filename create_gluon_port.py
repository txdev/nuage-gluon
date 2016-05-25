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
Contains a class and main function for creating Gluon ports.

--- Author ---
Kamal Hussain <kamal.hussain@nokia.com>

--- Version history ---
2016-06-23 - 0.1

--- Usage ---
modify the config dictionary in the code.
run 'python create-gluon-port.py

"""

import sys
import argparse
import ConfigParser

from vspk import v3_2 as vsdk
from vspk.utils import set_log_level
import logging
from bambou.exceptions import BambouHTTPError


class GluonPort:
    """ Represents Gluon port. """

    config = {}

    def __init__(self, config):
        self.config = config
        self.session = vsdk.NUVSDSession(username=self.config.username, password=self.config.password,
                                         enterprise=self.config.enterprise, api_url=self.config.api_url)

        logging.info("starting session username: %s, password: %s, enterprise: %s, api_url: %s" % (
            config.username, config.password, config.enterprise, config.api_url))
        self.session.start()

    def createPort(self):
        """Create Gluon port.
        """

        # get enterprise
        self.session.user.enterprises.fetch()
        enterprise = next((enterprise for enterprise in self.session.user.enterprises if
                           enterprise.name == self.config.enterprise_name), None)

        if enterprise is None:
            logging.critical("Enterprise %s not found, exiting" % enterprise)
            return False

        # get domains
        enterprise.domains.fetch()

        domain = next((domain for domain in enterprise.domains if domain.name == self.config.domain_name), None)

        if domain is None:
            logging.info("Domain %s not found, creating domain" % self.config.domain_name)

            domain = vsdk.NUDomain(name=self.config.domain_name, template_id=self.domain_template_id)
            enterprise.create_child(domain)

        # get zone
        domain.zones.fetch()

        zone = next((zone for zone in domain.zones if zone.name == self.config.zone_name), None)

        if zone is None:
            logging.info("Zone %s not found, creating zone" % self.config.zone_name)

            zone = vsdk.NUZone(name=self.config.zone_name)
            domain.create_child(zone)

        # get subnet
        zone.subnets.fetch()
        subnet = next((subnet for subnet in zone.subnets if subnet.name == self.config.subnet_name), None)

        if subnet is None:
            logging.info("Subnet %s not found, creating subnet" % self.config.subnet_name)

            subnet = vsdk.NUSubnet(name=self.config.subnet_name, address=self.config.network_address,
                                   netmask=self.config.netmask)
            zone.create_child(subnet)

        # get vport
        subnet.vports.fetch()
        vport = next((vport for vport in subnet.vports if vport.name == self.config.vport_name), None)

        if vport is None:
            # create vport
            logging.info("Vport %s is not found, creating Vport" % self.config.vport_name)

            vport = vsdk.NUVPort(name=self.config.vport_name, address_spoofing='INHERITED', type='VM',
                                 description='Automatically created, do not edit.')
            subnet.create_child(vport)

        # get vm
        vm = self.session.user.fetcher_for_rest_name('vm').get('name=="%s"' % self.config.vm_name)

        if not vm:
            logging.info("Vport %s is not found, creating Vport" % self.config.vport_name)

            vm = vsdk.NUVM(name=self.config.vm_name, uuid=self.config.vm_uuid, interfaces=[{
                'name': self.config.vm_name,
                'VPortID': vport.id,
                'MAC': self.config.vm_mac,
                'IPAddress': self.config.vm_ip
            }])

            self.session.user.create_child(vm)

        return True


def getargs():
    parser = argparse.ArgumentParser(description='Create Gluon ports.')
    parser.add_argument('-d', '--debug', required=False, help='Enable debug output', dest='debug',
                        action='store_true')
    parser.add_argument('-c', '--config-file', required=False, help='configuration file',
                        dest='config_file', type=str)
    args = parser.parse_args()
    return args


def parse_config_file(config_file):
    """ read configuration file """
    parser = ConfigParser.ConfigParser()

    parser.read(config_file)

    config = {}

    for section in parser.sections():
        for name, value in parser.items(section):
            config[name] = value
            print '  %s = %r' % (name, value)

    return config


def main():
    """ main program to test the GluonPort.
    """
    args = getargs()

    if args.config_file:
        config_file = args.logfile
        config = parse_config_file(config_file)

    else:
        config = {
            'username': '',
            'password': '',
            'enterprise': '',
            'api_url': '',
            'enterprise_name': '',
            'domain_name': '',
            'domain_rt': '',
            'domain_rd': '',
            'zone_name': '',
            'subnet_name': '',
            'vport_name': '',
            'vm_name': '',
            'vm_ip': '',
            'vm_uuid': ''
        }

    set_log_level(logging.ERROR)

    gp = GluonPort(config)

    if gp.createPort():
        logging.info('Port successfully created')

    else:
        logging.info("Port creation failed")


if __name__ == "__main__":
    main()
