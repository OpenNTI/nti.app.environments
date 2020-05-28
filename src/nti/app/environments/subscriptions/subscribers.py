import datetime

from zope import component

from nti.app.environments.models.interfaces import ISiteLicenseFactory
from nti.app.environments.models.interfaces import ITrialLicense

from nti.app.environments.stripe.interfaces import IStripeKey
from nti.app.environments.stripe.interfaces import IStripeCustomer
from nti.app.environments.stripe.interfaces import IStripeCheckoutSessionCompletedEvent
from nti.app.environments.stripe.interfaces import IStripeSubscription
from nti.app.environments.stripe.interfaces import IStripeSubscriptionBilling

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
    stripe_subscription_id = session.subscription
    logger.info('Customer %s completed checkout session %s. New subscription is %s',
                stripe_customer_id, session.client_reference_id, stripe_subscription_id)

    # Associate the stripe customer id to our customer
    customer = checkout.customer
    if customer is not None:
        logger.info('Linking stripe customer %s to %s', stripe_customer_id, customer.email)
        stripe_customer = IStripeCustomer(customer)
        if stripe_customer.customer_id and stripe_customer.customer_id != stripe_customer_id:
            logger.warn('Aborting linking because stripe customer id mismatch. %s != %s', stripe_customer.customer_id, stripe_customer_id)
        else:
            stripe_customer.customer_id = stripe_customer_id

    site = checkout.site
    if site is not None:
        logger.info('Linking stripe subscription %s to %s', stripe_subscription_id, site.id)
        stripe_subscription = IStripeSubscription(site)
        if stripe_subscription.id:
            logger.warn('Aborting linking %s because %s already linked to subscription %s',
                        stripe_subscription_id, site.id, stripe_subscription.id)
        else:
            stripe_subscription.id = stripe_subscription_id
    
            # adjust the license accordingly.
            if ITrialLicense.providedBy(site.license):

                # Look through the subscription for the plan, and look
                # for an ILicenseFactory registered as as a named
                # utility for the plan id, followed by the product
                # id. If one is found, call it and set the license on
                # the site.  NOTE we only deal with subscriptions for
                # single items
                billing = IStripeSubscriptionBilling(component.getUtility(IStripeKey))
                subscription = billing.get_subscription(stripe_subscription_id)
                plan = subscription.plan
                if plan is None:
                    logger.warn('No plan associated with subscription %s. Not updating license')
                else:
                    factory = component.queryUtility(ISiteLicenseFactory, name=plan.id)
                    if factory is None:
                        factory = component.queryUtility(ISiteLicenseFactory, name=plan.product)
                    if factory is None:
                        logger.warn('No license factory found for subscription %s. License won\'t be updated', subscription.id)
                    else:
                        site.license = factory(subscription)
                        logger.info('Updated site license to %s', site.license)
            else:
                logger.info('Skipping license update because site is not on a trial')
                        

            
    

    # notify internally that we had a payment
