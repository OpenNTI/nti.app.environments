from zope import component
from zope import interface

from nti.wref.interfaces import IWeakRef

from nti.app.environments.models.interfaces import ICustomer
from nti.app.environments.models.utils import get_customers_folder


@component.adapter(ICustomer)
@interface.implementer(IWeakRef)
class CustomerWeakRef(object):

    def __init__(self, ob):
        self.email = ob.email

    def __call__(self):
        folder = get_customers_folder()
        return folder.getCustomer(self.email)
