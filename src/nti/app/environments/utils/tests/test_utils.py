from hamcrest import assert_that
from hamcrest import is_
from hamcrest import is_not

import unittest

from nti.testing.matchers import verifiably_provides

from nti.testing.layers import ZopeComponentLayer

from zope import component

from zope.testing.cleanup import cleanUp

from io import StringIO

import os

from .. import _parse_settings
from .. import run_with_onboarding
from .. import run_as_onboarding_main

from nti.app.environments.interfaces import IOnboardingSettings
from nti.app.environments.models.interfaces import IOnboardingRoot

from nti.environments.management.interfaces import ISettings

from nti.environments.management.config import configure_settings

from nti.environments.management import tests

class ScriptsTestingLayer(ZopeComponentLayer):
    pass

class ConfiguredScriptsLayer(ScriptsTestingLayer):

    @classmethod
    def testSetUp(cls):
        settings = {
            'google_client_id': 'xxx',
            'google_client_secret': 'yyy',
            'hubspot_api_key': 'zzz',
            'hubspot_portal_id': 'kkk',
            'nti.environments.management.config': os.path.join(os.path.dirname(tests.__file__), 'test.ini'),
            'zodbconn.uri': 'memory://'
        }

        configure_settings(settings)

        component.getGlobalSiteManager().registerUtility(settings, IOnboardingSettings)

        cls.__envsettings = component.getUtility(ISettings)
        cls.__settings = settings

    @classmethod
    def testTearDown(cls):
        component.getGlobalSiteManager().unregisterUtility(cls.__settings, IOnboardingSettings)
        component.getGlobalSiteManager().unregisterUtility(cls.__envsettings, ISettings)
        cleanUp()

class TestRunWithOnboardingSettings(unittest.TestCase):

    layer = ScriptsTestingLayer

    @property
    def settings_file(self):
        return os.path.join(os.path.dirname(__file__), 'settings.ini')
        

    def test_settings(self):
        assert_that(component.queryUtility(IOnboardingSettings), is_(None))
        _parse_settings(self.settings_file)
        settings = component.queryUtility(IOnboardingSettings)
        assert_that(settings['foo'], is_('bar'))

        settings = component.queryUtility(ISettings)
        assert_that(component.queryUtility(ISettings), is_not(None))


class TestRunWithOnboarding(unittest.TestCase):

    layer = ConfiguredScriptsLayer
    
    def test_run_with_onboarding(self):

        def _with_root(root):
            assert_that(root, verifiably_provides(IOnboardingRoot))
            return True

        result = run_with_onboarding(function=_with_root)

        assert_that(result, is_(True))

    def test_run_as_main(self):

        def _with_root(args, root):
            assert_that(root, verifiably_provides(IOnboardingRoot))
            assert_that(args.pool_size, is_(5))

        with run_as_onboarding_main(_with_root, main_args=['-v','-c', 'foo']) as parser:
            parser.add_argument('-p', '--pool-size',
                            dest='pool_size',
                            type=int,
                            default=5)
