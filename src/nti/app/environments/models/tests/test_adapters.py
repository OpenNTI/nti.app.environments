from hamcrest import is_
from hamcrest import assert_that
from hamcrest import has_properties

from nti.testing.matchers import verifiably_provides

from zope.annotation.interfaces import IAnnotations

from nti.app.environments.tests import BaseTest
from nti.app.environments.models.adapters import site_usage_factory
from nti.app.environments.models.interfaces import ISiteUsage
from nti.app.environments.models.sites import PersistentSite


class TestAdapters(BaseTest):

    def test_site_usage_factory(self):
        site = PersistentSite()
        assert_that(site_usage_factory(site, False), is_(None))
        
        usage = ISiteUsage(site)
        assert_that(usage, verifiably_provides(ISiteUsage))
        assert_that(usage.__name__, is_('SiteUsage'))
        assert_that(usage.__parent__, is_(site))
