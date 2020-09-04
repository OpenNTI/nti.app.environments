import unittest

from hamcrest import assert_that
from hamcrest import is_

import fudge

from nti.app.environments.tests import BaseConfiguringLayer

from nti.app.environments.models.sites import PersistentSite

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
