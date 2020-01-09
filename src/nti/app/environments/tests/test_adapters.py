from hamcrest import assert_that
from hamcrest import not_none

from zope.securitypolicy.interfaces import IPrincipalRoleManager

from nti.app.environments.models import OnboardingRoot

from nti.app.environments.tests import BaseTest


class TestAdapters(BaseTest):

    def test_principal_role_manager(self):
        onboarding = OnboardingRoot()
        mgr = IPrincipalRoleManager(onboarding, None)
        assert_that(mgr, not_none())
