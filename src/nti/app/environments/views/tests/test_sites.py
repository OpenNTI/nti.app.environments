from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import has_properties
from hamcrest import instance_of
from hamcrest import is_

from nti.app.environments.views.customers import getOrCreateCustomer
from nti.app.environments.views.tests import BaseAppTest
from nti.app.environments.views.tests import with_test_app
from nti.app.environments.views.tests import ensure_free_txn
from nti.app.environments.models.sites import TrialLicense, EnterpriseLicense


class TestSiteCreationView(BaseAppTest):

    def _params(self, env_type='shared', license_type="trial", site_id=None):
        env = {'name': 'assoc'} if env_type == 'shared' else {'pod_id': 'xxx', 'host': 'okc.com'}
        return {
            'site_id': site_id,
            "owner": "test@gmail.com",
            "owner_username": "test004",
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
    def test_site(self):
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

        result = self.testapp.post_json(url, params=params, status=201, extra_environ=self._make_environ(username='admin001'))
        result = result.json_body
        assert_that(result, is_({}))
        assert_that(sites, has_length(1))
        site = [x for x in sites.values()][0]
        assert_that(site, has_properties({'owner': has_properties({'email': 'test@gmail.com'}),
                                                           'owner_username': 'test004',
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
                                                               'owner_username': 'test004',
                                                               'environment': has_properties({'pod_id': 'xxx', 'host': 'okc.com'}),
                                                               'license': instance_of(EnterpriseLicense),
                                                               'status': 'PENDING',
                                                               'dns_names': ['t1.nextthought.com', 't2.nextthought.com']}))
