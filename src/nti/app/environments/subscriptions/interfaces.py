from zope import interface

from nti.schema.field import DateTime
from nti.schema.field import Object
from nti.schema.field import ValidTextLine
from nti.schema.field import Int

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

class IPrice(interface.Interface):

    id = ValidTextLine(title='Globally Unique id for this price',
                       required=True)

    cost = Int(title='The cost in cents',
                    required=True)

    name = ValidTextLine(title='name for this price',
                         required=True)

    stripe_plan_id = ValidTextLine(title='The stripe plan or price identifier',
                                   required=False)

    # Object is an IProduct
    product = Object(interface.Interface,
                     title='The product this price is associated with',
                     required=True)

class IProduct(interface.Interface):

    id = ValidTextLine(title='Globally Unique id for this product',
                       required=True)

    title = ValidTextLine(title='name for this price',
                         required=True)

    monthly_price = Object(IPrice,
                          title='The monthly pricing information',
                          required=False)

    yearly_price = Object(IPrice,
                         title='The yearly pricing information',
                         required=False)

    min_seats = Int(title='The minimum number of seats required for this product',
                    required=False,
                    min=0,
                    max=999,
                    default=0)

    max_seats = Int(title='The minimum number of seats required for this product',
                    required=False,
                    min=0,
                    max=999)

    
