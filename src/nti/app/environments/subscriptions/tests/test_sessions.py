import unittest

from hamcrest import assert_that
from hamcrest import is_

import fudge

from nti.testing.matchers import provides
from nti.testing.matchers import verifiably_provides

from nti.app.environments.tests import BaseConfiguringLayer

from nti.app.environments.models.customers import  PersistentCustomer

from nti.app.environments.models.sites import PersistentSite

from ..sessions import ICheckoutSession
from ..sessions import ICheckoutSessionStorage

from ..sessions import CheckoutSessionStorage

class TestCheckoutSessions(unittest.TestCase):

    layer = BaseConfiguringLayer

    def setUp(self):
        self.storage = CheckoutSessionStorage()
        self.site = PersistentSite()
        self.customer =  PersistentCustomer()

    def test_provides(self):
        assert_that(self.storage, verifiably_provides(ICheckoutSessionStorage))

    def test_not_found(self):
        assert_that(self.storage.find_session('foo'), is_(None))

    def test_track_session(self):
        session = self.storage.track_session(self.customer, self.site)

        assert_that(session, provides(ICheckoutSession))

        found = self.storage.find_session(session.id)
        assert_that(found, is_(session))
