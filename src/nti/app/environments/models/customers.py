from persistent import Persistent

from zope import interface

from zope.container.contained import Contained

from zope.container.folder import Folder

from nti.schema.fieldproperty import createFieldProperties


from .interfaces import ICustomer
from .interfaces import ICustomersContainer

@interface.implementer(ICustomersContainer)
class CustomersFolder(Folder):

    def getCustomer(self, email):
        return self.get(email)


@interface.implementer(ICustomer)
class PersistentCustomer(Persistent, Contained):

    createFieldProperties(ICustomer)
