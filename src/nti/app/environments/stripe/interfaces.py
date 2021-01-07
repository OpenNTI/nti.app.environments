import sys

from zope import interface

from zope.interface import Attribute


from nti.schema.field import HTTPURL
from nti.schema.field import Object
from nti.schema.field import ValidTextLine
from nti.schema.field import Integral
from nti.schema.field import Mapping
from nti.schema.field import Number

class IStripeKey(interface.Interface):

    publishable_key = ValidTextLine(title='The Stripe Publishable Key',
                                    required=True)

    secret_key = ValidTextLine(title='The Stripe Secret Key',
                               required=True)


class IWebhookSigningSecret(interface.Interface):

    secret = ValidTextLine(title='The secret key',
                           required=True)

    # Matches stripes default tolerance
    tolerance = Integral(title='The timing tolerance to allow when validating the signature',
                         required=True,
                         default=300)    

class IStripeCustomer(interface.Interface):
    """
    A representation of a stripe customer. Typically obtained
    by way of adaptation
    """

    customer_id = ValidTextLine(title='The stripe customer id',
                                required=True)


class IStripeSubscription(interface.Interface):

    id = ValidTextLine(title='The subscription identifier')


class IStripeSubscriptionBilling(interface.Interface):

    def get_subscription(subscription):
        """
        Fetch the full subscription for subscription.id
        from stripe.
        """

    def get_upcoming_invoice(subscription):
        """
        Get the next invoice for this subscription.
        """

    def update_subscription_payment_method(subscription, payment_method):
        """
        Update the default payment method for the provided description to the
        provided payment method.
        """

    def update_customer_default_payment_method(customer, payment_method):
        """
        Updates the default invoice payment method on the provided customer.
        """

class IStripeInvoice(interface.Interface):
    """
    A Stripe billing invoice object
    """
    id = ValidTextLine(title='The invoice identifier',
                       required=True)

    subscription = ValidTextLine(title='The subscription this invoice was prepared for, if any.',
                                 required=False)

class IStripeCheckoutSession(interface.Interface):

    id = ValidTextLine(title='The session identifier')

class IStripeSubscriptionItem(interface.Interface):

    plan = ValidTextLine(title='The plan identifier',
                         required=True)

    quantity = Integral(title='The quantity of the subscription',
                        required=True,
                        default=1)



class IStripeCheckout(interface.Interface):

    def generate_subscription_session(subscription_items,
                                      cancel_url,
                                      success_url,
                                      customer=None,
                                      customer_email=None,
                                      client_reference_id=None,
                                      metadata=None):
        """
        Start a checkout session to subscribe to a list of IStripeSubscriptionItem objects.
        An optional IStripeCustomer can be provided, in which case the subscription will be tied
        to an existing customer.

        The returned IStripeCheckoutSession.id can be used to launch a client side stripe
        checkout flow. See: https://stripe.com/docs/payments/checkout/set-up-a-subscription
        """

    def generate_setup_session(cancel_url,
                               success_url,
                               customer=None,
                               client_reference_id=None,
                               **kwargs):
        """
        Start a checkout session in setup mode to collect a payment
        intent. This session can be used, for example to create a
        payment intent for association with a customer, or with a
        subscription. Suggested kwargs are specified in the signature,
        additional kwargs are passed directly to stripe.Session.create

        The returned IStripeCheckoutSession.id can be used to launch a
        client side stripe checkout flow. See:
        https://stripe.com/docs/payments/checkout/subscriptions/update-payment-details
        """

class IStripeSetupIntent(interface.Interface):

    id = ValidTextLine(title='The intent identifier',
                       required=True)

class IStripePayments(interface.Interface):

    def get_setup_intent(intent):
        """
        Returns an IStripeSetupIntent for the corresponding id
        """

class IStripeEventData(interface.Interface):

    object = Attribute('The stripe object relevant to the event')

class IStripeEventWithChangedData(IStripeEventData):

    previous_attributes = Mapping(title='The names of the attributes that have changed, and their previous values',
                                  required=False)
    
class IStripeEvent(interface.Interface):
    """
    Represents a stripe event typically provided via webhook,
    but also potentially via the Events api.

    See also: https://stripe.com/docs/api/events/object
    """

    id = ValidTextLine(title='The event identifier',
                       required=True)

    api_version = ValidTextLine(title='The stripe api version used to render data',
                                required=True)

    type = ValidTextLine(title='The event type',
                                required=True)

    data = Object(IStripeEventData, title='The data relevant to this event')

# There are tens of events that could be triggered. We want to notify events so subscribers
# can register for their type. We start definning the types here we need now
# but perhaps we can autogenerate interfaces and implementations from a list of strings like
# checkout.session.completed?

class IStripeCheckoutSessionCompletedEvent(IStripeEvent):
    """
    Dispatched when a checkout session has completed.

    https://stripe.com/docs/api/events/types#event_types-checkout.session.completed
    """

class IStripeInvoicePaidEvent(IStripeEvent):
    """
    Dispatched when an invoice is paid.

    https://stripe.com/docs/api/events/types#event_types-invoice.paid
    """


def iface_name_for_event_type(type):
    return 'IStripe'+''.join(map(lambda x:x.capitalize(), type.split('.')))+'Event'
    
def iface_for_event(event):
    iface_name = iface_name_for_event_type(event.type)
    module = sys.modules[IStripeEvent.__module__]
    return getattr(module, iface_name, IStripeEvent)
