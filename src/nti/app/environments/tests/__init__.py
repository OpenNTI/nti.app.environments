import os
import unittest
import nti.app.environments as base_pkg

from zope.configuration.xmlconfig import XMLConfig
from zope.testing.cleanup import cleanUp

from nti.environments.management.config import configure_settings
from nti.environments.management import tests


class BaseTest(unittest.TestCase):

    def setUp(self):
        settings = {
            'nti.environments.management.config': os.path.join(os.path.dirname(tests.__file__), 'test.ini')
        }
        configure_settings(settings)
        XMLConfig(file_name='configure.zcml', module=base_pkg)()

    def tearDown(self):
        cleanUp()
