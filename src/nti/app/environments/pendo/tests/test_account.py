import unittest

from hamcrest import assert_that
from hamcrest import is_

import fudge

from nti.testing.matchers import verifiably_provides

from nti.app.environments.tests import BaseConfiguringLayer

from nti.app.environments.models.sites import PersistentSite

from ..account import _test_pendo_account

from ..interfaces import IPendoAccount


class TestPendoAccount(unittest.TestCase):

    layer = BaseConfiguringLayer

    def setUp(self):
        self.site = PersistentSite()
        self.account = IPendoAccount(self.site)
    
    def test_adapter(self):
        assert_that(IPendoAccount.providedBy(self.account), is_(True))

    def test_account_prefers_dsid(self):
        self.site.ds_site_id = 'bar'
        assert_that(IPendoAccount(self.site).account_id, is_('bar::bar'))

    @fudge.patch('nti.app.environments.pendo.account.NTClient.dataserver_ping')
    def test_account_id(self, client):
        client.expects_call().returns({'Site': 'Foo.nt.io'})
        assert_that(self.account.account_id, is_('Foo.nt.io::Foo.nt.io'))

    @fudge.patch('nti.app.environments.pendo.account.NTClient.dataserver_ping')
    def test_account_url(self, client):
        client.expects_call().returns({'Site': 'beta.nextthought.com'})
        assert_that(self.account.account_web_url, is_('https://app.pendo.io/account/beta.nextthought.com%3A%3Abeta.nextthought.com'))

    def test_test_account(self):
        self.site.ds_site_id='S0001'
        self.site.dns_names = ['client.nextthought.io']
        account = _test_pendo_account(self.site)
        assert_that(account, is_(None))

        self.site.dns_names = ['client.nextthot.com']
        account = _test_pendo_account(self.site)
        assert_that(account, verifiably_provides(IPendoAccount))
        assert_that(account.account_id, is_('S0001::S0001'))
