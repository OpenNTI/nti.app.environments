import unittest

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_entries
from hamcrest import has_key
from hamcrest import not_

import datetime

from nti.app.environments.tests import BaseConfiguringLayer

from nti.app.environments.models.interfaces import SITE_STATUS_ACTIVE

from nti.app.environments.models.sites import PersistentSite
from nti.app.environments.models.sites import TrialLicense
from nti.app.environments.models.sites import StarterLicense
from nti.app.environments.models.sites import EnterpriseLicense

from nti.app.environments.pendo.subscribers import PendoSiteStatusPublisher

class TestPendoSiteStatusPayload(unittest.TestCase):

    layer = BaseConfiguringLayer

    def setUp(self):
        site = PersistentSite()
        site.status = SITE_STATUS_ACTIVE

        _start = datetime.datetime(2019, 12, 11, 0, 0, 0)
        _end = datetime.datetime(2019, 12, 12, 0, 0, 0)
        self.license = TrialLicense(start_date=_start,
                                    end_date=_end)
        site.license = self.license
        
        self.site = site

    def test_trial_payload(self):
        publisher = PendoSiteStatusPublisher(self.site)
        payload = publisher._build_payload()

        assert_that(payload, has_entries('sitestatus', 'ACTIVE',
                                         'sitelicensetype', 'trial',
                                         'sitelicensefrequency', 'unknown',
                                         'sitelicenseseats', 65535,
                                         'sitetrialenddate', '2019-12-12T00:00:00'))

    def test_starter_payload(self):
        inst = StarterLicense(start_date=datetime.datetime(2019, 12, 11, 0, 0, 0),
                              frequency='monthly',
                              seats=3)
        self.site.license = inst

        publisher = PendoSiteStatusPublisher(self.site)
        payload = publisher._build_payload()

        assert_that(payload, has_entries('sitestatus', 'ACTIVE',
                                         'sitelicensetype', 'starter',
                                         'sitelicensefrequency', 'monthly',
                                         'sitelicenseseats', 3))
        assert_that(payload, not_(has_key('sitetrialenddate')))
