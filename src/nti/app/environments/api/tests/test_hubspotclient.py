import hubspot3
import unittest

from unittest import mock

from hamcrest import is_
from hamcrest import calling
from hamcrest import raises
from hamcrest import assert_that
from hamcrest import has_entries

from nti.app.environments.api.hubspotclient import HubspotClient


class TestHubspotClient(unittest.TestCase):

    @mock.patch("nti.app.environments.api.hubspotclient.Hubspot3")
    def test_fetch_contact_with_email(self, mockHub):
        mockcontacts = mock.Mock()
        mockcontacts.get_contact_by_email.return_value = {'canonical-vid': 12630274,
                                                          'properties': {'email': {'value': 'test@gmail.com'}}}
        mockcontacts.get_contact_by_email.__name__ = 'test'
        mockHub.return_value = mock.Mock(contacts=mockcontacts)

        client = HubspotClient("test")
        result = client.fetch_contact_by_email('testing@gmail.com')
        assert_that(result, has_entries({'email': 'test@gmail.com',
                                         'name': '',
                                         'canonical-vid': 12630274}))

        # No found
        def _get(*args, **kwargs):
            raise hubspot3.error.HubspotNotFound(None, None)
        mockcontacts.get_contact_by_email.side_effect = _get
        result = client.fetch_contact_by_email('testing@gmail.com')
        assert_that(result, is_(None))

        def _get2(*args, **kwargs):
            raise hubspot3.error.HubspotError(None, None)
        mockcontacts.get_contact_by_email.side_effect = _get2
        assert_that(calling(client.fetch_contact_by_email).with_args('testing@gmail.com'),
                    raises(hubspot3.error.HubspotError))

        mockcontacts.get_contact_by_email.side_effect = None
        mockcontacts.get_contact_by_email.return_value = None
        result = client.fetch_contact_by_email('testing@gmail.com')
        assert_that(result, is_(None))

        # email, firstname
        mockcontacts.get_contact_by_email.return_value = {'canonical-vid': 12630274,
                                                          'properties': {'email': {'value': 'test@gmail.com'},
                                                                         'firstname': {'value': 'TestFirst'}}}
        result = client.fetch_contact_by_email('testing@gmail.com')
        assert_that(result, has_entries({'email': 'test@gmail.com',
                                         'name': 'TestFirst',
                                         'canonical-vid': 12630274}))

        # email, lastname
        mockcontacts.get_contact_by_email.return_value = {'canonical-vid': 12630274,
                                                          'properties': {'email': {'value': 'test@gmail.com'},
                                                                         'lastname': {'value': 'TestLast'}}}
        result = client.fetch_contact_by_email('testing@gmail.com')
        assert_that(result, has_entries({'email': 'test@gmail.com',
                                         'name': 'TestLast',
                                         'canonical-vid': 12630274}))

        # email, lastname, firstname
        mockcontacts.get_contact_by_email.return_value = {'canonical-vid': 12630274,
                                                          'properties': {'email': {'value': 'test@gmail.com'},
                                                                         'lastname': {'value': 'TestLast'},
                                                                         'firstname': {'value': 'TestFirst'}}}
        result = client.fetch_contact_by_email('testing@gmail.com')
        assert_that(result, has_entries({'email': 'test@gmail.com',
                                         'name': 'TestFirst TestLast',
                                         'canonical-vid': 12630274}))
