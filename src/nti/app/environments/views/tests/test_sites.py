from zope import component

from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import has_properties
from hamcrest import instance_of
from hamcrest import is_

from pyramid.interfaces import IRootFactory
from nti.app.environments.views.customers import getOrCreateCustomer
from nti.app.environments.views.tests import BaseTest
from nti.app.environments.views.tests import with_test_app
from nti.app.environments.views.tests import ensure_free_txn
from nti.app.environments.models.sites import TrialLicense


class TestSiteCreationView(BaseTest):

    @property
    def _root(self):
        return component.getUtility(IRootFactory)(self.request)

    def _params(self):
        return {
            "owner": "test@gmail.com",
            "owner_username": "test004",
            "environment": {
                "type": "shared",
                "name": "assoc"
            },
            "license": "trial",
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
            sites = self._root.get('sites')
            assert_that(sites, has_length(0))
            getOrCreateCustomer(self._root.get('customers'), 'test@gmail.com')

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
            sites = self._root.get('sites')
            assert_that(sites, has_length(0))
