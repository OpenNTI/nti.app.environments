import datetime

from unittest import mock

from hamcrest import is_
from hamcrest import has_entries
from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import has_items

from nti.app.environments.models.sites import PersistentSite, TrialLicense

from nti.app.environments.views.dns import ValidDomainView

from nti.app.environments.views.tests import BaseAppTest
from nti.app.environments.views.tests import ensure_free_txn
from nti.app.environments.views.tests import with_test_app


class TestCheckDNSNameAvailableView(BaseAppTest):

    @with_test_app()
    @mock.patch('nti.app.environments.views.utils._is_dns_name_available')
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

class TestValidDomainView(BaseAppTest):

    @with_test_app()
    def test_is_suffix_available(self):
        root = self._root()
        view = ValidDomainView(root, self.request)

        assert_that(hasattr(view, '_suffixes'), is_(False))
        assert_that(view._is_suffix_available('6969'), is_(False))
        assert_that(view._is_suffix_available('6660'), is_(False))
        assert_that(view._is_suffix_available('0420'), is_(False))
        assert_that(view._suffixes, has_length(0))

        assert_that(view._is_suffix_available('3456'), is_(True))
        assert_that(view._is_suffix_available('1234'), is_(True))
        assert_that(view._suffixes, has_length(2))
        assert_that(view._suffixes, has_items('1234', '3456'))

        assert_that(view._is_suffix_available('3456'), is_(False))
        assert_that(view._is_suffix_available('1234'), is_(False))
        assert_that(view._is_suffix_available('4200'), is_(False))

    @with_test_app()
    @mock.patch('nti.app.environments.views.utils._is_dns_name_available')
    @mock.patch('nti.app.environments.views.dns._generate_digits')
    def test_generate_dns_name(self, mock_generate_digits, mock_available):
        mock_available.return_value = True
        subdomain = 'okc'
        domain = 'nextthought.io'
        root = self._root()

        view = ValidDomainView(root, self.request)
        view._suffixes = set(['1234', '3456'])

        mock_generate_digits.return_value = '1234'
        assert_that(view._generate_dns_name(subdomain, domain, 3), is_(None))

        mock_generate_digits.return_value = '3456'
        assert_that(view._generate_dns_name(subdomain, domain, 3), is_(None))

        mock_generate_digits.return_value = '6666'
        assert_that(view._generate_dns_name(subdomain, domain, 3), is_(None))

        mock_generate_digits.return_value = '7890'
        assert_that(view._generate_dns_name(subdomain, domain, 3), is_('okc-7890.nextthought.io'))

        mock_available.return_value = False
        mock_generate_digits.return_value = '9087'
        assert_that(view._generate_dns_name(subdomain, domain, 3), is_(None))

    @with_test_app()
    @mock.patch('nti.app.environments.views.utils._is_dns_name_available')
    @mock.patch('nti.app.environments.views.dns.is_admin_or_account_manager')
    @mock.patch('nti.app.environments.views.dns.ValidDomainView._generate_dns_name')
    def test_get(self, mock_generate_dns, mock_admin, mock_available):
        url = '/onboarding/@@valid_domain'
        params = {}
        self.testapp.get(url, params=params, status=302, extra_environ=self._make_environ(username=None))
        result = self.testapp.get(url, params=params, status=400, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'message': 'Missing required subdomain'}))

        mock_admin.return_value = True
        mock_available.return_value = True
        params = {'subdomain': 'okc'}
        result = self.testapp.get(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'is_available': True,
                                                   'dns_name': 'okc.nextthought.io',
                                                   'subdomain': 'okc',
                                                   'domain': 'nextthought.io'}))

        mock_admin.return_value = True
        mock_available.return_value = False
        params = {'subdomain': 'okc'}
        result = self.testapp.get(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'is_available': False,
                                                   'dns_name': 'okc.nextthought.io',
                                                   'subdomain': 'okc',
                                                   'domain': 'nextthought.io'}))

        mock_admin.return_value = False
        mock_generate_dns.return_value = 'okc-1234.nextthought.io'
        params = {'subdomain': 'okc'}
        result = self.testapp.get(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'is_available': True,
                                                   'dns_name': 'okc-1234.nextthought.io',
                                                   'subdomain': 'okc',
                                                   'domain': 'nextthought.io'}))

        mock_admin.return_value = False
        mock_generate_dns.return_value = None
        params = {'subdomain': 'okc'}
        result = self.testapp.get(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'is_available': False,
                                                   'dns_name': None,
                                                   'subdomain': 'okc',
                                                   'domain': 'nextthought.io'}))
