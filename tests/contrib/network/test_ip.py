import subprocess
import unittest

import mock
import netifaces

import charmhelpers.contrib.network.ip as net_ip
from mock import patch
import nose.tools

DUMMY_ADDRESSES = {
    'lo': {
        17: [{'peer': '00:00:00:00:00:00',
              'addr': '00:00:00:00:00:00'}],
        2: [{'peer': '127.0.0.1', 'netmask':
             '255.0.0.0', 'addr': '127.0.0.1'}],
        10: [{'netmask': 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff',
              'addr': '::1'}]
    },
    'eth0': {
        2: [{'addr': '192.168.1.55',
             'broadcast': '192.168.1.255',
             'netmask': '255.255.255.0'}],
        10: [{'addr': '2a01:348:2f4:0:685e:5748:ae62:209f',
              'netmask': 'ffff:ffff:ffff:ffff::'},
             {'addr': 'fe80::3e97:eff:fe8b:1cf7%eth0',
              'netmask': 'ffff:ffff:ffff:ffff::'}],
        17: [{'addr': '3c:97:0e:8b:1c:f7',
              'broadcast': 'ff:ff:ff:ff:ff:ff'}]
    },
    'eth0:1': {
        2: [{'addr': '192.168.1.56',
             'broadcast': '192.168.1.255',
             'netmask': '255.255.255.0'}],
    },
    'eth1': {
        2: [{'addr': '10.5.0.1',
             'broadcast': '10.5.255.255',
             'netmask': '255.255.0.0'}],
        10: [{'addr': 'fe80::3e97:eff:fe8b:1cf7%eth1',
              'netmask': 'ffff:ffff:ffff:ffff::'}],
        17: [{'addr': '3c:97:0e:8b:1c:f7',
              'broadcast': 'ff:ff:ff:ff:ff:ff'}]
    },
    'eth2': {
        10: [{'addr': '3a01:348:2f4:0:685e:5748:ae62:209f',
              'netmask': 'ffff:ffff:ffff:ffff::'},
             {'addr': 'fe80::3e97:edd:fe8b:1cf7%eth0',
              'netmask': 'ffff:ffff:ffff:ffff::'}],
        17: [{'addr': '3c:97:0e:8b:1c:f7',
              'broadcast': 'ff:ff:ff:ff:ff:ff'}]
    },
    'eth2:1': {
        2: [{'addr': '192.168.10.58',
             'broadcast': '192.168.1.255',
             'netmask': '255.255.255.0'}],
    },
}


class IPTest(unittest.TestCase):

    def mock_ifaddresses(self, iface):
        return DUMMY_ADDRESSES[iface]

    def test_get_address_in_network_with_invalid_net(self):
        for net in ['192.168.300/22', '192.168.1.0/2a', '2.a']:
            self.assertRaises(ValueError,
                              net_ip.get_address_in_network,
                              net)

    def _test_get_address_in_network(self, expect_ip_addr,
                                     network, fallback=None, fatal=False):

        def side_effect(iface):
            return DUMMY_ADDRESSES[iface]

        with mock.patch.object(netifaces, 'interfaces') as interfaces:
            interfaces.return_value = DUMMY_ADDRESSES.keys()
            with mock.patch.object(netifaces, 'ifaddresses') as ifaddresses:
                ifaddresses.side_effect = side_effect
                if not fatal:
                    self.assertEqual(expect_ip_addr,
                                     net_ip.get_address_in_network(
                                         network, fallback, fatal))
                else:
                    net_ip.get_address_in_network(network, fallback, fatal)

    @mock.patch.object(subprocess, 'call')
    def test_get_address_in_network_with_none(self, popen):
        fallback = '10.10.10.10'
        self.assertEqual(fallback,
                         net_ip.get_address_in_network(None, fallback))

        self.assertRaises(SystemExit, self._test_get_address_in_network,
                          None, None, fatal=True)

    def test_get_address_in_network_ipv4(self):
        self._test_get_address_in_network('192.168.1.56', '192.168.1.0/24')

    def test_get_address_in_network_ipv6(self):
        self._test_get_address_in_network('2a01:348:2f4:0:685e:5748:ae62:209f',
                                          '2a01:348:2f4::/64')

    def test_get_address_in_network_with_non_existent_net(self):
        self._test_get_address_in_network(None, '172.16.0.0/16')

    def test_get_address_in_network_fallback_works(self):
        fallback = '10.10.0.0'
        self._test_get_address_in_network(fallback, '172.16.0.0/16', fallback)

    @mock.patch.object(subprocess, 'call')
    def test_get_address_in_network_not_found_fatal(self, popen):
        self.assertRaises(SystemExit, self._test_get_address_in_network,
                          None, '172.16.0.0/16', fatal=True)

    def test_get_address_in_network_not_found_not_fatal(self):
        self._test_get_address_in_network(None, '172.16.0.0/16', fatal=False)

    def test_is_address_in_network(self):
        self.assertTrue(
            net_ip.is_address_in_network(
                '192.168.1.0/24',
                '192.168.1.1'))
        self.assertFalse(
            net_ip.is_address_in_network(
                '192.168.1.0/24',
                '10.5.1.1'))
        self.assertRaises(ValueError, net_ip.is_address_in_network,
                          'broken', '192.168.1.1')
        self.assertRaises(ValueError, net_ip.is_address_in_network,
                          '192.168.1.0/24', 'hostname')
        self.assertTrue(
            net_ip.is_address_in_network(
                '2a01:348:2f4::/64',
                '2a01:348:2f4:0:685e:5748:ae62:209f')
        )
        self.assertFalse(
            net_ip.is_address_in_network(
                '2a01:348:2f4::/64',
                'fdfc:3bd5:210b:cc8d:8c80:9e10:3f07:371')
        )

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_iface_for_address(self, _interfaces, _ifaddresses):
        def mock_ifaddresses(iface):
            return DUMMY_ADDRESSES[iface]
        _interfaces.return_value = ['eth0', 'eth1']
        _ifaddresses.side_effect = mock_ifaddresses
        self.assertEquals(
            net_ip.get_iface_for_address('192.168.1.220'),
            'eth0')
        self.assertEquals(net_ip.get_iface_for_address('10.5.20.4'), 'eth1')
        self.assertEquals(
            net_ip.get_iface_for_address('2a01:348:2f4:0:685e:5748:ae62:210f'),
            'eth0'
        )
        self.assertEquals(net_ip.get_iface_for_address('172.4.5.5'), None)

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_netmask_for_address(self, _interfaces, _ifaddresses):
        def mock_ifaddresses(iface):
            return DUMMY_ADDRESSES[iface]
        _interfaces.return_value = ['eth0', 'eth1']
        _ifaddresses.side_effect = mock_ifaddresses
        self.assertEquals(
            net_ip.get_netmask_for_address('192.168.1.220'),
            '255.255.255.0')
        self.assertEquals(
            net_ip.get_netmask_for_address('10.5.20.4'),
            '255.255.0.0')
        self.assertEquals(net_ip.get_netmask_for_address('172.4.5.5'), None)
        self.assertEquals(
            net_ip.get_netmask_for_address('2a01:348:2f4:0:685e:5748:ae62:210f'),
            'ffff:ffff:ffff:ffff::'
        )

    def test_is_ipv6(self):
        self.assertFalse(net_ip.is_ipv6('myhost'))
        self.assertFalse(net_ip.is_ipv6('172.4.5.5'))
        self.assertTrue(net_ip.is_ipv6('2a01:348:2f4:0:685e:5748:ae62:209f'))

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_ipv6_addr_no_ipv6(self, _interfaces, _ifaddresses):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        _ifaddresses.side_effect = DUMMY_ADDRESSES.__getitem__
        with nose.tools.assert_raises(Exception):
            net_ip.get_ipv6_addr('eth0:1')

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_ipv6_addr_no_global_ipv6(self, _interfaces,
                                          _ifaddresses):
        DUMMY_ADDRESSES = {
            'eth0': {
                10: [{'addr': 'fe80::3e97:eff:fe8b:1cf7%eth0',
                      'netmask': 'ffff:ffff:ffff:ffff::'}],
            }
        }
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        _ifaddresses.side_effect = DUMMY_ADDRESSES.__getitem__
        self.assertRaises(Exception, net_ip.get_ipv6_addr)

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_ipv6_addr_exc_list(self, _interfaces, _ifaddresses):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        _ifaddresses.side_effect = DUMMY_ADDRESSES.__getitem__
        result = net_ip.get_ipv6_addr(
            exc_list='2a01:348:2f4:0:685e:5748:ae62:209f',
            inc_aliases=True,
            fatal=False,
            global_dynamic=False
        )
        self.assertEqual([], result)

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_ipv6_addr(self, _interfaces, _ifaddresses):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        _ifaddresses.side_effect = DUMMY_ADDRESSES.__getitem__
        result = net_ip.get_ipv6_addr(global_dynamic=False)
        self.assertEqual(['2a01:348:2f4:0:685e:5748:ae62:209f'], result)

    @patch.object(net_ip, 'select_ipv6_global_dynamic_address')
    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_ipv6_addr_global_dynamic(self, _interfaces, _ifaddresses,
                                          _select_global_dynamic_addr):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        _ifaddresses.side_effect = DUMMY_ADDRESSES.__getitem__
        FAKE_ADDRESS = '2a01:348:2f4:0:685e:5748:ae62:209f'
        _select_global_dynamic_addr.return_value = FAKE_ADDRESS
        result = net_ip.get_ipv6_addr(global_dynamic=True)
        self.assertEqual(['2a01:348:2f4:0:685e:5748:ae62:209f'], result)

    @patch.object(netifaces, 'interfaces')
    def test_get_ipv6_addr_invalid_nic(self, _interfaces):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        self.assertRaises(Exception, net_ip.get_ipv6_addr, 'eth1')

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_iface_addr(self, _interfaces, _ifaddresses):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        _ifaddresses.side_effect = DUMMY_ADDRESSES.__getitem__
        result = net_ip.get_iface_addr("eth0")
        self.assertEqual(["192.168.1.55"], result)

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_iface_addr_excaliases(self, _interfaces, _ifaddresses):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        _ifaddresses.side_effect = DUMMY_ADDRESSES.__getitem__
        result = net_ip.get_iface_addr("eth0")
        self.assertEqual(['192.168.1.55'], result)

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_iface_addr_incaliases(self, _interfaces, _ifaddresses):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        _ifaddresses.side_effect = DUMMY_ADDRESSES.__getitem__
        result = net_ip.get_iface_addr("eth0", inc_aliases=True)
        self.assertEqual(['192.168.1.55', '192.168.1.56'], result)

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_iface_addr_exclist(self, _interfaces, _ifaddresses):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        _ifaddresses.side_effect = DUMMY_ADDRESSES.__getitem__
        result = net_ip.get_iface_addr("eth0", inc_aliases=True,
                                       exc_list=['192.168.1.55'])
        self.assertEqual(['192.168.1.56'], result)

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_iface_addr_mixedaddr(self, _interfaces, _ifaddresses):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        _ifaddresses.side_effect = DUMMY_ADDRESSES.__getitem__
        result = net_ip.get_iface_addr("eth2", inc_aliases=True)
        self.assertEqual(["192.168.10.58"], result)

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_iface_addr_full_interface_path(self, _interfaces,
                                                _ifaddresses):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        _ifaddresses.side_effect = DUMMY_ADDRESSES.__getitem__
        result = net_ip.get_iface_addr("/dev/eth0")
        self.assertEqual(["192.168.1.55"], result)

    @patch.object(netifaces, 'interfaces')
    def test_get_iface_addr_invalid_type(self, _interfaces):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        with nose.tools.assert_raises(Exception):
            net_ip.get_iface_addr(iface='eth0', inet_type='AF_BOB')

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_iface_addr_invalid_interface(self, _interfaces, _ifaddresses):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        result = net_ip.get_ipv4_addr("eth3", fatal=False)
        self.assertEqual([], result)

    @patch.object(netifaces, 'interfaces')
    def test_get_iface_addr_invalid_interface_fatal(self, _interfaces):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        with nose.tools.assert_raises(Exception):
            net_ip.get_ipv4_addr("eth3", fatal=True)

    @patch.object(netifaces, 'interfaces')
    def test_get_iface_addr_invalid_interface_fatal_incaliases(self,
                                                               _interfaces):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        with nose.tools.assert_raises(Exception):
            net_ip.get_ipv4_addr("eth3", fatal=True, inc_aliases=True)

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_get_iface_addr_interface_has_no_ipv4(self, _interfaces,
                                                      _ifaddresses):

        # This will raise a KeyError since we are looking for "2"
        # (actally, netiface.AF_INET).
        DUMMY_ADDRESSES = {
            'eth0': {
                10: [{'addr': 'fe80::3e97:eff:fe8b:1cf7%eth0',
                      'netmask': 'ffff:ffff:ffff:ffff::'}],
            }
        }

        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        _ifaddresses.side_effect = DUMMY_ADDRESSES.__getitem__

        result = net_ip.get_ipv4_addr("eth0", fatal=False)
        self.assertEqual([], result)

    @patch('glob.glob')
    def test_get_bridges(self, _glob):
        _glob.return_value = ['/sys/devices/virtual/net/br0/bridge']
        self.assertEqual(['br0'], net_ip.get_bridges())

    @patch.object(net_ip, 'get_bridges')
    @patch('glob.glob')
    def test_get_bridge_nics(self, _glob, _get_bridges):
        _glob.return_value = ['/sys/devices/virtual/net/br0/brif/eth4',
                              '/sys/devices/virtual/net/br0/brif/eth5']
        self.assertEqual(['eth4', 'eth5'], net_ip.get_bridge_nics('br0'))

    @patch.object(net_ip, 'get_bridges')
    @patch('glob.glob')
    def test_get_bridge_nics_invalid_br(self, _glob, _get_bridges):
        _glob.return_value = []
        self.assertEqual([], net_ip.get_bridge_nics('br1'))

    @patch.object(net_ip, 'get_bridges')
    @patch.object(net_ip, 'get_bridge_nics')
    def test_is_bridge_member(self, _get_bridge_nics, _get_bridges):
        _get_bridges.return_value = ['br0']
        _get_bridge_nics.return_value = ['eth4', 'eth5']
        self.assertTrue(net_ip.is_bridge_member('eth4'))
        self.assertFalse(net_ip.is_bridge_member('eth6'))

    def test_format_ipv6_addr(self):
        DUMMY_ADDRESS = '2001:db8:1:0:f131:fc84:ea37:7d4'
        self.assertEquals(net_ip.format_ipv6_addr(DUMMY_ADDRESS),
                          '[2001:db8:1:0:f131:fc84:ea37:7d4]')

    @patch('charmhelpers.contrib.network.ip.log')
    def test_format_invalid_ipv6_addr(self, mock_log):
        INVALID_IPV6_ADDR = 'myhost'
        self.assertEquals(net_ip.format_ipv6_addr(INVALID_IPV6_ADDR),
                          None)
        mock_log.assert_called_with(
            'Not a valid ipv6 address: myhost', level='WARNING')

    def test_select_ipv6_global_dynamic_address(self):
        dummy_addresses = ['2001:db8:1:0:f816:3eff:feba:b633',
                           'fe80::f816:3eff:feba:b633']
        self.assertEqual(
            '2001:db8:1:0:f816:3eff:feba:b633',
            net_ip.select_ipv6_global_dynamic_address(dummy_addresses))

    def test_select_ipv6_global_dynamic_address_invalid_address(self):
        INVALID_ADDRESSESS = []
        with nose.tools.assert_raises(Exception):
            net_ip.select_ipv6_global_dynamic_address(INVALID_ADDRESSESS)

        DUMMY_ADDRESS = ['2001:db8:1:0:f816:3eff:feba:0000',
                         'fe80::f816:3eff:feba:b633']
        with nose.tools.assert_raises(Exception):
            net_ip.select_ipv6_global_dynamic_address(DUMMY_ADDRESS)
