"""
Test full system.

Tests the system initialization and attributes of
the main Blink system.  Tests if we properly catch
any communication related errors at startup.
"""

import unittest
from unittest import mock
from blinkpy import blinkpy
from blinkpy.sync_module import BlinkSyncModule
from blinkpy.helpers.util import (
    http_req, create_session, BlinkAuthenticationException,
    BlinkException, BlinkURLHandler)
import tests.mock_responses as mresp

USERNAME = 'foobar'
PASSWORD = 'deadbeef'


@mock.patch('blinkpy.helpers.util.Session.send',
            side_effect=mresp.mocked_session_send)
class TestBlinkSetup(unittest.TestCase):
    """Test the Blink class in blinkpy."""

    def setUp(self):
        """Set up Blink module."""
        self.blink_no_cred = blinkpy.Blink()
        self.blink = blinkpy.Blink(username=USERNAME,
                                   password=PASSWORD)
        self.blink.sync = BlinkSyncModule(self.blink, dict(), self.blink.urls)

    def tearDown(self):
        """Clean up after test."""
        self.blink = None
        self.blink_no_cred = None

    def test_initialization(self, mock_sess):
        """Verify we can initialize blink."""
        # pylint: disable=protected-access
        self.assertEqual(self.blink._username, USERNAME)
        # pylint: disable=protected-access
        self.assertEqual(self.blink._password, PASSWORD)

    def test_no_credentials(self, mock_sess):
        """Check that we throw an exception when no username/password."""
        with self.assertRaises(BlinkAuthenticationException):
            self.blink_no_cred.get_auth_token()
        # pylint: disable=protected-access
        self.blink_no_cred._username = USERNAME
        with self.assertRaises(BlinkAuthenticationException):
            self.blink_no_cred.get_auth_token()

    def test_no_auth_header(self, mock_sess):
        """Check that we throw an exception when no auth header given."""
        # pylint: disable=unused-variable
        (region_id, region), = mresp.LOGIN_RESPONSE['region'].items()
        self.blink.urls = BlinkURLHandler(region_id)
        with self.assertRaises(BlinkException):
            self.blink.get_ids()
        with self.assertRaises(BlinkException):
            self.blink.summary_request()

    @mock.patch('blinkpy.blinkpy.getpass.getpass')
    def test_manual_login(self, getpwd, mock_sess):
        """Check that we can manually use the login() function."""
        getpwd.return_value = PASSWORD
        with mock.patch('builtins.input', return_value=USERNAME):
            self.assertTrue(self.blink_no_cred.login())
        # pylint: disable=protected-access
        self.assertEqual(self.blink_no_cred._username, USERNAME)
        # pylint: disable=protected-access
        self.assertEqual(self.blink_no_cred._password, PASSWORD)

    def test_bad_request(self, mock_sess):
        """Check that we raise an Exception with a bad request."""
        self.blink.session = create_session()
        with self.assertRaises(BlinkException):
            http_req(self.blink, reqtype='bad')

        with self.assertRaises(BlinkAuthenticationException):
            http_req(self.blink, reqtype='post', is_retry=True)

    def test_authentication(self, mock_sess):
        """Check that we can authenticate Blink up properly."""
        authtoken = self.blink.get_auth_token()['TOKEN_AUTH']
        expected = mresp.LOGIN_RESPONSE['authtoken']['authtoken']
        self.assertEqual(authtoken, expected)

    def test_reauthorization_attempt(self, mock_sess):
        """Check that we can reauthorize after first unsuccessful attempt."""
        original_header = self.blink.get_auth_token()
        # pylint: disable=protected-access
        bad_header = {'Host': self.blink._host, 'TOKEN_AUTH': 'BADTOKEN'}
        # pylint: disable=protected-access
        self.blink._auth_header = bad_header
        # pylint: disable=protected-access
        self.assertEqual(self.blink._auth_header, bad_header)
        self.blink.summary_request()
        # pylint: disable=protected-access
        self.assertEqual(self.blink._auth_header, original_header)
