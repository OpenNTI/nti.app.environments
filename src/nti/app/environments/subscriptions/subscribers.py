import datetime

from zope import component

from nti.app.environments.stripe.interfaces import IStripeCustomer
from nti.app.environments.stripe.interfaces import IStripeCheckoutSessionCompletedEvent

from nti.app.environments.subscriptions.interfaces import ICheckoutSessionStorage

from nti.app.environments.models.utils import get_onboarding_root

logger = __import__('logging').getLogger(__name__)

@component.adapter(IStripeCheckoutSessionCompletedEvent)
def _checkout_session_completed(event):
    session = event.data.object
    
    checkout_storage = ICheckoutSessionStorage(get_onboarding_root())
    checkout = checkout_storage.find_session(session.client_reference_id)

    if checkout is None:
        logger.warn('No checkout info for %s', session.client_reference_id)
        return

    if checkout.completed:
        logger.debug('Checkout session % already handled', session.client_reference_id)
        return

    checkout.completed = datetime.datetime.utcnow()

    
    stripe_customer_id = session.customer
    stripe_subscription = session.subscription
    logger.info('Customer %s completed checkout session %s. New subscription is %s',
                stripe_customer_id, session.client_reference_id, stripe_subscription)

    # Associate the stripe customer id to our customer
    customer = checkout.customer
    if customer is not None:
        stripe_customer = IStripeCustomer(customer)
        if stripe_customer.customer_id and stripe_customer.customer_id != stripe_customer_id:
            logger.warn('Stripe customer id mismatch. %s != %s', stripe_customer.customer_id, stripe_customer_id)
        else:
            stripe_customer.customer_id = stripe_customer_id
    
    # adjust the license accordingly.

    # notify internally that we had a payment
