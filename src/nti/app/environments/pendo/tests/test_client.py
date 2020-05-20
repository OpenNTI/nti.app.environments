import unittest

from hamcrest import assert_that
from hamcrest import calling
from hamcrest import is_
from hamcrest import has_entries
from hamcrest import raises

import fudge

from zope import interface

from nti.app.environments.tests import BaseConfiguringLayer

from .. import make_pendo_client

from ..interfaces import IPendoAccount

class TestPendoClient(unittest.TestCase):

    layer = BaseConfiguringLayer

    def setUp(self):
        self.client = make_pendo_client('secret')

    def test_key_in_headers(self):
        assert_that(self.client.session.headers, has_entries('X-PENDO-INTEGRATION-KEY', 'secret'))

    @fudge.patch('nti.app.environments.pendo.client.requests.Session.post')
    def test_update_metadata_set(self, mock_post):
        (mock_post.expects_call()
        .with_args('https://app.pendo.io/api/v1/metadata/account/custom/value', json={})
        .returns_fake().is_a_stub())
        
        self.client.update_metadata_set('account', 'custom', {})

    @fudge.patch('nti.app.environments.pendo.client.PendoV1Client.update_metadata_set')
    def test_set_metadata(self, mock_updater):

        @interface.implementer(IPendoAccount)
        class MockAccount(object):
            account_id = 'foo'
        
        mock_updater.expects_call().with_args('account', 'custom', [{'accountId': 'foo', 'values': {'bar': 1}}])
        self.client.set_metadata_for_accounts({MockAccount(): {'bar': 1}})

    @fudge.patch('nti.app.environments.pendo.client.PendoV1Client.update_metadata_set')
    def test_set_metadata(self, mock_updater):       
        mock_updater.expects_call().with_args('account', 'custom', [{'accountId': 'foo', 'values': {'bar': 1}}])
        self.client.set_metadata_for_accounts({'foo': {'bar': 1}})

    
    @fudge.patch('nti.app.environments.pendo.client.PendoV1Client.update_metadata_set')
    def test_set_metadata_without_account(self, mock_updater):

        @interface.implementer(IPendoAccount)
        class MockAccount(object):
            account_id = None
        
        assert_that(calling(self.client.set_metadata_for_accounts).with_args({MockAccount(): {'bar': 1}}), raises(ValueError))
