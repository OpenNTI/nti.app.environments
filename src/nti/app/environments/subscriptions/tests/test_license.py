import unittest

from hamcrest import assert_that
from hamcrest import is_

from nti.testing.matchers import verifiably_provides

from nti.app.environments.tests import BaseConfiguringLayer

import calendar
import datetime
from datetime import timezone

from zope import component

from stripe.api_resources.plan import Plan
from stripe.api_resources.subscription import Subscription

from nti.app.environments.models.interfaces import IStarterLicense
from nti.app.environments.models.interfaces import IGrowthLicense
from nti.app.environments.models.interfaces import LICENSE_FREQUENCY_MONTHLY
from nti.app.environments.models.interfaces import LICENSE_FREQUENCY_YEARLY

from nti.app.environments.models.sites import PersistentSite

from nti.app.environments.stripe.interfaces import IStripeSubscription

from nti.app.environments.subscriptions.license import stripe_subcription_factory

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
        self.now = datetime.datetime.now(timezone.utc)
        self.subscription = Subscription()
        self.subscription.start_date = self.now.timestamp()
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
