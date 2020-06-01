from hamcrest import assert_that
from hamcrest import not_
from hamcrest import has_key

import unittest

import datetime

from nti.testing.matchers import verifiably_provides

from nti.app.environments.tests import BaseConfiguringLayer

from nti.app.environments.models import OnboardingRoot

from nti.app.environments.subscriptions.interfaces import ICheckoutSessionStorage
from nti.app.environments.subscriptions.sessions import STRIPE_CHECKOUT_SESSIONS_KEY

from ..evolve2 import install_stripe_sessions

class TestEvolve2(unittest.TestCase):

    layer = BaseConfiguringLayer
    
    def test_evolve(self):
        root = OnboardingRoot()
        assert_that(root, not_(has_key(STRIPE_CHECKOUT_SESSIONS_KEY)))

        install_stripe_sessions(root)

        assert_that(root[STRIPE_CHECKOUT_SESSIONS_KEY], verifiably_provides(ICheckoutSessionStorage))
        
