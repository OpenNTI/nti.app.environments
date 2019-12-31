import datetime

from unittest import mock
from hamcrest import is_
from hamcrest import assert_that
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

from nti.app.environments.views.tests import BaseAppTest
from nti.app.environments.views.tests import with_test_app
from nti.app.environments.views.tests import ensure_free_txn
from nti.app.environments.views._table_utils import SitesTable
from nti.app.environments.views._table_utils import CustomersTable


class TestAdminViews(BaseAppTest):

    @with_test_app()
    def testCustomersListView(self):
        url = '/admin/customers/@@list'
        params = {}
        self.testapp.get(url, params=params, status=401, extra_environ=self._make_environ(username=None))
        self.testapp.get(url, params=params, status=403, extra_environ=self._make_environ(username='user001'))
        result = self.testapp.get(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        assert_that(b"<h1>Customers</h1>" in result.body, is_(True))

        with ensure_free_txn():
            customers = self._root().get('customers')
            view = CustomersListView(customers, self.request)
            result = view()
            assert_that(result, has_entries({'table': instance_of(CustomersTable),
                                             'creation_url': 'http://example.com/customers/@@hubspot'}))

    @with_test_app()
    def testCustomerDetailView(self):
        email = '123@gmail.com'
        with ensure_free_txn():
            customers = self._root().get('customers')
            customers.addCustomer(PersistentCustomer(email=email,
                                                     name="testname",
                                                     hubspot_contact=HubspotContact(contact_vid='vid001')))

        url = '/admin/customers/{}/@@details'.format(email)
        params = {}
        self.testapp.get(url, params=params, status=401, extra_environ=self._make_environ(username=None))
        self.testapp.get(url, params=params, status=403, extra_environ=self._make_environ(username='user001'))
        result = self.testapp.get(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        assert_that(b'Customer Detail' in result.body, is_(True))

        with ensure_free_txn():
            customer = customers[email]
            view = CustomerDetailView(customer, self.request)
            result = view()
            assert_that(result, has_entries({'customers_list_link': 'http://example.com/admin/customers/@@list',
                                             'customer': has_entries({'email': email,
                                                          'name': 'testname',
                                                          'hubspot': has_entries({'contact_vid': 'vid001'})}),
                                             'table': instance_of(SitesTable)}))

    @with_test_app()
    def testSitesListView(self):
        url = '/admin/sites/@@list'
        params = {}
        self.testapp.get(url, params=params, status=401, extra_environ=self._make_environ(username=None))
        self.testapp.get(url, params=params, status=403, extra_environ=self._make_environ(username='user001'))
        result = self.testapp.get(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        assert_that(b"<h1>Sites</h1>" in result.body, is_(True))

        with ensure_free_txn():
            sites = self._root().get('sites')
            view = SitesListView(sites, self.request)
            result = view()
            assert_that(result, has_entries({'table': instance_of(SitesTable),
                                             'creation_url': 'http://example.com/sites/',
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
                                                created=datetime.datetime(2019, 12, 11, 0, 0, 0),
                                                status='ACTIVE',
                                                dns_names=['x', 'y'],
                                                owner=customer), siteId=siteId)

        url = '/admin/sites/{}/@@details'.format(siteId)
        params = {}
        self.testapp.get(url, params=params, status=401, extra_environ=self._make_environ(username=None))
        self.testapp.get(url, params=params, status=403, extra_environ=self._make_environ(username='user001'))
        result = self.testapp.get(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        assert_that(b'Site Detail' in result.body, is_(True))
        with ensure_free_txn():
            view = SiteDetailView(site, self.request)
            result = view()
            assert_that(result, has_entries({'sites_list_link': 'http://example.com/admin/sites/@@list',
                                             'site': {'created': '2019-12-10T18:00:00',
                                                 'owner': {'owner': customer, 'detail_url': 'http://example.com/admin/customers/123@gmail.com/@@details'},
                                                 'site_id': siteId,
                                                 'status': 'ACTIVE',
                                                 'dns_names': ['x', 'y'],
                                                 'license': {'type': 'trial', 'start_date': '2019-12-11T18:00:00', 'end_date': '2019-12-12T18:00:00',
                                                             'edit_link': 'http://example.com/sites/Sxxx/@@license'},
                                                 'environment': {'type': 'shared', 'name': 'test',
                                                                 'edit_link': 'http://example.com/sites/Sxxx/@@environment'}
                                             }}))
