import datetime
import tempfile
import shutil
import os

from unittest import mock
from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import has_entries
from hamcrest import has_properties
from hamcrest import instance_of
from hamcrest import contains_string
from hamcrest import starts_with
from hamcrest import calling
from hamcrest import raises
from hamcrest import is_

from pyramid_mailer.interfaces import IMailer
from pyramid_mailer import Mailer
from pyramid import httpexceptions as hexc

from zope import component

from zope.interface.exceptions import Invalid

from nti.externalization import to_external_object
from nti.externalization.internalization.updater import update_from_external_object

from nti.app.environments.views.customers import getOrCreateCustomer
from nti.app.environments.views.sites import SitesUploadCSVView
from nti.app.environments.views.tests import BaseAppTest
from nti.app.environments.views.tests import with_test_app
from nti.app.environments.views.tests import ensure_free_txn
from nti.app.environments.models.customers import PersistentCustomer
from nti.app.environments.models.hosts import PersistentHost
from nti.app.environments.models.sites import TrialLicense
from nti.app.environments.models.sites import EnterpriseLicense
from nti.app.environments.models.sites import PersistentSite
from nti.app.environments.models.sites import SharedEnvironment
from nti.app.environments.models.interfaces import ICustomer, ISiteUsage
from nti.app.environments.models.interfaces import IEnterpriseLicense
from nti.app.environments.models.interfaces import ITrialLicense
from nti.app.environments.models.interfaces import ISharedEnvironment
from nti.app.environments.models.interfaces import IDedicatedEnvironment


def _absolute_path(filename):
    return os.path.join(os.path.dirname(__file__), 'resources/'+filename)


class TestHosts(BaseAppTest):

    @with_test_app()
    def testHostsViews(self):
        url = '/onboarding/hosts'
        params = {'host_name': 'okc', 'capacity': 10, 'MimeType': 'application/vnd.nextthought.app.environments.host'}
        self.testapp.post_json(url, params=params, status=302, extra_environ=self._make_environ(username=None))
        self.testapp.post_json(url, params=params, status=403, extra_environ=self._make_environ(username='user001'))
        result = self.testapp.post_json(url, params=params, status=201, extra_environ=self._make_environ(username='admin001')).json_body
        assert_that(result, has_entries({'host_name': 'okc',
                                         'capacity': 10,
                                         'current_load': 0}))

        result = self.testapp.post_json(url, params=params, status=409, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'message': "Existing host: okc."}))

        params = {'host_name': 'okc2', 'capacity': "ddd", 'MimeType': 'application/vnd.nextthought.app.environments.host'}
        result = self.testapp.post_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'message': "invalid literal for int() with base 10: 'ddd'"}))

        params = {'host_name': 'okc2', 'capacity': 20, 'MimeType': 'application/vnd.nextthought.app.environments.host'}
        result = self.testapp.post_json(url, params=params, status=201, extra_environ=self._make_environ(username='admin001')).json_body
        assert_that(result, has_entries({'host_name': 'okc2',
                                         'capacity': 20,
                                         'current_load': 0}))
        host_id2 = result['id']

        # update
        url = '/onboarding/hosts/%s' % host_id2
        params = {'host_name': 'okc3', 'capacity': 30}
        self.testapp.put_json(url, params=params, status=302, extra_environ=self._make_environ(username=None))
        self.testapp.put_json(url, params=params, status=403, extra_environ=self._make_environ(username='user001'))
        result = self.testapp.put_json(url, params=params, status=200, extra_environ=self._make_environ(username='admin001')).json_body
        assert_that(result, has_entries({'host_name': 'okc3',
                                         'capacity': 30,
                                         'current_load': 0}))

        params = {'host_name': 'okc3', 'capacity': 30}
        result = self.testapp.put_json(url, params=params, status=200, extra_environ=self._make_environ(username='admin001')).json_body
        assert_that(result, has_entries({'host_name': 'okc3',
                                         'capacity': 30,
                                         'current_load': 0}))

        params = {'host_name': 'okc', 'capacity': 30}
        result = self.testapp.put_json(url, params=params, status=409, extra_environ=self._make_environ(username='admin001')).json_body
        assert_that(result['message'], is_('Existing host: okc.'))

        # delete
        self.testapp.delete(url, status=302, extra_environ=self._make_environ(username=None))
        self.testapp.delete(url, status=403, extra_environ=self._make_environ(username='user001'))
        self.testapp.delete(url, status=204, extra_environ=self._make_environ(username='admin001'))

    @with_test_app()
    def testHostsListView(self):
        url = '/onboarding/hosts/@@list'
        self.testapp.get(url, status=302, extra_environ=self._make_environ(username=None))
        self.testapp.get(url, status=403, extra_environ=self._make_environ(username='user001'))
        self.testapp.get(url, status=200, extra_environ=self._make_environ(username='admin001'))
