import datetime

from unittest import mock

from hamcrest import is_
from hamcrest import has_entries
from hamcrest import assert_that

from nti.app.environments.models.sites import PersistentSite, TrialLicense

from nti.app.environments.views.tests import BaseAppTest
from nti.app.environments.views.tests import ensure_free_txn
from nti.app.environments.views.tests import with_test_app


class TestCheckDNSNameAvailableView(BaseAppTest):

    @with_test_app()
    @mock.patch('nti.app.environments.views.dns._is_dns_name_available')
    @mock.patch('nti.app.environments.views.dns.is_admin_or_account_manager')
    def test_dns(self, mock_admin, mock_available):
        url = '/onboarding/@@check_dns_name'
        params = {}
        self.testapp.get(url, params=params, status=302, extra_environ=self._make_environ(username=None))

        result = self.testapp.get(url, params=params, status=400, extra_environ=self._make_environ(username='user001')).json_body
        assert_that(result['message'], is_('Missing required dns_name'))

        mock_available.return_value = True
        mock_admin.return_value = True

        params = {'dns_name': 'test.com'}
        result = self.testapp.get(url, params=params, status=200, extra_environ=self._make_environ(username='user001')).json_body
        assert_that(result, has_entries({'dns_name': 'test.com',
                                         'is_available': True}))

        mock_available.return_value = True
        mock_admin.return_value = False
        params = {'dns_name': 'test.com'}
        result = self.testapp.get(url, params=params, status=422, extra_environ=self._make_environ(username='user001')).json_body
        assert_that(result, has_entries({'message': 'Invalid dns name.'}))

        mock_available.return_value = False

        params = {'dns_name': 'x.nextthought.io'}
        result = self.testapp.get(url, params=params, status=200, extra_environ=self._make_environ(username='user001')).json_body
        assert_that(result, has_entries({'dns_name': 'x.nextthought.io',
                                         'is_available': False}))

        mock_available.return_value = True

        params = {'dns_name': 'x.nextthought.io'}
        result = self.testapp.get(url, params=params, status=200, extra_environ=self._make_environ(username='user001')).json_body
        assert_that(result, has_entries({'dns_name': 'x.nextthought.io',
                                         'is_available': True}))

        with ensure_free_txn():
            sites = self._root().get('sites')
            sites.addSite(PersistentSite(dns_names=['x.nextthought.io'],
                                         license=TrialLicense(start_date=datetime.datetime(2015,1,1),
                                                              end_date=datetime.datetime(2016,1,1))))

        params = {'dns_name': 'x.nextthought.io'}
        result = self.testapp.get(url, params=params, status=200, extra_environ=self._make_environ(username='user001')).json_body
        assert_that(result, has_entries({'dns_name': 'x.nextthought.io',
                                         'is_available': False}))
