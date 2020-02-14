import os
import unittest
import nti.app.environments as base_pkg

from zope import component

from zope.configuration.xmlconfig import XMLConfig
from zope.testing.cleanup import cleanUp

from nti.app.environments.interfaces import IOnboardingSettings

from nti.environments.management.config import configure_settings
from nti.environments.management import tests


class BaseTest(unittest.TestCase):

    def setUp(self):
        settings = {
            'google_client_id': 'xxx',
            'google_client_secret': 'yyy',
            'hubspot_api_key': 'zzz',
            'hubspot_portal_id': 'kkk',
            'nti.environments.management.config': os.path.join(os.path.dirname(tests.__file__), 'test.ini')
        }
        configure_settings(settings)

        component.getGlobalSiteManager().registerUtility(settings, IOnboardingSettings)

        XMLConfig(file_name='configure.zcml', module=base_pkg)()

    def tearDown(self):
        cleanUp()
