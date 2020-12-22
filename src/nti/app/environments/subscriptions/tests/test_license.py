import fudge

import unittest

from hamcrest import assert_that
from hamcrest import is_

from nti.testing.matchers import verifiably_provides

from nti.app.environments.tests import BaseConfiguringLayer

import calendar
import datetime
from datetime import timezone

from zope import component
from zope import interface

from zope.event import notify

from stripe.api_resources.plan import Plan
from stripe.api_resources.subscription import Subscription
from stripe.util import convert_to_stripe_object

from nti.app.environments.models.interfaces import SITE_STATUS_ACTIVE
from nti.app.environments.models.interfaces import IStarterLicense
from nti.app.environments.models.interfaces import IGrowthLicense
from nti.app.environments.models.interfaces import LICENSE_FREQUENCY_MONTHLY
from nti.app.environments.models.interfaces import LICENSE_FREQUENCY_YEARLY
from nti.app.environments.models.interfaces import ILMSSite

from nti.app.environments.models.sites import PersistentSite
from nti.app.environments.models.sites import StarterLicense

from nti.app.environments.stripe.interfaces import IStripeSubscription
from nti.app.environments.stripe.interfaces import iface_for_event
from nti.app.environments.stripe.billing import MinimalStripeSubscription

from nti.app.environments.subscriptions.license import stripe_subcription_factory

from nti.app.environments.views.tests import BaseAppTest
from nti.app.environments.views.tests import with_test_app
from nti.app.environments.views.tests import ensure_free_txn


from ..license import starter_factory
from ..license import growth_factory


class TestSiteSubscription(unittest.TestCase):

    layer = BaseConfiguringLayer

    def setUp(self):
        self.site = PersistentSite()

    def test_can_associate_subscription(self):
        IStripeSubscription(self.site).id = 'sub_123'
        assert_that(stripe_subcription_factory(self.site, create=False).id, is_('sub_123'))

    def test_no_subscription_by_default(self):
        assert_that(stripe_subcription_factory(self.site, create=False), is_(None))

class TestLicenseFactory(unittest.TestCase):

    layer = BaseConfiguringLayer

    def setUp(self):
        self.now = datetime.datetime.utcnow().replace(microsecond=0) #Drop the partial seconds as we lose them in our timestamp we generate
        self.subscription = Subscription()
        self.subscription.start_date = calendar.timegm(self.now.utctimetuple())
        self.subscription.quantity = 10
        self.subscription.plan = Plan()
        self.subscription.plan.interval = 'month'
        
    
    def test_starter_factory(self):
        license = starter_factory(self.subscription)
        assert_that(license, verifiably_provides(IStarterLicense))
        assert_that(license.seats, is_(10))
        assert_that(license.frequency, is_(LICENSE_FREQUENCY_MONTHLY))
        assert_that(license.start_date, is_(self.now))

    def test_growth_factory(self):
        self.subscription.plan.interval = 'year'
        
        license = starter_factory(self.subscription)
        assert_that(license, verifiably_provides(IStarterLicense))
        assert_that(license.seats, is_(10))
        assert_that(license.frequency, is_(LICENSE_FREQUENCY_YEARLY))
        assert_that(license.start_date, is_(self.now))


SUB = {
    "id": "sub_ISMf7NK8PCsuqR",
    "object": "subscription",
    "current_period_end": 12345,
    "current_period_start": 1234
}

INV = {
    "id": "in_0Hzpn3fWolyj2wJcQOf6sNz7",
    "object": "invoice",
    "subscription" : SUB
}

INVOICE_PAID_EVENT = {
    "id": "evt_1GlEeIJSl3QXdEfxphYmtYDf",
    "object": "event",
    "api_version": "2020-03-02",
    "created": 1590068486,
    "data": {
        "object": INV
    },
    "livemode": False,
    "pending_webhooks": 0,
    "request": {
        "id": None,
        "idempotency_key": None
    },
    "type": "invoice.paid"
}


class TestPaidInvoiceHandling(BaseAppTest):

    @with_test_app()
    @fudge.patch('nti.app.environments.subscriptions.license.get_onboarding_root')
    def test_find_site_by_subscription(self, mock_get_root):
        mock_get_root.is_callable().returns(self._root())
        
        sites = self._root()['sites']
        site1 = sites.addSite(PersistentSite())
        site2 = sites.addSite(PersistentSite())

        # A site's subscription finds itself
        sub = IStripeSubscription(site1)
        IStripeSubscription(site1).id = 'sub_site1'

        assert_that(ILMSSite(sub), is_(site1))

        # But we can't find a subscription that doesn't exist
        sub = MinimalStripeSubscription(subscription_id='foo')
        assert_that(component.queryAdapter(sub, ILMSSite), is_(None))

    @with_test_app()
    @fudge.patch('nti.app.environments.subscriptions.license.get_onboarding_root')
    def test_invoice_paid_moves_end_date(self, mock_get_root):
        mock_get_root.is_callable().returns(self._root())
        
        sites = self._root()['sites']
        site1 = sites.addSite(PersistentSite())
        end_date = datetime.datetime(2020, 1, 11, 0, 0, 0)
        site1.license = StarterLicense(start_date=datetime.datetime(2019, 12, 11, 0, 0, 0),
                                       end_date=end_date,
                                       frequency='monthly',
                                       seats=3,
                                       additional_instructor_seats=2)

        # A site's subscription finds itself
        sub = IStripeSubscription(site1)
        IStripeSubscription(site1).id = 'sub_site1'
        
        event = convert_to_stripe_object(INVOICE_PAID_EVENT)
        event.data.object.subscription.id = 'sub_site1'
        interface.alsoProvides(event, iface_for_event(event))

        # Only active sites are modified
        notify(event)
        assert_that(site1.license.end_date, is_(end_date))

        # Now make the site active
        site1.status = SITE_STATUS_ACTIVE
        # And lets see how our end_date updates
        new_end_date = datetime.datetime(2020, 2, 11, 0, 0, 0)
        event.data.object.subscription.current_period_end = calendar.timegm(new_end_date.utctimetuple())

        notify(event)
        assert_that(site1.license.end_date, is_(new_end_date))

        # We dont blow for subscriptions we don't know about
        event.data.object.subscription = 'foobar'
        notify(event)

        # And if we get an invoice that has no subscription we ignore that as well
        event.data.object.subscription = None
        notify(event)
        

    
