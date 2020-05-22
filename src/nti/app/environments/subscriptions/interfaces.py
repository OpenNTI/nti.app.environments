from zope import interface

from nti.schema.field import DateTime
from nti.schema.field import Object
from nti.schema.field import ValidTextLine

from nti.app.environments.models.interfaces import ICustomer
from nti.app.environments.models.interfaces import ILMSSite

class ICheckoutSession(interface.Interface):

    id = ValidTextLine(title='A unique identifier for this checkout',
                       required=True)

    customer = Object(ICustomer,
                      title='The customer doing the checkout')

    site = Object(ILMSSite,
                  title='The site being subscribed to')

    completed = DateTime(title='The time the session was completed',
                         required=False)

class ICheckoutSessionStorage(interface.Interface):

    def track_session(customer, site):
        """
        Start tracking a checkout session for the provided customer and site.
        returns ICheckoutSession
        """

    def find_session(id):
        """
        Return the ICheckoutSession with the given id or None if
        no session with the id exists.
        """
