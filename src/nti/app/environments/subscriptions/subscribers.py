from zope import component

from nti.app.environments.stripe.interfaces import IStripeCheckoutSessionCompletedEvent

logger = __import__('logging').getLogger(__name__)

@component.adapter(IStripeCheckoutSessionCompletedEvent)
def _checkout_session_completed(event):
    logger.info('Checkout session completed for %s', event.data.object.customer)
    # TODO associate customer from event with our customer
    
    # adjust the license accordingly.

    # notify internally that we had a payment
