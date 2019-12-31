import datetime

from unittest import mock
from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import has_properties
from hamcrest import instance_of
from hamcrest import is_

from nti.app.environments.views.customers import getOrCreateCustomer
from nti.app.environments.views.tests import BaseAppTest
from nti.app.environments.views.tests import with_test_app
from nti.app.environments.views.tests import ensure_free_txn
from nti.app.environments.models.customers import PersistentCustomer
from nti.app.environments.models.sites import TrialLicense, EnterpriseLicense, PersistentSite, SharedEnvironment
from nti.app.environments.models.interfaces import IEnterpriseLicense,\
    ITrialLicense, ISharedEnvironment, IDedicatedEnvironment
from hamcrest.library.collection.isdict_containingentries import has_entries


class TestSiteCreationView(BaseAppTest):

    def _params(self, env_type='shared', license_type="trial", site_id=None):
        env = {'name': 'assoc'} if env_type == 'shared' else {'pod_id': 'xxx', 'host': 'okc.com'}
        return {
            'site_id': site_id,
            "owner": "test@gmail.com",
            "environment": {
                "type": env_type,
                **env,
            },
            "license": {
                "type": license_type,
                'start_date': '2019-11-27T00:00:00',
                'end_date': '2019-11-28T00:00:00'
            },
            "dns_names": ["t1.nextthought.com", "t2.nextthought.com"],
            "status": "PENDING",
            "created": "2019-11-26T00:00:00"
        }

    @with_test_app()
    @mock.patch('nti.app.environments.models.wref.get_customers_folder')
    def test_site(self, mock_customers):
        url = '/sites'
        params = self._params()
        self.testapp.post_json(url, params=params, status=401, extra_environ=self._make_environ(username=None))
        self.testapp.post_json(url, params=params, status=403, extra_environ=self._make_environ(username='user001'))
        result = self.testapp.post_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        result = result.json_body
        assert_that(result, {})

        with ensure_free_txn():
            sites = self._root().get('sites')
            assert_that(sites, has_length(0))
            getOrCreateCustomer(self._root().get('customers'), 'test@gmail.com')
            mock_customers.return_value = self._root().get('customers')

        result = self.testapp.post_json(url, params=params, status=201, extra_environ=self._make_environ(username='admin001'))
        result = result.json_body
        assert_that(result, is_({}))
        assert_that(sites, has_length(1))
        site = [x for x in sites.values()][0]
        assert_that(site, has_properties({'owner': has_properties({'email': 'test@gmail.com'}),
                                                           'environment': has_properties({'name': 'assoc'}),
                                                           'license': instance_of(TrialLicense),
                                                           'status': 'PENDING',
                                                           'dns_names': ['t1.nextthought.com', 't2.nextthought.com']}))
        assert_that(site.created.strftime('%y-%m-%d %H:%M:%S'), '2019-11-26 06:00:00')

        # edit
        site_url = '/sites/%s' % (site.__name__,)
        params = {
            'status': 'ACTIVE',
            'dns_names': ['s@next.com']
        }
        result = self.testapp.put_json(site_url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        assert_that(site, has_properties({'status': 'ACTIVE',
                                          'dns_names': ['s@next.com']}))

        # delete
        self.testapp.delete(site_url, status=204, extra_environ=self._make_environ(username='admin001'))
        with ensure_free_txn():
            sites = self._root().get('sites')
            assert_that(sites, has_length(0))

        params = self._params(env_type='dedicated', license_type="enterprise", site_id='S1id')
        self.testapp.post_json(url, params=params, status=201, extra_environ=self._make_environ(username='admin001'))
        with ensure_free_txn():
            sites = self._root().get('sites')
            assert_that(sites, has_length(1))
            site = [x for x in sites.values()][0]
            assert_that(site, has_properties({'owner': has_properties({'email': 'test@gmail.com'}),
                                                               'id': 'S1id',
                                                               'environment': has_properties({'pod_id': 'xxx', 'host': 'okc.com'}),
                                                               'license': instance_of(EnterpriseLicense),
                                                               'status': 'PENDING',
                                                               'dns_names': ['t1.nextthought.com', 't2.nextthought.com']}))

class TestSitePutView(BaseAppTest):

    @with_test_app()
    def testSiteLicensePutView(self):
        siteId = 'Sxxx'
        with ensure_free_txn():
            customers = self._root().get('customers')
            customer = customers.addCustomer(PersistentCustomer(email='123@gmail.com',
                                                                name="testname"))

            sites = self._root().get('sites')
            site = sites.addSite(PersistentSite(license=TrialLicense(start_date=datetime.datetime(2019, 12, 12, 0, 0, 0),
                                                                     end_date=datetime.datetime(2019, 12, 13, 0, 0, 0)),
                                                environment=SharedEnvironment(name='test'),
                                                created=datetime.datetime(2019, 12, 11, 0, 0, 0),
                                                status='ACTIVE',
                                                dns_names=['x', 'y'],
                                                owner=customer), siteId=siteId)
            assert_that(ITrialLicense.providedBy(site.license), is_(True))

        url = '/sites/{}/@@license'.format(siteId)
        params = {'type': 'trial',
                  'start_date': '2019-12-30',
                  'end_date': '2029-12-30'}
        self.testapp.put_json(url, params=params, status=401, extra_environ=self._make_environ(username=None))
        self.testapp.put_json(url, params=params, status=403, extra_environ=self._make_environ(username='user001'))
        self.testapp.put_json(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        with ensure_free_txn():
            assert_that(ITrialLicense.providedBy(site.license), is_(True))
            assert_that(site.license.start_date.strftime('%Y-%m-%d%H:%M:%S'), '2019-12-30 00:00:00')
            assert_that(site.license.end_date.strftime('%Y-%m-%d%H:%M:%S'), '2029-12-30 00:00:00')

        params = {'type': 'enterprise',
                  'start_date': '2019-12-30',
                  'end_date': '2029-12-30'}
        self.testapp.put_json(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        with ensure_free_txn():
            assert_that(IEnterpriseLicense.providedBy(site.license), is_(True))
            assert_that(site.license.start_date.strftime('%Y-%m-%d%H:%M:%S'), '2019-12-30 00:00:00')
            assert_that(site.license.end_date.strftime('%Y-%m-%d%H:%M:%S'), '2029-12-30 00:00:00')

        params = {'type': 'enterprise',
                  'start_date': '2019-11-30',
                  'end_date': '2029-11-30'}
        self.testapp.put_json(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        with ensure_free_txn():
            assert_that(IEnterpriseLicense.providedBy(site.license), is_(True))
            assert_that(site.license.start_date.strftime('%Y-%m-%d%H:%M:%S'), '2019-11-30 00:00:00')
            assert_that(site.license.end_date.strftime('%Y-%m-%d%H:%M:%S'), '2029-11-30 00:00:00')

        params = {'type': 'enterprise2',
                  'start_date': '2019-12-30',
                  'end_date': '2029-12-30'}
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({"message": "Unknown license type."}))

        params = {'start_date': '2019-23'}
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({"message": "Unknown license type."}))

        params = {'type': 'enterprise',
                  'start_date': '2019-23',
                  'end_date': '2016-07'}
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({"message": "Invalid date format for start_date."}))

        params = {'type': 'enterprise',
                  'end_date': '2016-07'}
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({"message": "Missing required field: start_date."}))

        params = {'type': 'enterprise',
                  'start_date': '2016-07'}
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({"message": "Missing required field: end_date."}))

    @with_test_app()
    def testSiteEnvironmentPutView(self):
        siteId = 'Sxxx'
        with ensure_free_txn():
            customers = self._root().get('customers')
            customer = customers.addCustomer(PersistentCustomer(email='123@gmail.com',
                                                                name="testname"))

            sites = self._root().get('sites')
            site = sites.addSite(PersistentSite(license=TrialLicense(start_date=datetime.datetime(2019, 12, 12, 0, 0, 0),
                                                                     end_date=datetime.datetime(2019, 12, 13, 0, 0, 0)),
                                                environment=SharedEnvironment(name='test'),
                                                created=datetime.datetime(2019, 12, 11, 0, 0, 0),
                                                status='ACTIVE',
                                                dns_names=['x', 'y'],
                                                owner=customer), siteId=siteId)
            assert_that(ITrialLicense.providedBy(site.license), is_(True))

        url = '/sites/{}/@@environment'.format(siteId)
        params = {'type': 'shared',
                  'name': 'prod'}
        self.testapp.put_json(url, params=params, status=401, extra_environ=self._make_environ(username=None))
        self.testapp.put_json(url, params=params, status=403, extra_environ=self._make_environ(username='user001'))
        self.testapp.put_json(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        with ensure_free_txn():
            assert_that(ISharedEnvironment.providedBy(site.environment), is_(True))
            assert_that(site.environment.name, is_('prod'))

        params = {'type': 'dedicated',
                  'pod_id': 'okc',
                  'host': 'okc2'}
        self.testapp.put_json(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        with ensure_free_txn():
            assert_that(IDedicatedEnvironment.providedBy(site.environment), is_(True))
            assert_that(site.environment, has_properties({'pod_id': 'okc',
                                                          'host': 'okc2'}))

        params = {'type': 'dedicated',
                  'pod_id': 'pod',
                  'host': 'pod2'}
        self.testapp.put_json(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        with ensure_free_txn():
            assert_that(IDedicatedEnvironment.providedBy(site.environment), is_(True))
            assert_that(site.environment, has_properties({'pod_id': 'pod',
                                                          'host': 'pod2'}))

        params = {'type': 'dedicated2',
                  'pod_id': 'pod',
                  'host': 'pod2'}
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'message': 'Unknown environment type.'}))

        params = {'pod_id': 'pod',
                  'host': 'pod2'}
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'message': 'Unknown environment type.'}))

        params = {'type': 'dedicated',
                  'host': 'pod2'}
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'message': 'Missing required field: pod_id.'}))

        params = {'type': 'dedicated',
                  'pod_id': 'pod2'}
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'message': 'Missing required field: host.'}))

        params = {'type': 'shared',
                  'name': None}
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'message': 'Missing required field: name.'}))

        params = {'type': 'shared',
                  'name': 3}
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'message': 'Invalid name.'}))