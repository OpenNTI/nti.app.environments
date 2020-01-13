import datetime
import tempfile
import shutil
import os

from unittest import mock
from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import has_properties
from hamcrest import instance_of
from hamcrest import contains_string
from hamcrest import starts_with
from hamcrest import is_

from pyramid_mailer.interfaces import IMailer
from pyramid_mailer import Mailer

from zope import component

from nti.externalization import to_external_object

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

    def _params(self,
                env_type='application/vnd.nextthought.app.environments.sharedenvironment',
                license_type="application/vnd.nextthought.app.environments.triallicense",
                site_id=None):
        env = {'name': 'assoc'} if env_type == 'application/vnd.nextthought.app.environments.sharedenvironment' else {'pod_id': 'xxx', 'host': 'okc.com'}
        return {
            'id': site_id,
            "owner": "test@gmail.com",
            "environment": {
                "MimeType": env_type,
                **env,
            },
            "license": {
                "MimeType": license_type,
                'start_date': '2019-11-27T00:00:00',
                'end_date': '2019-11-28T00:00:00'
            },
            "dns_names": ["t1.nextthought.com", "t2.nextthought.com"],
            "status": "PENDING",
            "created": "2019-11-26T00:00:00",
            "MimeType": "application/vnd.nextthought.app.environments.site",
        }

    @with_test_app()
    @mock.patch('nti.app.environments.models.wref.get_customers_folder')
    def test_site(self, mock_customers):
        url = '/onboarding/sites'
        params = self._params()
        self.testapp.post_json(url, params=params, status=302, extra_environ=self._make_environ(username=None))
        self.testapp.post_json(url, params=params, status=403, extra_environ=self._make_environ(username='user001'))
        result = self.testapp.post_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        result = result.json_body
        assert_that(result, has_entries({'message': 'No customer found with email: test@gmail.com.'}))

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
        site_url = '/onboarding/sites/%s' % (site.__name__,)
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

        params = self._params(env_type='application/vnd.nextthought.app.environments.dedicatedenvironment',
                              license_type="application/vnd.nextthought.app.environments.enterpriselicense",
                              site_id='S1id')
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
            external = to_external_object(site)
            assert_that(external, has_entries({'id': 'S1id'}))


class TestSitePutView(BaseAppTest):

    @with_test_app()
    @mock.patch('nti.app.environments.models.utils.get_onboarding_root')
    def testSiteLicensePutView(self, mock_get_onboarding_root):
        mock_get_onboarding_root.return_value = self._root()
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

        url = '/onboarding/sites/{}/@@license'.format(siteId)
        params = {'MimeType': 'application/vnd.nextthought.app.environments.triallicense',
                  'start_date': '2019-12-30',
                  'end_date': '2029-12-30'}
        self.testapp.put_json(url, params=params, status=302, extra_environ=self._make_environ(username=None))
        self.testapp.put_json(url, params=params, status=403, extra_environ=self._make_environ(username='user001'))
        self.testapp.put_json(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        with ensure_free_txn():
            assert_that(ITrialLicense.providedBy(site.license), is_(True))
            assert_that(site.license.start_date.strftime('%Y-%m-%d%H:%M:%S'), '2019-12-30 00:00:00')
            assert_that(site.license.end_date.strftime('%Y-%m-%d%H:%M:%S'), '2029-12-30 00:00:00')

        params = {'MimeType': 'application/vnd.nextthought.app.environments.enterpriselicense',
                  'start_date': '2019-12-30',
                  'end_date': '2029-12-30'}
        self.testapp.put_json(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        with ensure_free_txn():
            assert_that(IEnterpriseLicense.providedBy(site.license), is_(True))
            assert_that(site.license.start_date.strftime('%Y-%m-%d%H:%M:%S'), '2019-12-30 00:00:00')
            assert_that(site.license.end_date.strftime('%Y-%m-%d%H:%M:%S'), '2029-12-30 00:00:00')

        params = {'MimeType': 'application/vnd.nextthought.app.environments.enterpriselicense',
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
        assert_that(result.json_body, has_entries({"message": contains_string('No factory for object')}))

        params = {'start_date': '2019-23'}
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({"message": 'Invalid date format for start_date.'}))

        params = {'MimeType': 'application/vnd.nextthought.app.environments.enterpriselicense',
                  'start_date': '2019-23',
                  'end_date': '2016-07'}
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({"message": "Invalid date format for start_date."}))

        params = {'MimeType': 'application/vnd.nextthought.app.environments.enterpriselicense',
                  'end_date': '2016-07'}
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({"message": "Missing required field: start_date."}))

        params = {'MimeType': 'application/vnd.nextthought.app.environments.enterpriselicense',
                  'start_date': '2016-07'}
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({"message": "Missing required field: end_date."}))

    @with_test_app()
    @mock.patch('nti.app.environments.models.utils.get_onboarding_root')
    def testSiteEnvironmentPutView(self, mock_get_onboarding_root):
        siteId = 'Sxxx'
        with ensure_free_txn():
            mock_get_onboarding_root.return_value = self._root()
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

        url = '/onboarding/sites/{}/@@environment'.format(siteId)
        params = {'MimeType': 'application/vnd.nextthought.app.environments.sharedenvironment',
                  'name': 'prod'}
        self.testapp.put_json(url, params=params, status=302, extra_environ=self._make_environ(username=None))
        self.testapp.put_json(url, params=params, status=403, extra_environ=self._make_environ(username='user001'))
        self.testapp.put_json(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        with ensure_free_txn():
            assert_that(ISharedEnvironment.providedBy(site.environment), is_(True))
            assert_that(site.environment.name, is_('prod'))

        params = {'MimeType': 'application/vnd.nextthought.app.environments.dedicatedenvironment',
                  'pod_id': 'okc',
                  'host': 'okc2'}
        self.testapp.put_json(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        with ensure_free_txn():
            assert_that(IDedicatedEnvironment.providedBy(site.environment), is_(True))
            assert_that(site.environment, has_properties({'pod_id': 'okc',
                                                          'host': 'okc2'}))

        params = {'MimeType': 'application/vnd.nextthought.app.environments.dedicatedenvironment',
                  'pod_id': 'pod',
                  'host': 'pod2'}
        self.testapp.put_json(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        with ensure_free_txn():
            assert_that(IDedicatedEnvironment.providedBy(site.environment), is_(True))
            assert_that(site.environment, has_properties({'pod_id': 'pod',
                                                          'host': 'pod2'}))

        params = {'MimeType': 'dedicated2',
                  'pod_id': 'pod',
                  'host': 'pod2'}
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'message': contains_string('No factory for object')}))

        params = {'pod_id': 'pod',
                  'host': 'pod2'}
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'message': contains_string('No factory for object')}))

        params = {'MimeType': 'application/vnd.nextthought.app.environments.dedicatedenvironment',
                  'host': 'pod2'}
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'message': 'Missing field: pod_id.'}))

        params = {'MimeType': 'application/vnd.nextthought.app.environments.dedicatedenvironment',
                  'pod_id': 'pod2'}
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'message': 'Missing field: host.'}))

        params = {'MimeType': 'application/vnd.nextthought.app.environments.sharedenvironment',
                  'name': None}
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'message': 'Missing field: name.'}))

        params = {'MimeType': 'application/vnd.nextthought.app.environments.sharedenvironment',
                  'name': 3}
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'message': 'Invalid name.'}))


class TestRequestTrialSiteView(BaseAppTest):

    @with_test_app()
    @mock.patch('nti.app.environments.views.sites.get_hubspot_client')
    def testRequestTrialSiteView(self, mock_client):
        _client = mock.MagicMock()
        _client.fetch_contact_by_email = lambda email: None
        mock_client.return_value = _client
        url = '/onboarding/sites/@@request_trial_site'
        with ensure_free_txn():
            dirpath = tempfile.mkdtemp()
            os.mkdir(os.path.join(dirpath, 'new'))
            os.mkdir(os.path.join(dirpath, 'cur'))
            os.mkdir(os.path.join(dirpath, 'tmp'))
            component.getGlobalSiteManager().registerUtility(Mailer(default_sender='no-reply.nextthought.com',
                                                                    queue_path=dirpath), IMailer)
            sites = self._root().get('sites')
            assert_that(sites, has_length(0))

            customers = self._root().get('customers')
            customers.addCustomer(PersistentCustomer(email='123@gmail.com', name="testname"))
            assert_that(customers, has_length(1))

        params = {}
        self.testapp.post_json(url, params=params, status=302, extra_environ=self._make_environ(username=None))
        self.testapp.post_json(url, params=params, status=403, extra_environ=self._make_environ(username='user001'))
        result = self.testapp.post_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001')).json_body
        assert_that(result, has_entries({'message': 'Missing email.'}))

        params = {'owner': 'xyz'}
        result = self.testapp.post_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001')).json_body
        assert_that(result, has_entries({'message': 'Invalid email.'}))

        params = {'owner': '123@gmail.com'}
        result = self.testapp.post_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001')).json_body
        assert_that(result, has_entries({'message': 'Please provide at least one site url.'}))

        params = {'owner': '123@gmail.com', 'dns_names': []}
        result = self.testapp.post_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001')).json_body
        assert_that(result['message'], starts_with('Please provide at least one site url.'))

        params = {'owner': '123@gmail.com', 'dns_names': [None]}
        result = self.testapp.post_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001')).json_body
        assert_that(result['message'], starts_with('Missing field: dns_names.'))

        params = {'owner': '123@gmail.com', 'dns_names': ['xxx']}
        result = self.testapp.post_json(url, params=params, status=201, extra_environ=self._make_environ(username='admin001')).json_body
        assert_that(result['redirect_url'], starts_with('http://localhost/onboarding/sites/'))

        params = {'owner': '1234@gmail.com', 'dns_names': ['xxx', 'yyy']}
        result = self.testapp.post_json(url, params=params, status=201, extra_environ=self._make_environ(username='admin001')).json_body
        assert_that(result['redirect_url'], starts_with('http://localhost/onboarding/sites/'))

        _client.fetch_contact_by_email = lambda email: {'canonical-vid': '133','email': email, 'name': "OKC Test"}
        params = {'owner': '12345@gmail.com', 'dns_names': ['xxx', 'yyy']}
        result = self.testapp.post_json(url, params=params, status=201, extra_environ=self._make_environ(username='admin001')).json_body
        assert_that(result['redirect_url'], starts_with('http://localhost/onboarding/sites/'))

        with ensure_free_txn():
            component.getGlobalSiteManager().unregisterUtility(Mailer(default_sender='no-reply.nextthought.com'), IMailer)
            shutil.rmtree(dirpath)
            assert_that(sites, has_length(3))
            assert_that(customers, has_length(3))
            assert_that(customers['12345@gmail.com'].hubspot_contact.contact_vid, '133')
