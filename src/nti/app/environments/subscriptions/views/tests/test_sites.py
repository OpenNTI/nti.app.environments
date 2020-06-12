from hamcrest import assert_that
from hamcrest import is_
from hamcrest import not_none
from hamcrest import has_entry
from hamcrest import has_length

import fudge

import unittest

from nti.app.environments.views.tests import BaseAppTest
from nti.app.environments.views.tests import with_test_app
from nti.app.environments.views.tests import ensure_free_txn

from zope import component

import datetime

from nti.app.environments.models.customers import PersistentCustomer

from nti.app.environments.models.sites import PersistentSite
from nti.app.environments.models.sites import TrialLicense
from nti.app.environments.models.sites import SharedEnvironment

from nti.app.environments.stripe.interfaces import IStripeCustomer

from nti.app.environments.models.interfaces import SITE_STATUS_ACTIVE
from nti.app.environments.models.interfaces import SITE_STATUS_INACTIVE

from nti.app.environments.subscriptions.interfaces import IProduct

from nti.app.environments.subscriptions.views.sites import ManageSubscriptionPage

from nti.app.environments.tests import BaseConfiguringLayer

class BaseSubscriptionMixin(object):

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

    def make_site(self):
        customer = PersistentCustomer(email=self.customer_email,
                                      name="Test Customer")

        trial = TrialLicense(start_date=datetime.datetime(2019, 12, 12, 0, 0, 0),
                             end_date=datetime.datetime(2019, 12, 13, 0, 0, 0))

        site = PersistentSite(license=trial,
                              environment=SharedEnvironment(name='test'),
                              created=datetime.datetime(2019, 12, 11, 0, 0, 0),
                              status=SITE_STATUS_ACTIVE,
                              dns_names=['x', 'y'],
                              owner=customer)

        return site
        

class BaseSubscriptionTest(BaseSubscriptionMixin):

    def setUp(self):
        super(BaseSubscriptionTest, self).setUp()

        self.customer_email = 'customer@example.com'
        self.siteid = 'S1234'
            

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

class TestManageSubscriptionInfo( BaseSubscriptionTest ):

    @property
    def manage_subscription_url(self):
        return '/onboarding/sites/%s/stripe_subscription/@@manage' % self.siteid
    
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

    @with_test_app()
    def test_checkout_only_owner(self):
        with ensure_free_txn():
            self._do_setup_site()

        #valid plan and seats
        params = {'plan': 'starter_monthly', 'seats': 3}

        # Only owner gets a 200, all else gets 403
        self.testapp.post(self.manage_subscription_url,
                          params=params,
                          status=403,
                          extra_environ=self._make_environ(username='admin001'))

        self.testapp.post(self.manage_subscription_url,
                          params=params,
                          status=200,
                          extra_environ=self._make_environ(username=self.customer_email))
        
    @with_test_app()
    def test_checkout_validates_seats(self):
        with ensure_free_txn():
            self._do_setup_site()

        #too many seats
        params = {'plan': 'starter_monthly', 'seats': 22}
        self.testapp.post(self.manage_subscription_url,
                          params=params,
                          status=400,
                          extra_environ=self._make_environ(username=self.customer_email))

    @with_test_app()
    def test_checkout_requires_good_plan(self):
        with ensure_free_txn():
            self._do_setup_site()

        #not a valid plan
        params = {'plan': 'starter_weekly', 'seats': 3}
        self.testapp.post(self.manage_subscription_url,
                          params=params,
                          status=400,
                          extra_environ=self._make_environ(username=self.customer_email))

    @with_test_app()
    def test_checkout_requires_active(self):
        with ensure_free_txn():
            site = self._do_setup_site()
            site.status = SITE_STATUS_INACTIVE
        
        self.testapp.get(self.manage_subscription_url,
                         status=404,
                         extra_environ=self._make_environ(username=self.customer_email))

    

class TestProductRegistration(BaseSubscriptionMixin, unittest.TestCase):

    layer = BaseConfiguringLayer

    customer_email = 'customer@example.com'
    siteid = 'S1234'
    
    def test_registered_products(self):
        products = component.getAllUtilitiesRegisteredFor(IProduct)
        assert_that(products, has_length(4))

    def test_finds_prices(self):
        product = component.getUtility(IProduct, name="starter")
        assert_that(product.yearly_price, not_none())
        assert_that(product.monthly_price, not_none())
        assert_that(product.monthly_price.product, is_(product))

    def test_view_data(self):
        site = self.make_site()
        view = ManageSubscriptionPage(site, None)
        product_info = view.plan_options()

        assert_that(product_info, is_({'product_details':
                                       {'enterprise': {'cost': 299},
                                        'growth': {
                                            'plans': [
                                                {'cost': 199,
                                                 'frequency': 'yearly',
                                                 'plan_id': 'growth_yearly'},
                                                {'cost': 239,
                                                 'frequency': 'monthly',
                                                 'plan_id': 'growth_monthly'}
                                            ],
                                            'seat_options': [x+1 for x in range(0,10)]
                                        },
                                        'starter': {
                                            'plans': [
                                                {'cost': 99,
                                                 'frequency': 'yearly',
                                                 'plan_id': 'starter_yearly'},
                                                {'cost': 119,
                                                 'frequency': 'monthly',
                                                 'plan_id': 'starter_monthly'}],
                                            'seat_options': [x+1 for x in range(0,5)]
                                        },
                                        'trial': {'cost': 0}},
                                       'products': ['trial', 'starter', 'growth', 'enterprise']}
        ))

    

    
        
        
    
