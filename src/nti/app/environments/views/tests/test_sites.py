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
            'dns_names': ['s@Next.com']
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
        result = self.testapp.post_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body['message'], is_("No host found: okc.com"))
        with ensure_free_txn():
            hosts = self._root().get('hosts')
            host = hosts.addHost(PersistentHost(host_name='okc.com', capacity=5))
            assert_that(host.current_load, is_(0))

        params['environment']['host'] = host.id
        self.testapp.post_json(url, params=params, status=201, extra_environ=self._make_environ(username='admin001'))
        with ensure_free_txn():
            assert_that(host.current_load, is_(1))
            sites = self._root().get('sites')
            assert_that(sites, has_length(1))
            site = [x for x in sites.values()][0]
            assert_that(site, has_properties({'owner': has_properties({'email': 'test@gmail.com'}),
                                                               'id': 'S1id',
                                                               'environment': has_properties({'pod_id': 'xxx',
                                                                                              'host': has_properties({'host_name': 'okc.com'})}),
                                                               'license': instance_of(EnterpriseLicense),
                                                               'status': 'PENDING',
                                                               'dns_names': ['t1.nextthought.com', 't2.nextthought.com']}))
            external = to_external_object(site)
            assert_that(external, has_entries({'id': 'S1id'}))


class TestSitePutView(BaseAppTest):

    @with_test_app()
    @mock.patch('nti.app.environments.models.wref.get_customers_folder')
    def testSitePutView(self, mock_customers):
        with ensure_free_txn():
            mock_customers.return_value = customers = self._root().get('customers')
            customer = customers.addCustomer(PersistentCustomer(email='123@gmail.com', name="testname"))
            sites = self._root().get('sites')
            for site_id in ('Sxxx1', 'Sxxx2'):
                sites.addSite(PersistentSite(license=TrialLicense(start_date=datetime.datetime(2019, 12, 12, 0, 0, 0),
                                                                  end_date=datetime.datetime(2019, 12, 13, 0, 0, 0)),
                                             status='PENDING',
                                             dns_names=['x', 'y'],
                                             owner=customer), siteId=site_id)
            assert_that(sites, has_length(2))

        url = '/onboarding/sites/Sxxx1'

        # parent_site
        params = { 'parent_site': 'Sxxx1' }
        self.testapp.put_json(url, params=params, status=302, extra_environ=self._make_environ(username=None))
        self.testapp.put_json(url, params=params, status=403, extra_environ=self._make_environ(username='user001'))
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body['message'], is_('parent site can not be self.'))

        params = { 'parent_site': 'xxx'}
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body['message'], is_('No parent site found: xxx'))

        params = { 'parent_site': 123}
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body['message'], is_('Invalid parent site type.'))

        params = { 'parent_site': 'Sxxx2' }
        self.testapp.put_json(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        assert_that(sites['Sxxx1'].parent_site, is_(sites['Sxxx2']))

        params = { 'parent_site': None }
        self.testapp.put_json(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        assert_that(sites['Sxxx1'].parent_site, is_(None))
        with ensure_free_txn():
            with mock.patch('nti.app.environments.models.utils.get_current_request') as mock_request:
                mock_request.return_value = self.request
                result = update_from_external_object(sites['Sxxx1'], {'parent_site': 'Sxxx2'})
                assert_that(result.parent_site, sites['Sxxx2'])

                result = update_from_external_object(sites['Sxxx1'], {'parent_site': sites['Sxxx2']})
                assert_that(result.parent_site, sites['Sxxx2'])

                assert_that(calling(update_from_external_object).with_args(sites['Sxxx1'], {'parent_site': 'Sxxx1'}),
                            raises(Invalid, pattern="parent site can not be self."))

                temp = PersistentSite(id='Sxxx2')
                result = update_from_external_object(sites['Sxxx1'], {'parent_site': temp})
                assert_that(result.parent_site, sites['Sxxx2'])

        # dns_names
        params = { 'dns_names': None }
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({"message": "Missing field: dns_names."}))

        params = { 'dns_names': [] }
        self.testapp.put_json(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        assert_that(sites['Sxxx1'].dns_names, is_([]))

        params = { 'dns_names': ['xxx'] }
        self.testapp.put_json(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        assert_that(sites['Sxxx1'].dns_names, is_(['xxx']))

        params = { 'dns_names': ['YYY', 'XXX'] }
        self.testapp.put_json(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        assert_that(sites['Sxxx1'].dns_names, is_(['yyy', 'xxx']))

        params = { 'dns_names': ['xxx', 'xxx'] }
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'message': 'Existing duplicated xxx for dns_names.'}))

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

            hosts = self._root().get('hosts')
            host_okc2 = hosts.addHost(PersistentHost(host_name='okc2', capacity=5))
            host_pod2 = hosts.addHost(PersistentHost(host_name='pod2', capacity=5))

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
                  'host': 'okc3'}
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body['message'], is_("No host found: okc3"))

        params = {'MimeType': 'dedicated2',
                  'pod_id': 'pod',
                  'host': host_pod2.id}
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'message': contains_string('No factory for object')}))

        params = {'pod_id': 'pod',
                  'host': host_pod2.id}
        result = self.testapp.put_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'message': contains_string('No factory for object')}))

        params = {'MimeType': 'application/vnd.nextthought.app.environments.dedicatedenvironment',
                  'host': host_pod2.id}
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
        assert_that(result['message'], starts_with('Missing field: .'))

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


class TestSitesUploadCSVView(BaseAppTest):

    def setUp(self):
        super(TestSitesUploadCSVView, self).setUp()
        self.url = '/onboarding/sites/@@upload_sites'
        self.site_info = ('sites', _absolute_path('site_info.csv'))

    def _f(self, file_info, content=None):
        return file_info if content is None else (file_info[0], file_info[1], str(content))

    def _upload_file(self, file, content=None, status=200):
        return self.testapp.post(self.url,
                                 upload_files=(self._f(file, content), ),
                                 status=status,
                                 extra_environ=self._make_environ(username='admin001'))

    @with_test_app()
    def test_get_or_update_dns_names(self):
        sites = self._root().get('sites')
        assert_that(sites, has_length(0))
        view = SitesUploadCSVView(sites, self.request)
        assert_that(view._get_or_update_dns_names(), has_length(0))
        assert_that(view._existing_site_dns_names, has_length(0))

        kwargs = {'license': TrialLicense(start_date=datetime.datetime(2019, 12, 12, 0, 0, 0), end_date=datetime.datetime(2019, 12, 13, 0, 0, 0)),
                  'environment': SharedEnvironment(name='test'),
                  'status': 'ACTIVE',}
        site = sites.addSite(PersistentSite(dns_names=['abc.com', 'ddd.com'], **kwargs), siteId='Sxx1')
        assert_that(view._get_or_update_dns_names(site=site), has_length(2))
        assert_that(view._existing_site_dns_names, has_length(2))

        site = sites.addSite(PersistentSite(dns_names=['xyz.com', 'opq.com'], **kwargs), siteId='Sxx2')
        assert_that(view._get_or_update_dns_names(site), has_length(4))

        site = sites.addSite(PersistentSite(dns_names=['xyz.com'], **kwargs), siteId='Sxx3')
        assert_that(calling(view._get_or_update_dns_names).with_args(site), raises(hexc.HTTPConflict, pattern="Existing identical dns_name in different sites: xyz.com."))
        assert_that(view._existing_site_dns_names, has_length(4))

        del view._existing_site_dns_names
        assert_that(calling(view._get_or_update_dns_names).with_args(), raises(hexc.HTTPConflict, pattern="Existing identical dns_name in different sites: xyz.com."))

        del sites['Sxx3']
        assert_that(view._get_or_update_dns_names(), has_length(4))
        assert_that(view._existing_site_dns_names, has_length(4))

        view = SitesUploadCSVView(sites, self.request)
        assert_that(view._get_or_update_dns_names(sites['Sxx2']), has_length(4))
        assert_that(calling(view._get_or_update_dns_names).with_args(sites['Sxx2']), raises(hexc.HTTPConflict))

    @with_test_app()
    def test_process_dns(self):
        sites = self._root().get('sites')
        assert_that(sites, has_length(0))
        view = SitesUploadCSVView(sites, self.request)
        assert_that(view._process_dns({'nti_site': 'ABC.com', 'nti_URL': 'XYZ.com'}), is_(['abc.com', 'xyz.com']))
        assert_that(view._process_dns({'nti_site': 'abc.com', 'nti_URL': ''}), is_(['abc.com']))
        assert_that(view._process_dns({'nti_site': '', 'nti_URL': 'xyz.com'}), is_(['xyz.com']))
        assert_that(view._process_dns({'nti_site': '', 'nti_URL': ''}), is_([]))
        assert_that(view._existing_site_dns_names, has_length(0))

        kwargs = {'license': TrialLicense(start_date=datetime.datetime(2019, 12, 12, 0, 0, 0), end_date=datetime.datetime(2019, 12, 13, 0, 0, 0)),
                  'environment': SharedEnvironment(name='test'),
                  'status': 'ACTIVE',}
        sites.addSite(PersistentSite(dns_names=['abc.com', 'ddd.com'], **kwargs), siteId='Sxx1')
        del view._existing_site_dns_names
        assert_that(calling(view._process_dns).with_args({'nti_site':'abc.com','nti_URL':''}), raises(hexc.HTTPConflict))

    @with_test_app()
    def test_get_or_update_parent_sites_ids(self):
        # Save <dns_name, site_id> mapping for sites who are not child sites.
        sites = self._root().get('sites')
        assert_that(sites, has_length(0))
        view = SitesUploadCSVView(sites, self.request)
        assert_that(view._get_or_update_parent_sites_ids(), has_length(0))
        assert_that(view._parent_sites_ids, has_length(0))

        kwargs = {'license': TrialLicense(start_date=datetime.datetime(2019, 12, 12, 0, 0, 0), end_date=datetime.datetime(2019, 12, 13, 0, 0, 0)),
                  'environment': SharedEnvironment(name='test'),
                  'status': 'ACTIVE',}
        site = sites.addSite(PersistentSite(dns_names=['abc.com', 'xyz.com'], **kwargs), siteId='Sxx1')
        assert_that(view._get_or_update_parent_sites_ids(site), has_length(2))

        site = sites.addSite(PersistentSite(dns_names=['opq.com'], **kwargs), siteId='Sxx2')
        assert_that(view._get_or_update_parent_sites_ids(site), has_length(3))

        site = sites.addSite(PersistentSite(dns_names=['opq.com'], **kwargs), siteId='Sxx3')
        assert_that(calling(view._get_or_update_parent_sites_ids).with_args(site=site), raises(hexc.HTTPConflict))

        # child site shouldn't be added.
        site = sites.addSite(PersistentSite(dns_names=['rst.com'], parent_site=sites['Sxx2'], **kwargs), siteId='Sxx4')
        assert_that(view._get_or_update_parent_sites_ids(site), has_length(3))

        # re-calculate
        del sites['Sxx3']
        del view._parent_sites_ids
        assert_that(view._get_or_update_parent_sites_ids(), has_length(3))
        assert_that(view._parent_sites_ids, has_length(3))

        view = SitesUploadCSVView(sites, self.request)
        assert_that(view._get_or_update_parent_sites_ids(site=sites['Sxx2']), has_length(3))
        assert_that(view._parent_sites_ids, has_length(3))

        assert_that(calling(view._get_or_update_parent_sites_ids).with_args(site=sites['Sxx2']), raises(hexc.HTTPConflict))

    @with_test_app()
    def test_process_parent_site(self):
        sites = self._root().get('sites')
        assert_that(sites, has_length(0))
        view = SitesUploadCSVView(sites, self.request)
        assert_that(calling(view._process_parent_site).with_args('abc.com'), raises(hexc.HTTPUnprocessableEntity))

        kwargs = {'license': TrialLicense(start_date=datetime.datetime(2019, 12, 12), end_date=datetime.datetime(2019, 12, 13)),
                  'environment': SharedEnvironment(name='test')}
        site = sites.addSite(PersistentSite(dns_names=['abc.com'], **kwargs), siteId='Sxx2')
        view = SitesUploadCSVView(sites, self.request)
        assert_that(view._process_parent_site('abc.com'), is_(site))

    @with_test_app()
    @mock.patch('nti.app.environments.views.sites.get_hubspot_client')
    @mock.patch('nti.app.environments.models.utils.get_current_request')
    def testSitesUploadCSVView(self, mock_request, mock_client):
        mock_request.return_value = self.request

        _client = mock.MagicMock()
        _client.fetch_contact_by_email = lambda email: None
        mock_client.return_value = _client

        sites = self._root().get('sites')
        assert_that(sites, has_length(0))
        customers = self._root().get('customers')
        assert_that(customers, has_length(0))

        view = SitesUploadCSVView(sites, self.request)
        # license
        result = view._process_license({'License Type': 'trial', 'LicenseStartDate': '', 'LicenseEndDate': ''})
        assert_that(ITrialLicense.providedBy(result), is_(True))
        assert_that(result, has_properties({'start_date': datetime.datetime(2011, 4, 1, 5, 0, 0),
                                            'end_date': datetime.datetime(2029, 12, 31, 6, 0, 0)}))

        result = view._process_license({'License Type': 'enterprise', 'LicenseStartDate': '', 'LicenseEndDate': ''})
        assert_that(IEnterpriseLicense.providedBy(result), is_(True))
        assert_that(result, has_properties({'start_date': datetime.datetime(2011, 4, 1, 5, 0, 0),
                                            'end_date': datetime.datetime(2029, 12, 31, 6, 0, 0)}))

        result = view._process_license({'License Type': 'internal', 'LicenseStartDate': '', 'LicenseEndDate': ''})
        assert_that(IEnterpriseLicense.providedBy(result), is_(True))
        assert_that(result, has_properties({'start_date': datetime.datetime(2011, 4, 1, 5, 0, 0),
                                            'end_date': datetime.datetime(2029, 12, 31, 6, 0, 0)}))

        assert_that(calling(view._process_license).with_args({'License Type': ''}), raises(ValueError, pattern="Unknown license type: ."))
        assert_that(calling(view._process_license).with_args({'License Type': 'xyz'}), raises(ValueError, pattern="Unknown license type: xyz."))

        result = view._process_license({'License Type': 'trial', 'LicenseStartDate': '2020-01-14', 'LicenseEndDate': '2020-01-15'})
        assert_that(ITrialLicense.providedBy(result), is_(True))
        assert_that(result, has_properties({'start_date': datetime.datetime(2020, 1, 14, 6, 0, 0),
                                            'end_date': datetime.datetime(2020, 1, 15, 6, 0, 0)}))

        # environment
        view = SitesUploadCSVView(sites, self.request)
        result = view._process_environment({'Environment': 'shared:prod'})
        assert_that(ISharedEnvironment.providedBy(result), is_(True))
        assert_that(result, has_properties({'name': 'prod'}))

        view = SitesUploadCSVView(sites, self.request)
        assert_that(calling(view._process_environment).with_args({'Environment': 'dedicated:Sxxx2', 'Host Machine': 'hh'}),
                    raises(ValueError, pattern='Unknown host: hh.'))

        hosts = self._root().get('hosts')
        hosts.addHost(PersistentHost(host_name='hh', capacity=5))
        hosts.addHost(PersistentHost(host_name='xx', capacity=5))
        hosts.addHost(PersistentHost(host_name='host3.4pp', capacity=5))

        view = SitesUploadCSVView(sites, self.request)
        result = view._process_environment({'Environment': 'dedicated:Sxxx2', 'Host Machine': 'hh'})
        assert_that(IDedicatedEnvironment.providedBy(result), is_(True))
        assert_that(result, has_properties({'pod_id': 'Sxxx2', 'host': has_properties({'host_name': 'hh'})}))

        view = SitesUploadCSVView(sites, self.request)
        result = view._process_environment({'Environment': 'dedicated:Sxxx2', 'Host Machine': ''})
        assert_that(IDedicatedEnvironment.providedBy(result), is_(True))
        assert_that(result, has_properties({'pod_id': 'Sxxx2', 'host': has_properties({'host_name': 'host3.4pp'})}))

        assert_that(calling(view._process_environment).with_args({}), raises(KeyError, pattern="Environment"))
        assert_that(calling(view._process_environment).with_args({'Environment': 'dedicated:Sxxy'}), raises(KeyError, pattern="Host Machine"))
        assert_that(calling(view._process_environment).with_args({'Environment': ''}), raises(ValueError, pattern="Invalid Environment."))
        assert_that(calling(view._process_environment).with_args({'Environment': 'x:y'}), raises(ValueError, pattern="Invalid Environment."))
        assert_that(calling(view._process_environment).with_args({'Environment': 'x'}), raises(ValueError, pattern="Invalid Environment."))

        # owner
        result = view._process_owner({'Hubspot Contact': 'test@nt.com'})
        assert_that(ICustomer.providedBy(result))
        assert_that(result, has_properties({'email': 'test@nt.com', 'hubspot_contact': None, 'name': None}))
        assert_that(customers, has_length(1))

        result = view._process_owner({'Hubspot Contact': 'test2@nt.com'})
        assert_that(result, has_properties({'email': 'test2@nt.com', 'hubspot_contact': None, 'name': None}))
        assert_that(customers, has_length(2))

        result = view._process_owner({'Hubspot Contact': 'test2@nt.com'})
        assert_that(result, has_properties({'email': 'test2@nt.com', 'hubspot_contact': None, 'name': None}))
        assert_that(customers, has_length(2))

        _client.fetch_contact_by_email = lambda email: {'canonical-vid': 123, 'email': email, 'name': 'Test OK'}
        result = view._process_owner({'Hubspot Contact': 'test3@nt.com'})
        assert_that(result, has_properties({'email': 'test3@nt.com', 'hubspot_contact': has_properties({'contact_vid': '123'}), 'name': 'Test OK'}))
        assert_that(customers, has_length(3))

        result = view._process_owner({'Hubspot Contact': ''})
        assert_that(result.email, is_('tony.tarleton@nextthought.com'))

        assert_that(calling(view._process_owner).with_args({'Hubspot Contact': 'test'}), raises(hexc.HTTPUnprocessableEntity, pattern="Invalid email."))

        # row: creator, createdTime, parent_site, status
        assert_that(sites, has_length(0))
        params = { 'nti_site': 'abc.com', 'nti_URL': 'xyz.com',
                   'License Type': 'trial', 'LicenseStartDate': '2020-01-14', 'LicenseEndDate': '2020-01-15',
                   'Environment': 'dedicated: Sxxx1', 'Host Machine': 'xx',
                   'Hubspot Contact': 'test@nt.com',
                   'Status': '',
                   'Parent Site': '',
                   'Site Created Date': ''}
        view = SitesUploadCSVView(sites, self.request)
        view._process_row(params)
        assert_that(sites, has_length(1))
        assert_that(sites['Sxxx1'], has_properties({'dns_names': is_(['abc.com', 'xyz.com']),
                                                    'license': has_properties({'start_date': datetime.datetime(2020,1,14,6,0,0), 'end_date': datetime.datetime(2020,1,15,6,0,0)}),
                                                    'environment': has_properties({'pod_id': 'Sxxx1', 'host': has_properties({'host_name':'xx'})}),
                                                    'owner': has_properties({'email': 'test@nt.com'}),
                                                    'status': 'UNKNOWN',
                                                    'parent_site': None,
                                                    'createdTime': 1301634000,
                                                    'creator': None
                                                    }))
        assert_that(view._parent_sites_ids, has_length(2))
        assert_that(view._parent_sites_ids, has_entries({'abc.com': 'Sxxx1', 'xyz.com': 'Sxxx1'}))

        params.update({'nti_site': 'abc1.com', 'nti_URL': 'xyz1.com',
                       'Environment': 'dedicated: Sxxx2', 'Host Machine': 'xx',
                       'Status': 'ACTIVE',
                       'Parent Site': 'abc.com',
                       'Site Created Date': '2020-01-14'})
        view._process_row(params, remoteUser="testuser")
        assert_that(sites, has_length(2))
        assert_that(sites['Sxxx2'], has_properties({'dns_names': is_(['abc1.com', 'xyz1.com']),
                                                    'license': has_properties({'start_date': datetime.datetime(2020,1,14,6,0,0), 'end_date': datetime.datetime(2020,1,15,6,0,0)}),
                                                    'environment': has_properties({'pod_id': 'Sxxx2', 'host': has_properties({'host_name':'xx'})}),
                                                    'owner': has_properties({'email': 'test@nt.com'}),
                                                    'status': 'ACTIVE',
                                                    'parent_site': is_(sites['Sxxx1']),
                                                    'createdTime': 1578981600,
                                                    'creator': 'testuser'
                                                    }))
        assert_that(view._parent_sites_ids, has_length(2))
        assert_that(view._parent_sites_ids, has_entries({'abc.com': 'Sxxx1', 'xyz.com': 'Sxxx1',}))

        params.update({'nti_site': 'abc1.com', 'nti_URL': '','Environment': 'dedicated: Sxxx3',})
        assert_that(calling(view._process_row).with_args(params, remoteUser="testuser"),
                    raises(hexc.HTTPConflict, pattern="Existing dns_names: abc1.com."))

        params.update({'nti_site': 'abc2.com', 'nti_URL': '','Environment': 'dedicated: Sxxx3', 'Parent Site': 'xxx'})
        assert_that(calling(view._process_row).with_args(params, remoteUser="testuser"),
                    raises(hexc.HTTPUnprocessableEntity, pattern="Parent site not found: xxx."))

        params.update({'nti_site': 'abc2.com', 'nti_URL': '','Environment': 'dedicated: Sxxx3', 'Parent Site': 'abc.com'})
        view._process_row(params, remoteUser="testuser")
        assert_that(sites, has_length(3))

        params.update({'nti_site': 'abc3.com', 'nti_URL': '','Environment': 'dedicated: Sxxx4', 'Parent Site': ''})
        view._process_row(params, remoteUser="testuser")
        assert_that(sites, has_length(4))
        assert_that(view._parent_sites_ids, has_length(3))
        assert_that(view._existing_site_dns_names, has_length(6))

    @with_test_app()
    @mock.patch('nti.app.environments.views.sites.get_hubspot_client')
    def testGet(self, mock_client):
        mock_client.return_value = client = mock.MagicMock()
        client.fetch_contact_by_email = lambda email: None
        
        sites = self._root().get('sites')
        assert_that(sites, has_length(0))
        with ensure_free_txn():
            hosts = self._root().get('hosts')
            host1 = hosts.addHost(PersistentHost(host_name='host3.4pp', capacity=5))
            host2 = hosts.addHost(PersistentHost(host_name='app1.4pp', capacity=5))
        self._upload_file(self.site_info)

        assert_that(sites, has_length(4))
        assert_that(sites['S79b714e55864457388118892dc6df51b'].dns_names, is_(['intelligentedu.nextthought.com']))

        assert_that(host1.current_load, is_(0))
        assert_that(host2.current_load, is_(2))


class TestSiteUsagesBulkUpdateView(BaseAppTest):

    @with_test_app()
    def testSiteUsagesBulkUpdateView(self):
        url = '/onboarding/sites/@@usages'
        params = []
        self.testapp.post_json(url, params=params, status=302, extra_environ=self._make_environ(username=None))
        self.testapp.post_json(url, params=params, status=403, extra_environ=self._make_environ(username='user001'))
        result = self.testapp.post_json(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'total_updated': 0}))

        params = {}
        result = self.testapp.post_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body['message'], is_('Invalid data format.'))

        params = {'site_id': ''}
        result = self.testapp.post_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body['message'], is_('site_id should be non-empty string: .'))

        params = {'site_id': 'Sxx'}
        result = self.testapp.post_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body['message'], is_('No site found: Sxx.'))

        with ensure_free_txn():
            sites = self._root().get('sites')
            for siteId in ('Sxx', 'Sxx1'):
                sites.addSite(PersistentSite(license=TrialLicense(start_date=datetime.datetime(2019, 12, 12, 0, 0, 0),
                                                                  end_date=datetime.datetime(2019, 12, 13, 0, 0, 0)),
                                             created=datetime.datetime(2019, 12, 11, 0, 0, 0),
                                             status='PENDING',
                                             dns_names=['x', 'y']), siteId=siteId)
            assert_that(ISiteUsage(sites['Sxx']), has_properties({'total_user_count': None, 'total_admin_count': None, 'monthly_active_users': None}))

        params = {'site_id': 'Sxx'}
        result = self.testapp.post_json(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'total_updated': 1}))
        assert_that(ISiteUsage(sites['Sxx']), has_properties({'total_user_count': None, 'total_admin_count': None, 'monthly_active_users': None}))

        params = {'site_id': 'Sxx', 'total_user_count': 10, 'total_admin_count': 8, 'monthly_active_users': 9}
        result = self.testapp.post_json(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'total_updated': 1}))
        assert_that(ISiteUsage(sites['Sxx']), has_properties({'total_user_count': 10, 'total_admin_count': 8, 'monthly_active_users': 9}))

        params = [{'site_id': 'Sxx', 'total_user_count': 100, 'total_admin_count': 8, 'monthly_active_users': 9},
                  {'site_id': 'Sxx1', 'total_user_count': 20, 'total_admin_count': 18, 'monthly_active_users': 19}]
        result = self.testapp.post_json(url, params=params, status=200, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'total_updated': 2}))
        assert_that(ISiteUsage(sites['Sxx']), has_properties({'total_user_count': 100, 'total_admin_count': 8, 'monthly_active_users': 9}))
        assert_that(ISiteUsage(sites['Sxx1']), has_properties({'total_user_count': 20, 'total_admin_count': 18, 'monthly_active_users': 19}))

        params = [{'site_id': 'Sxx', 'total_user_count': 100, 'total_admin_count': 'ss'}]
        result = self.testapp.post_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body['message'], is_("invalid literal for int() with base 10: 'ss'"))
