from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_entry

import fudge

from nti.app.environments.views.tests import BaseAppTest
from nti.app.environments.views.tests import with_test_app
from nti.app.environments.views.tests import ensure_free_txn

import datetime

from nti.app.environments.models.customers import PersistentCustomer

from nti.app.environments.models.sites import PersistentSite
from nti.app.environments.models.sites import TrialLicense
from nti.app.environments.models.sites import SharedEnvironment

from nti.app.environments.models.interfaces import SITE_STATUS_ACTIVE
from nti.app.environments.models.interfaces import SITE_STATUS_INACTIVE

from nti.app.environments.tests import BaseConfiguringLayer

class BaseSubscriptionTest(BaseAppTest):

    def setUp(self):
        super(BaseSubscriptionTest, self).setUp()

        self.customer_email = 'customer@example.com'
        self.siteid = 'S1234'

    def _do_setup_site(self):
        customers = self._root().get('customers')
        customer = customers.addCustomer(
            PersistentCustomer(email=self.customer_email,
                               name="Test Customer"))

        trial = TrialLicense(start_date=datetime.datetime(2019, 12, 12, 0, 0, 0),
                             end_date=datetime.datetime(2019, 12, 13, 0, 0, 0))

        sites = self._root().get('sites')
        site = sites.addSite(PersistentSite(license=trial,
                                            environment=SharedEnvironment(name='test'),
                                            created=datetime.datetime(2019, 12, 11, 0, 0, 0),
                                            status=SITE_STATUS_ACTIVE,
                                            dns_names=['x', 'y'],
                                            owner=customer), siteId=self.siteid)
        return site
            

class TestAssociateSubscriptionInfo( BaseSubscriptionTest ):

    @with_test_app()
    def test_link_subscription(self):
        with ensure_free_txn():
            siteid = self._do_setup_site().id

        url = f'/onboarding/sites/{siteid}/stripe_subscription'

        sub_id = 'sub_1234'

        # only admins should be able to update to link a subscription
        self.testapp.put_json(url,
                              params={'subscription_id': sub_id},
                              status=403,
                              extra_environ=self._make_environ(username=self.customer_email))

        resp = self.testapp.put_json(url,
                                     params={'subscription_id': sub_id},
                                     status=200,
                                     extra_environ=self._make_environ(username='admin001'))
        resp = resp.json_body
        assert_that(resp, has_entry('subscription_id', sub_id))

class TestAssociateSubscriptionInfo( BaseSubscriptionTest ):    

    @property
    def manage_subscription_url(self):
        return '/onboarding/sites/%s/@@manage_subscription' % self.siteid
    
    @with_test_app()
    def test_only_owner_can_see(self):
        with ensure_free_txn():
            self._do_setup_site()

        # Only owner gets a 200, all else gets 403
        self.testapp.get(self.manage_subscription_url,
                          status=403,
                          extra_environ=self._make_environ(username='admin001'))

        self.testapp.get(self.manage_subscription_url,
                         status=200,
                         extra_environ=self._make_environ(username=self.customer_email))

    @with_test_app()
    def test_only_active_site_available(self):
        with ensure_free_txn():
            site = self._do_setup_site()
            site.status = SITE_STATUS_INACTIVE
        
        self.testapp.get(self.manage_subscription_url,
                         status=404,
                         extra_environ=self._make_environ(username=self.customer_email))
    
