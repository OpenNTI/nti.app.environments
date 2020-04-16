import time
import datetime

from unittest import mock
from hamcrest import is_
from hamcrest import not_none
from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import has_entries
from hamcrest import instance_of

from nti.app.environments.models.interfaces import SITE_STATUS_OPTIONS
from nti.app.environments.models.interfaces import SHARED_ENV_NAMES

from nti.app.environments.models.customers import PersistentCustomer
from nti.app.environments.models.customers import HubspotContact
from nti.app.environments.models.sites import PersistentSite, TrialLicense,\
    SharedEnvironment

from nti.app.environments.views.admin_views import SitesListView
from nti.app.environments.views.admin_views import SiteDetailView
from nti.app.environments.views.admin_views import CustomersListView
from nti.app.environments.views.admin_views import CustomerDetailView
from nti.app.environments.views.admin_views import TrialSitesDigestEmailView

from nti.app.environments.views.tests import BaseAppTest
from nti.app.environments.views.tests import with_test_app
from nti.app.environments.views.tests import ensure_free_txn
from nti.app.environments.views._table_utils import SitesTable
from nti.app.environments.views._table_utils import CustomersTable


class TestAdminViews(BaseAppTest):

    @with_test_app()
    def testCustomersListView(self):
        url = '/onboarding/customers/@@list'
        params = {}
        self.testapp.get(url, params=params, status=302, extra_environ=self._make_environ(username=None))
        self.testapp.get(url, params=params, status=403, extra_environ=self._make_environ(username='user001'))
        result = self.testapp.get(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        assert_that(b"<h1>Customers</h1>" in result.body, is_(True))

        with ensure_free_txn():
            customers = self._root().get('customers')
            view = CustomersListView(customers, self.request)
            result = view()
            assert_that(result, has_entries({'table': instance_of(CustomersTable),
                                             'creation_url': None}))

    @with_test_app()
    def testCustomerDetailView(self):
        email = '123@gmail.com'
        with ensure_free_txn():
            customers = self._root().get('customers')
            customers.addCustomer(PersistentCustomer(email=email,
                                                     name="testname",
                                                     hubspot_contact=HubspotContact(contact_vid='vid001')))

        url = '/onboarding/customers/{}/@@details'.format(email)
        params = {}
        self.testapp.get(url, params=params, status=302, extra_environ=self._make_environ(username=None))
        self.testapp.get(url, params=params, status=403, extra_environ=self._make_environ(username='user001'))
        result = self.testapp.get(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        assert_that(b'Customer Detail' in result.body, is_(True))

        with ensure_free_txn():
            customer = customers[email]
            view = CustomerDetailView(customer, self.request)
            result = view()
            assert_that(result, has_entries({'customers_list_link': 'http://example.com/onboarding/customers/@@list',
                                             'customer': has_entries({'customer': customer,
                                                          'hubspot': has_entries({'contact_vid': 'vid001'})}),
                                             'table': instance_of(SitesTable)}))

    @with_test_app()
    def testSitesListView(self):
        url = '/onboarding/sites/@@list'
        params = {}
        self.testapp.get(url, params=params, status=302, extra_environ=self._make_environ(username=None))
        self.testapp.get(url, params=params, status=403, extra_environ=self._make_environ(username='user001'))
        result = self.testapp.get(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        assert_that(b"<h1>Sites</h1>" in result.body, is_(True))

        with ensure_free_txn():
            sites = self._root().get('sites')
            view = SitesListView(sites, self.request)
            result = view()
            assert_that(result, has_entries({'table': instance_of(SitesTable),
                                             'creation_url': None,
                                             'site_status_options': SITE_STATUS_OPTIONS,
                                             'env_shared_options': SHARED_ENV_NAMES}))

    @with_test_app()
    @mock.patch('nti.app.environments.views.admin_views.SiteDetailView._site_extra_info')
    @mock.patch('nti.app.environments.models.wref.get_customers_folder')
    def testSiteDetailView(self, mock_customers, mock_info):
        mock_info.return_value = {}
        siteId = 'Sxxx'
        with ensure_free_txn():
            mock_customers.return_value = customers = self._root().get('customers')
            customer = customers.addCustomer(PersistentCustomer(email='123@gmail.com',
                                                                name="testname",
                                                                hubspot_contact=HubspotContact(contact_vid='vid001')))

            sites = self._root().get('sites')
            site = sites.addSite(PersistentSite(license=TrialLicense(start_date=datetime.datetime(2019, 12, 12, 0, 0, 0),
                                                                     end_date=datetime.datetime(2019, 12, 13, 0, 0, 0)),
                                                environment=SharedEnvironment(name='test'),
                                                status='ACTIVE',
                                                dns_names=['x', 'y'],
                                                owner=customer), siteId=siteId)

        url = '/onboarding/sites/{}/@@details'.format(siteId)
        params = {}
        self.testapp.get(url, params=params, status=302, extra_environ=self._make_environ(username=None))
        self.testapp.get(url, params=params, status=403, extra_environ=self._make_environ(username='user001'))
        result = self.testapp.get(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        assert_that(b'Site Detail' in result.body, is_(True))
        with ensure_free_txn():
            view = SiteDetailView(site, self.request)
            result = view()
            assert_that(result, has_entries({'sites_list_link': 'http://example.com/onboarding/sites/@@list',
                                             'site': has_entries({'created': not_none(),
                                                 'owner': {'owner': customer, 'detail_url': 'http://example.com/onboarding/customers/123@gmail.com/@@details'},
                                                 'site_id': siteId,
                                                 'status': 'ACTIVE',
                                                 'dns_names': ['x', 'y'],
                                                 'license': has_entries({'type': 'trial', 'start_date': '2019-12-11 18:00:00', 'end_date': '2019-12-12 18:00:00',
                                                             'edit_link': None}),
                                                 'environment': has_entries({'type': 'shared'}),
                                                 'environment_edit_link': None,
                                                 'creator': None,
                                                 'client_name': 'x',
                                                 'site_edit_link': None,
                                                 'lastModified': not_none()
                                             })}))


class TestTrialSitesDigestEmailView(BaseAppTest):

    @with_test_app()
    @mock.patch('nti.app.environments.models.wref.get_customers_folder')
    def testTrialSitesDigestEmailView(self, mock_customers):
        inst = TrialSitesDigestEmailView(self._root(), self.request)
        assert_that(inst.get_newly_created_trial_sites(0, time.time()), has_length(0))

        with ensure_free_txn():
            root = self._root()
            mock_customers.return_value = customers = root.get('customers')
            customer = PersistentCustomer(email='123@gmail.com',
                                          name="testname",
                                          hubspot_contact=HubspotContact(contact_vid='vid001'))
            customer = customers.addCustomer(customer)

            sites = root.get('sites')
            def _d(month, day):
                return datetime.datetime(2020, month, day, 0, 0, 0)
            for site_id, created, _license in (('S001', 90, TrialLicense(start_date=_d(4, 10), end_date=_d(4, 15))),
                                               ('S002', 100, TrialLicense(start_date=_d(4, 11), end_date=_d(4, 16))),
                                               ('S003', 110, TrialLicense(start_date=_d(4, 12), end_date=_d(4, 17))),
                                               ('S004', 120, TrialLicense(start_date=_d(4, 13), end_date=_d(4, 18)))):
                site = PersistentSite(license=_license,
                                      environment=SharedEnvironment(name='test'),
                                      status='ACTIVE',
                                      dns_names=['x', 'y'],
                                      owner=customer)
                site.createdTime = created
                sites.addSite(site, site_id)

        # notBefore(inclusive), notAfter(inclusive)
        inst = TrialSitesDigestEmailView(root, self.request)
        assert_that(inst.get_newly_created_trial_sites(91, 99), has_length(0))
        assert_that(inst.get_newly_created_trial_sites(90, 100), has_length(2))

        # notBefore(exclusive), notAfter(inclusive)
        assert_that(inst.get_ending_trial_sites(_d(4, 10), _d(4, 14)), has_length(0))
        assert_that(inst.get_ending_trial_sites(_d(4, 10), _d(4, 15)), has_length(1))
        assert_that(inst.get_ending_trial_sites(_d(4, 15), _d(4, 18)), has_length(3))

        # notAfter(inclusive)
        assert_that(inst.get_past_due_trial_sites(_d(4,14)), has_length(0))
        assert_that(inst.get_past_due_trial_sites(_d(4,15)), has_length(1))
        assert_that(inst.get_past_due_trial_sites(_d(4,18)), has_length(4))
