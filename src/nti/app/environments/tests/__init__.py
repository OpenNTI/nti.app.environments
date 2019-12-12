import unittest
import nti.app.environments as base_pkg

from zope.configuration.xmlconfig import XMLConfig
from zope.testing.cleanup import cleanUp


class BaseTest(unittest.TestCase):

    def setUp(self):
        XMLConfig(file_name='configure.zcml', module=base_pkg)()

    def tearDown(self):
        cleanUp()
