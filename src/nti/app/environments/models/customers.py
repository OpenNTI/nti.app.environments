from persistent import Persistent

from pyramid.security import Allow
from pyramid.security import ALL_PERMISSIONS

from zope import interface

from zope.container.contained import Contained

from zope.container.folder import Folder

from nti.property.property import LazyOnClass

from nti.schema.fieldproperty import createFieldProperties
from nti.schema.schema import SchemaConfigured

from nti.app.environments.auth import ADMIN_ROLE
from nti.app.environments.auth import ACCOUNT_MANAGEMENT_ROLE
from nti.app.environments.auth import ACT_READ

from nti.app.environments.models.interfaces import ICustomer
from nti.app.environments.models.interfaces import ICustomersContainer
from nti.app.environments.models.interfaces import IHubspotContact


@interface.implementer(IHubspotContact)
class HubspotContact(SchemaConfigured, Persistent, Contained):

    createFieldProperties(IHubspotContact)

    mimeType = mime_type = 'application/vnd.nextthought.app.environments.hubspotcontact'


@interface.implementer(ICustomersContainer)
class CustomersFolder(Folder):

    @LazyOnClass
    def __acl__(self):
        return [(Allow, ADMIN_ROLE, ALL_PERMISSIONS),
                (Allow, ACCOUNT_MANAGEMENT_ROLE, ACT_READ)]

    def addCustomer(self, customer):
        self[customer.email] = customer
        return customer

    def getCustomer(self, email):
        return self.get(email)


@interface.implementer(ICustomer)
class PersistentCustomer(SchemaConfigured, Persistent, Contained):

    createFieldProperties(ICustomer)

    mimeType = mime_type = 'application/vnd.nextthought.app.environments.customer'
