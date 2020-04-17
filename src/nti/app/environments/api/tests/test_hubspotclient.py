import hubspot3

from unittest import mock

from hamcrest import is_
from hamcrest import calling
from hamcrest import raises
from hamcrest import assert_that
from hamcrest import has_entries

from nti.app.environments.api.hubspotclient import HubspotClient

from nti.app.environments.tests import BaseTest


class TestHubspotClient(BaseTest):

    @mock.patch("nti.app.environments.api.hubspotclient.Hubspot3")
    def test_fetch_contact_with_email(self, mockHub):
        mockcontacts = mock.Mock()
        mockcontacts.get_by_email.return_value = {'canonical-vid': 12630274,
                                                          'properties': {'email': {'value': 'test@gmail.com'}}}
        mockcontacts.get_by_email.__name__ = 'test'
        mockHub.return_value = mock.Mock(contacts=mockcontacts)

        client = HubspotClient("test")
        result = client.fetch_contact_by_email('testing@gmail.com')
        assert_that(result, has_entries({'email': 'test@gmail.com',
                                         'name': '',
                                         'canonical-vid': 12630274}))

        # No found
        def _get(*args, **kwargs):
            raise hubspot3.error.HubspotNotFound(None, None)
        mockcontacts.get_by_email.side_effect = _get
        result = client.fetch_contact_by_email('testing@gmail.com')
        assert_that(result, is_(None))

        def _get2(*args, **kwargs):
            raise hubspot3.error.HubspotError(None, None)
        mockcontacts.get_by_email.side_effect = _get2
        assert_that(calling(client.fetch_contact_by_email).with_args('testing@gmail.com'),
                    raises(hubspot3.error.HubspotError))

        mockcontacts.get_by_email.side_effect = None
        mockcontacts.get_by_email.return_value = None
        result = client.fetch_contact_by_email('testing@gmail.com')
        assert_that(result, is_(None))

        # email, firstname
        mockcontacts.get_by_email.return_value = {'canonical-vid': 12630274,
                                                          'properties': {'email': {'value': 'test@gmail.com'},
                                                                         'firstname': {'value': 'TestFirst'}}}
        result = client.fetch_contact_by_email('testing@gmail.com')
        assert_that(result, has_entries({'email': 'test@gmail.com',
                                         'name': 'TestFirst',
                                         'phone': '',
                                         'canonical-vid': 12630274}))

        # email, lastname
        mockcontacts.get_by_email.return_value = {'canonical-vid': 12630274,
                                                          'properties': {'email': {'value': 'test@gmail.com'},
                                                                         'lastname': {'value': 'TestLast'}}}
        result = client.fetch_contact_by_email('testing@gmail.com')
        assert_that(result, has_entries({'email': 'test@gmail.com',
                                         'name': 'TestLast',
                                         'phone': '',
                                         'canonical-vid': 12630274}))

        # email, lastname, firstname
        mockcontacts.get_by_email.return_value = {'canonical-vid': 12630274,
                                                          'properties': {'email': {'value': 'test@gmail.com'},
                                                                         'lastname': {'value': 'TestLast'},
                                                                         'firstname': {'value': 'TestFirst'},
                                                                         'mobilephone': {'value': '77'}}}
        result = client.fetch_contact_by_email('testing@gmail.com')
        assert_that(result, has_entries({'email': 'test@gmail.com',
                                         'name': 'TestFirst TestLast',
                                         'phone': '77',
                                         'canonical-vid': 12630274}))


    @mock.patch("nti.app.environments.api.hubspotclient.Hubspot3")
    def test_upsert_contact(self, mockHub):
        mockcontacts = mock.Mock()
        mockcontacts.get_by_email.return_value = None
        mockcontacts.get_by_email.__name__ = 'test_get'

        mockcontacts.create.return_value = {'vid': 123}
        mockcontacts.create.__name__ = 'test'

        mockcontacts.update_by_email.return_value = ''
        mockcontacts.update_by_email.__name__ = 'test_update'

        mockHub.return_value = mock.Mock(contacts=mockcontacts)

        client = HubspotClient("test")
        result = client.upsert_contact('testing@gmail.com', 'Test Last', '44')
        assert_that(result, has_entries({'contact_vid': '123'}))

        mockcontacts.get_by_email.return_value = {'vid': '456',
                                                  'properties': {'product_interest': {'value': ''}}}
        
        client = HubspotClient("test")
        result = client.upsert_contact('testing@gmail.com', 'Test Last', '44')
        assert_that(result, has_entries({'contact_vid': '456'}))

        # No found
        def _upsert(*args, **kwargs):
            raise hubspot3.error.HubspotNotFound(None, None)
        mockcontacts.update_by_email.side_effect = _upsert
        result = client.upsert_contact('testing@gmail.com', 'Test Last', '44')
        assert_that(result, is_(None))

        def _upsert2(*args, **kwargs):
            raise hubspot3.error.HubspotError(None, None)
        mockcontacts.update_by_email.side_effect = _upsert2
        assert_that(calling(client.upsert_contact).with_args('testing@gmail.com', 'Test Last', '44'),
                    raises(hubspot3.error.HubspotError))

        def _upsert3(*args, **kwargs):
            raise hubspot3.error.HubspotConflict(None, None)
        mockcontacts.update_by_email.side_effect = _upsert3
        assert_that(calling(client.upsert_contact).with_args('testing@gmail.com', 'Test Last', '44'),
                    raises(hubspot3.error.HubspotConflict))
