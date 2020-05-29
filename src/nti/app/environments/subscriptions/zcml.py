from zope import interface

from zope.component.zcml import utility

from zope.configuration.fields import Bool

from zope.schema import TextLine
from zope.schema import Int

from .interfaces import IPrice
from .interfaces import IProduct

from .license import RegistryBackedPrice
from .license import RegistryBackedProduct

logger = __import__('logging').getLogger(__name__)


class IRegisterPriceDirective(interface.Interface):
    """
    The arguments needed for creating and registering a price
    """

    id = TextLine(title='Globally Unique id for this price',
                  required=True)

    cost = Int(title='The cost in cents',
               required=True)

    name = TextLine(title='name for this price',
                    required=True)

    stripe_plan_id = TextLine(title='The stripe plan or price identifier',
                              required=False)

    product = TextLine(title='The id of a product',
                       required=True)


def registerPrice(_context, id, cost, name, product, stripe_plan_id=None):
    """
    Register a stripe key with the given alias
    """
    # We have some downstream UI components that are expecting our prices are in whole dollars.
    # Internally we don't assume that, but guard against it here for the views sake
    assert cost % 100 == 0, 'Expecting prices to be whole dollars only'
    
    p = RegistryBackedPrice(id=id, cost=cost, name=name, product=product, stripe_plan_id=stripe_plan_id)
    utility(_context, provides=IPrice, component=p, name=id)

class IRegisterProductDirective(interface.Interface):
    """
    The arguments needed for creating and registering a price
    """

    id = TextLine(title='Globally Unique id for this product',
                  required=True)

    name = TextLine(title='name for this price',
                     required=True)

    monthly_price = TextLine(title='The id of a price',
                             required=False)
    
    yearly_price = TextLine(title='The id of a price',
                            required=False)

    min_seats = Int(title='The minimum number of seats required for this product',
                    required=False,
                    min=0,
                    max=9999)

    max_seats = Int(title='The minimum number of seats required for this product',
                    required=False,
                    min=0,
                    max=9999)


def registerProduct(_context, id, name, monthly_price=None, yearly_price=None, min_seats=0, max_seats=None):
    """
    Register a stripe key with the given alias
    """

    p = RegistryBackedProduct(id=id,
                              title=name,
                              monthly_price=monthly_price,
                              yearly_price=yearly_price,
                              min_seats=min_seats,
                              max_seats=max_seats)
    utility(_context, provides=IProduct, component=p, name=id)
