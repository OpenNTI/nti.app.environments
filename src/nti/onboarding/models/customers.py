from persistent import Persistent

from zope import interface

from zope.container.interfaces import INameChooser

from zope.container.contained import Contained

from zope.container.folder import Folder

from nti.schema.fieldproperty import createFieldProperties

from .interfaces import ICustomer
from .interfaces import ICustomersContainer


@interface.implementer(ICustomersContainer)
class CustomersFolder(Folder):

    def create_user(self, user):
        key = INameChooser(self).chooseName(user.email, user)
        user.__name__ = key
        self[key] = user
        return user

@interface.implementer(ICustomer)
class PersistentUser(Persistent, Contained):

    createFieldProperties(ICustomer)

