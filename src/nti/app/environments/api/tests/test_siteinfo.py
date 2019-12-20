import requests
import unittest

from unittest import mock

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import has_entries

from nti.app.environments.api.siteinfo import NTClient


class TestSiteInfo(unittest.TestCase):

    @mock.patch('nti.app.environments.api.siteinfo.requests.Session')
    def test_fetch_site_info(self, mock_session):
        mock_resp = mock.MagicMock(status_code=409,
                                   json=mock.MagicMock(return_value={}))
        mock_session.return_value = mock.MagicMock(get=mock.MagicMock(return_value=mock_resp))
        
        client = NTClient()
        result = client.fetch_site_info('xxx')
        assert_that(result, is_(None))

        json_body = {'assets': {'login_logo': {'href': "/xxx.logo"}},
                     'brand_name': 'Test Site'}
        mock_session.return_value = mock.MagicMock(get=mock.MagicMock(return_value=mock.MagicMock(status_code=200,
                                                                                                  json=mock.MagicMock(return_value=json_body))))
        client = NTClient()
        result = client.fetch_site_info('xxx')
        assert_that(result, has_entries({'site_url': 'https://xxx',
                                         'brand_name': 'Test Site',
                                         'logo_url': 'https://xxx/xxx.logo'}))

        mock_session.return_value = mock.MagicMock(get=mock.MagicMock(side_effect=requests.exceptions.ConnectionError))
        client = NTClient()
        result = client.fetch_site_info('xxx')
        assert_that(result, is_(None))
