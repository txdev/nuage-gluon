import unittest

from nuage.nuage_gluon_shim import compute_network_addr

class MyTestCase(unittest.TestCase):
    def test_something(self):
        ip_addr = '10.10.20.30'
        expected_net_addr = '10.10.16.0'
        net_addr = compute_network_addr("10.10.20.30", 20)
        self.assertEqual(expected_net_addr, net_addr)


if __name__ == '__main__':
    unittest.main()
