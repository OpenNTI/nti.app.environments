import unittest

from hamcrest import assert_that
from hamcrest import calling
from hamcrest import is_
from hamcrest import has_entries
from hamcrest import raises

import fudge

from zope import interface

from nti.testing.matchers import verifiably_provides

from nti.app.environments.models.sites import PersistentSite

from nti.app.environments.tests import BaseConfiguringLayer

from .. import make_pendo_client

from ..client import BoundPendoClient
from ..client import _pendo_client_for_site

from ..interfaces import IPendoAccount
from ..interfaces import IPendoClient
from ..interfaces import InvalidPendoAccount
from ..interfaces import MissingPendoAccount

class TestPendoClient(unittest.TestCase):

    layer = BaseConfiguringLayer

    def setUp(self):
        self.client = make_pendo_client('secret')

    def test_key_in_headers(self):
        assert_that(self.client.session.headers, has_entries('X-PENDO-INTEGRATION-KEY', 'secret'))
    

    @fudge.patch('nti.app.environments.pendo.client.requests.Session.post')
    def test_update_metadata_set(self, mock_post):
        payload = [{'accountId': 'myaccount',
                    'values': {'prop': 'propvalue'}}]
        
        (mock_post.expects_call()
        .with_args('https://app.pendo.io/api/v1/metadata/account/custom/value', json=payload)
        .returns_fake().is_a_stub())
        
        self.client.update_metadata_set('account', 'custom', payload)

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
        
        assert_that(calling(self.client.set_metadata_for_accounts).with_args({MockAccount(): {'bar': 1}}),
                    raises(MissingPendoAccount))


class TestBoundPendoClient(TestPendoClient):

    layer = BaseConfiguringLayer

    def setUp(self):
        client = make_pendo_client('secret')
        self.client = BoundPendoClient(client)

    def test_account_binding(self):
        # For an unbound client any account validates
        assert_that(self.client.as_account_id('myaccount'), is_('myaccount'))
        assert_that(self.client.check_accountid('myaccount'), is_(True))

        # And we can bind to an account and it still validates
        self.client.bind_account('myaccount')
        assert_that(self.client.as_account_id('myaccount'), is_('myaccount'))
        assert_that(self.client.check_accountid('myaccount'), is_(True))

        # Of course as soon as we are bound we raise exceptions for other accounts
        assert_that(calling(self.client.as_account_id).with_args('anotheraccount'),
                    raises(InvalidPendoAccount))
        assert_that(calling(self.client.check_accountid).with_args('anotheraccount'),
                    raises(InvalidPendoAccount))

        # If we rebind the client, things work as normal again
        self.client.bind_account('anotheraccount')
        assert_that(self.client.as_account_id('anotheraccount'), is_('anotheraccount'))
        assert_that(self.client.check_accountid('anotheraccount'), is_(True))

        # We can even unbind the client all together
        self.client.bind_account(None)
        assert_that(self.client.as_account_id('myaccount'), is_('myaccount'))
        assert_that(self.client.as_account_id('anotheraccount'), is_('anotheraccount'))

    @fudge.patch('nti.app.environments.pendo.client.requests.Session.post')
    def test_update_metadata_set_restricts(self, mock_post):
        payload = [{'accountId': 'myaccount',
                    'values': {'prop': 'propvalue'}}]
        
        # If we are bound to an account, our payload can only be for that account
        self.client.bind_account('myaccount')

        (mock_post.expects_call()
        .with_args('https://app.pendo.io/api/v1/metadata/account/custom/value', json=payload)
        .returns_fake().is_a_stub())
        
        self.client.update_metadata_set('account', 'custom', payload)

        # Trying to send a payload for another account will raise an error
        for obj in payload:
            obj['accountId'] = 'anotheraccount'

        assert_that(calling(self.client.update_metadata_set).with_args('account', 'custom', payload),
                    raises(InvalidPendoAccount))

class TestPendoForSite(unittest.TestCase):

    layer = BaseConfiguringLayer

    def setUp(self):
        site = PersistentSite()
        site.ds_site_id = 'mysite'
        site.id = 'mysiteid'
        self.site = site

    def test_adapter(self):
        client = IPendoClient(self.site)
        assert_that(client, verifiably_provides(IPendoClient))
        assert_that(client.check_accountid(IPendoAccount(self.site).account_id),
                    is_(True))

    def test_pendo_client_for_site(self):
        client = _pendo_client_for_site(self.site)
        assert_that(client, verifiably_provides(IPendoClient))
        assert_that(client.check_accountid(IPendoAccount(self.site).account_id),
                    is_(True))
