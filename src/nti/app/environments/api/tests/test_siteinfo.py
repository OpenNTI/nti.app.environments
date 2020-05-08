import jwt
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


class TestBearerTokenFactory(unittest.TestCase):

    def setUp(self):
        self.factory = BearerTokenFactory('secret', 'nti', default_ttl=60)

    def tearDown(self):
        del self.factory
        
    def test_jwt_only_username(self):
        token = self.factory.make_bearer_token('admin@nextthought.com')
        decoded = jwt.decode(token, self.factory.secret)
        
        assert_that(decoded, has_entries({'login': 'admin@nextthought.com',
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
        decoded = jwt.decode(token, self.factory.secret)
        
        assert_that(decoded, has_entries({'login': 'admin@nextthought.com',
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
        decoded = jwt.decode(token, self.factory.secret)
        assert_that(decoded, is_not(has_key('ttl')))

    def test_jwt_ttl_works(self):
        token = self.factory.make_bearer_token('admin@nextthought.com',
                                               realname="Larry Bird",
                                               email="larry.bird@nt.com",
                                               ttl=-10)
        # ttl in the past forces expiration
        assert_that(calling(jwt.decode).with_args(token, self.factory.secret),
                    raises(jwt.exceptions.ExpiredSignatureError))
