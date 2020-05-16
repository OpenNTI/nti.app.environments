from hamcrest import assert_that
from hamcrest import is_

import unittest

import datetime

from nti.app.environments.tests import BaseConfiguringLayer

from nti.app.environments.models.sites import PersistentSite
from nti.app.environments.models.sites import TrialLicense

from ..evolve1 import migrate_site_license

class TestEvolve1(unittest.TestCase):

    layer = BaseConfiguringLayer
    
    def test_evolve(self):
        site = PersistentSite()
        
        _start = datetime.datetime(2019, 12, 11, 0, 0, 0)
        _end = datetime.datetime(2019, 12, 12, 0, 0, 0)
        inst = TrialLicense(start_date=_start,
                            end_date=_end)
        site.__dict__['license'] = inst

        assert_that(inst.__parent__, is_(None))

        migrate_site_license(site)

        assert_that(site.license, is_(inst))
        assert_that(inst.__parent__, is_(site))
        
