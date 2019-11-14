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

    pass

@interface.implementer(ICustomer)
class PersistentCustomer(Persistent, Contained):

    createFieldProperties(ICustomer)

