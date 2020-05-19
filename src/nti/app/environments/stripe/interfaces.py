from zope import interface

from nti.schema.field import HTTPURL
from nti.schema.field import Object
from nti.schema.field import ValidTextLine

class IStripeKey(interface.Interface):

    publishable_key = ValidTextLine(title='The Stripe Publishable Key',
                                    required=True)

    secret_key = ValidTextLine(title='The Stripe Secret Key',
                               required=True)

class IStripeCustomer(interface.Interface):
    """
    A representation of a stripe customer. Typically obtained
    by way of adaptation
    """

    customer_id = ValidTextLine(title='The stripe customer id',
                                required=True)

class IStripeBillingPortalSession(interface.Interface):
    """
    Represents a stripe billing portal session.

    https://stripe.com/docs/api/self_service_portal/create
    """

    id = ValidTextLine(title='The session identifier')

    customer = Object(IStripeCustomer,
                      title='The stripe customer for this session')

    url = HTTPURL(title='The url to launch the billing portal.',
                  description='The portal url is one time use and has a short lifetime')
    
class IStripeBillingPortal(interface.Interface):

    def generate_session(customer, return_url):
        """
        Initialize a billing portal session for the provided customer.
        The user will be sent to the return_url on completion. returns an
        implementation of IStripeBillingPortalSession.

        Note: Do not rely on the return_url being called. Handle consuming
        changes via webhooks or polling.
        """
