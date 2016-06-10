import unittest
import etcd

from nuage.nuage_gluon_shim import compute_network_addr, compute_netmask, get_vpn_info

class MyTestCase(unittest.TestCase):
    def test_compute_network_addr(self):
        ip_addr = '10.10.20.30'
        expected_net_addr = '10.10.16.0'
        net_addr = compute_network_addr("10.10.20.30", 20)
        self.assertEqual(expected_net_addr, net_addr)

    def test_compute_netmask(self):
        prefix = 16
        expected_netmask = '255.255.0.0'
        netmask = compute_netmask(prefix)
        self.assertEqual(expected_netmask, netmask)

    def test_get_vpn_info(self):
        client = etcd.Client()
        uuid = '4d3b364c-f871-407a-8426-0eaed602862f'
        vpn_info = get_vpn_info(client, uuid)
        print vpn_info


if __name__ == '__main__':
    unittest.main()