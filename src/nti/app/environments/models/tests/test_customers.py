import datetime

from hamcrest import assert_that
from hamcrest import has_properties
from hamcrest import has_length
from hamcrest import has_items
from hamcrest import not_none
from hamcrest import is_

from zope.schema._bootstrapinterfaces import RequiredMissing
from zope.schema import getValidationErrors

from nti.app.environments.tests import BaseTest

from nti.app.environments.models.customers import HubspotContact
from nti.app.environments.models.customers import PersistentCustomer
from nti.app.environments.models.customers import CustomersFolder

from nti.app.environments.models.interfaces import IHubspotContact
from nti.app.environments.models.interfaces import ICustomer


class TestCustomers(BaseTest):

    def testHubspotContact(self):
        inst = HubspotContact()
        assert_that(inst, has_properties({'contact_vid': None}))
        errors = getValidationErrors(IHubspotContact, inst)
        assert_that(errors, has_length(1))
        assert_that(errors, has_items(('contact_vid', RequiredMissing('contact_vid'))))

        inst = HubspotContact(contact_vid='xxx')
        assert_that(inst, has_properties({'contact_vid': 'xxx'}))
        errors = getValidationErrors(IHubspotContact, inst)
        assert_that(errors, has_length(0))

    def testPersistentCustomer(self):
        inst = PersistentCustomer()
        assert_that(inst, has_properties({'email': None,
                                          'name': None,
                                          'created': None,
                                          'hubspot_contact': None,
                                          'last_verified': None}))
        errors = getValidationErrors(ICustomer, inst)
        assert_that(errors, has_length(2))
        assert_that(errors, has_items(('email', RequiredMissing('email')),
                                      ('created', RequiredMissing('created'))))

        inst = PersistentCustomer(email='xxx@gmail.com',
                                  created=datetime.datetime.utcnow())
        assert_that(inst, has_properties({'email': 'xxx@gmail.com',
                                          'created': not_none(),
                                          'name': None,
                                          'hubspot_contact': None,
                                          'last_verified': None}))
        errors = getValidationErrors(ICustomer, inst)
        assert_that(errors, has_length(0))

        inst.hubspot_contact = HubspotContact(contact_vid='xxx')
        inst.name = 'test last'
        inst.last_verified = datetime.datetime.utcnow()
        assert_that(inst, has_properties({'name': 'test last',
                                          'hubspot_contact': has_properties({'contact_vid': 'xxx'}),
                                          'last_verified': not_none()}))
        errors = getValidationErrors(ICustomer, inst)
        assert_that(errors, has_length(0))

    def testCustomersFolder(self):
        folder = CustomersFolder()
        inst = PersistentCustomer(email='xxx@gmail.com')
        folder.addCustomer(inst)

        assert_that(folder, has_length(1))
        assert_that(folder['xxx@gmail.com'], is_(inst))

        assert_that(folder.getCustomer('yyy@gmail.com'), is_(None))
        assert_that(folder.getCustomer('xxx@gmail.com'), is_(inst))