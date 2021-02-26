import json
import jwt
import os
import requests
import unittest

from unittest import mock

from hamcrest import is_
from hamcrest import is_not
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_key
from hamcrest import calling
from hamcrest import raises

from nti.app.environments.api.siteinfo import NTClient
from nti.app.environments.api.siteinfo import BearerTokenFactory
from nti.app.environments.api.siteinfo import get_workspace
from nti.app.environments.api.siteinfo import get_collection
from nti.app.environments.api.siteinfo import get_link

from nti.app.environments.models.sites import PersistentSite


class TestSiteInfo(unittest.TestCase):

    @mock.patch('nti.app.environments.api.siteinfo.requests.Session')
    def test_fetch_site_info(self, mock_session):
        mock_resp = mock.MagicMock(status_code=409,
                                   json=mock.MagicMock(return_value={}))
        mock_session.return_value = mock.MagicMock(get=mock.MagicMock(return_value=mock_resp))

        site = PersistentSite()
        site.dns_names = ['xxx']
        
        client = NTClient(site)
        result = client.fetch_site_info()
        assert_that(result, is_(None))

        json_body = {'assets': {'login_logo': {'href': "/xxx.logo"}},
                     'brand_name': 'Test Site'}
        mock_session.return_value = mock.MagicMock(get=mock.MagicMock(return_value=mock.MagicMock(status_code=200,
                                                                                                  json=mock.MagicMock(return_value=json_body))))
        client = NTClient(site)
        result = client.fetch_site_info()
        assert_that(result, has_entries({'site_url': 'https://xxx',
                                         'brand_name': 'Test Site',
                                         'logo_url': 'https://xxx/xxx.logo'}))

        mock_session.return_value = mock.MagicMock(get=mock.MagicMock(side_effect=requests.exceptions.ConnectionError))
        client = NTClient(site)
        result = client.fetch_site_info()
        assert_that(result, is_(None))

    def test_make_url(self):

        class MockSite(object):

            @property
            def dns_names(self):
                return ['nt.com']

        link = {'href': '/dataserver2/dict'}

        class HrefObject(object):

            href = '/dataserver2/obj'

        client = NTClient(MockSite())

        assert_that(client.make_url('https://google.com'), is_('https://google.com'))
        assert_that(client.make_url(link), is_('https://nt.com/dataserver2/dict'))
        assert_that(client.make_url(HrefObject()), is_('https://nt.com/dataserver2/obj'))
        assert_that(client.make_url('/dataserver2/foo'), is_('https://nt.com/dataserver2/foo'))
     

class TestPlatformJsonObjects(unittest.TestCase):

    def setUp(self):
        with open(os.path.join(os.path.dirname(__file__), 'servicedoc.json')) as f:
            self.service = json.load(f)
    
    def test_get_workspace(self):
        assert_that(self.service, has_entries('Class', 'Service'))
        assert_that(get_workspace(self.service, 'FOO'), is_(None))
        assert_that(get_workspace(self.service, 'Analytics'), has_entries('Title', 'Analytics'))

    def test_get_collection(self):
        analytics = get_workspace(self.service, 'Analytics')
        assert_that(get_collection(analytics, 'foo'), is_(None))
        assert_that(get_collection(analytics, 'Sessions'), has_entries('Title', 'Sessions'))

    def test_get_link(self):
        sessions = get_collection(get_workspace(self.service, 'Analytics'), 'Sessions')
        assert_that(get_link(sessions, 'foo'), is_(None))
        assert_that(get_link(sessions, 'active_session_count'),
                    has_entries('href', '/dataserver2/analytics/sessions/@@active_session_count'))


class TestBearerTokenFactory(unittest.TestCase):
    def setUp(self):
        self.site = PersistentSite(ds_site_id='site')
        self.factory = BearerTokenFactory(self.site, 'secret', 'nti', default_ttl=60)

    def tearDown(self):
        del self.factory
        
    def test_jwt_only_username(self):
        token = self.factory.make_bearer_token('admin@nextthought.com')
        decoded = jwt.decode(token, self.factory.secret, audience=self.site.ds_site_id, algorithms=[self.factory.algorithm])
        
        assert_that(decoded, has_entries({'login': 'admin@nextthought.com',
                                          'aud': self.site.ds_site_id,
                                          'realname': None,
                                          'email': None,
                                          'create': "true",
                                          "admin": "true",
                                          "iss": "nti",
                                          "exp": is_not(None)}))

    def test_jwt_full(self):
        token = self.factory.make_bearer_token('admin@nextthought.com',
                                               realname="Larry Bird",
                                               email="larry.bird@nt.com")
        decoded = jwt.decode(token, self.factory.secret, audience=self.site.ds_site_id, algorithms=[self.factory.algorithm])
        
        assert_that(decoded, has_entries({'login': 'admin@nextthought.com',
                                          'aud': self.site.ds_site_id,
                                          'realname': "Larry Bird",
                                          'email': "larry.bird@nt.com",
                                          'create': "true",
                                          "admin": "true",
                                          "iss": "nti",
                                          "exp": is_not(None)}))

    def test_jwt_no_ttl(self):
        token = self.factory.make_bearer_token('admin@nextthought.com',
                                               realname="Larry Bird",
                                               email="larry.bird@nt.com",
                                               ttl=None)
        decoded = jwt.decode(token, self.factory.secret, audience=self.site.ds_site_id, algorithms=[self.factory.algorithm])
        assert_that(decoded, is_not(has_key('ttl')))

    def test_jwt_ttl_works(self):
        token = self.factory.make_bearer_token('admin@nextthought.com',
                                               realname="Larry Bird",
                                               email="larry.bird@nt.com",
                                               ttl=-10)
        # ttl in the past forces expiration
        assert_that(calling(jwt.decode).with_args(token, self.factory.secret, audience=self.site.ds_site_id, algorithms=[self.factory.algorithm]),
                    raises(jwt.exceptions.ExpiredSignatureError))

    def test_jwt_no_id(self):
        no_id_site = PersistentSite()
        try:
            no_id_factory = BearerTokenFactory(no_id_site, 'secret', 'nti', default_ttl=60)
        
        except AssertionError:
            "Site without ds_site_id was caught correctly."
        
