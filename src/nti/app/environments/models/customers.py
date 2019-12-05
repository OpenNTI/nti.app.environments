from persistent import Persistent

from pyramid.security import Allow
from pyramid.security import ALL_PERMISSIONS

from zope import interface

from zope.container.contained import Contained

from zope.container.folder import Folder

from nti.property.property import LazyOnClass

from nti.schema.fieldproperty import createFieldProperties

from nti.app.environments.auth import ADMIN_ROLE

from nti.app.environments.models.interfaces import ICustomer
from nti.app.environments.models.interfaces import ICustomersContainer


@interface.implementer(ICustomersContainer)
class CustomersFolder(Folder):

    @LazyOnClass
    def __acl__(self):
        return [(Allow, ADMIN_ROLE, ALL_PERMISSIONS)]

    def getCustomer(self, email):
        return self.get(email)


@interface.implementer(ICustomer)
class PersistentCustomer(Persistent, Contained):

    createFieldProperties(ICustomer)
