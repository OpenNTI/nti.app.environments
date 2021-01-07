import datetime

from stripe.error import InvalidRequestError

from zope import component

from nti.app.environments.models.interfaces import SITE_STATUS_ACTIVE
from nti.app.environments.models.interfaces import ISiteLicenseFactory
from nti.app.environments.models.interfaces import ITrialLicense
from nti.app.environments.models.interfaces import ILMSSite

from nti.app.environments.stripe.interfaces import IStripeKey
from nti.app.environments.stripe.interfaces import IStripeCustomer
from nti.app.environments.stripe.interfaces import IStripeCheckoutSessionCompletedEvent
from nti.app.environments.stripe.interfaces import IStripeInvoicePaidEvent
from nti.app.environments.stripe.interfaces import IStripePayments
from nti.app.environments.stripe.interfaces import IStripeSubscription
from nti.app.environments.stripe.interfaces import IStripeSubscriptionBilling

from nti.app.environments.subscriptions.interfaces import ICheckoutSessionStorage

from nti.app.environments.models.utils import get_onboarding_root

logger = __import__('logging').getLogger(__name__)

@component.adapter(IStripeInvoicePaidEvent)
def _invoice_paid(event):
    """
    Process an invoice paid event by finding the site associated with the
    subscription and moving the end date forward to the period end
    """
    invoice = event.data.object

    # We only care about invoices tied to subscriptions
    # with a period end date. We ignore other invoices as we know they
    # wont be ones we care about
    if not invoice.subscription:
        logger.debug('Ignoring invoice.paid event for %s without an associated subscription', invoice.id)
        return

    # reify the subscription if needed
    subscription = invoice.subscription
    if not IStripeSubscription.providedBy(subscription):
        try:
            billing = IStripeSubscriptionBilling(component.getUtility(IStripeKey))
            subscription = billing.get_subscription(subscription)
        except InvalidRequestError:
            logger.exception('Unable to reify stripe subscription %s for %s', invoice.subscription, invoice.id)
            return
    

    site = component.queryAdapter(subscription, ILMSSite)
    if site is None or site.status != SITE_STATUS_ACTIVE:
        logger.debug('Unable to find site associated with subscription %s', subscription.id)
        return

    # We found an active site associated with the subscription tied to this invoice
    # Roll the end date on the associated license to the the subscription's current_period_end.
    # Stripe guide implies adding wiggle room for failed payment retries, etc. That's probably
    # a good idea if we are automating access based on this date. Right now we use it to drive
    # alerts and dashboards and we probably want attention drawn to late/failed payments so we
    # provide no wiggle room.
    new_end_date = datetime.datetime.utcfromtimestamp(subscription.current_period_end)
    logger.info('Updating %s license end date from %s to %s because of paid invoice %s',
                site.id,
                site.license.end_date,
                new_end_date,
                invoice.id)
    site.license.end_date = new_end_date


def _do_handle_subscription_session_completed(session, checkout):
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
                    logger.warn('No plan associated with subscription %s. Not updating license', stripe_subscription_id)
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


def _do_handle_setup_session_completed(session, checkout):
    payments = IStripePayments(component.getUtility(IStripeKey))
    
    setup_intent_id = session.setup_intent
    setup_intent = payments.get_setup_intent(setup_intent_id)

    payment_method_id = setup_intent.payment_method

    # We have two options here. We can update the default invoice payment
    # method for the customer, or we can update the default payment method
    # on the subscription
    # https://stripe.com/docs/payments/checkout/subscriptions/update-payment-details#set-default-payment-method

    billing = IStripeSubscriptionBilling(component.getUtility(IStripeKey))

    # If our SetupIntent has a subscription_id entry in the metadata
    # we will update the payment info on the subscription, otherwise
    # we update the default payment for the customer on all future invoices.
    subscription_id = setup_intent.metadata.get('subscription_id')
    customer_id = setup_intent.customer
    if subscription_id:
        logger.info('Updating default payment method for subscription %s', subscription_id)
        billing.update_subscription_payment_method(subscription_id, payment_method_id)
    elif customer_id:
        logger.info('Updating default payment method for customer %s', customer_id)
        billing.update_customer_default_payment_method(customer_id, payment_method_id)
    else:
        logger.warn('Unknown target for setup intent %s', setup_intent_id)

    

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

    if session.mode == 'subscription':
        logger.info('Handling %s checkout session for %s', session.mode, session.client_reference_id)
        _do_handle_subscription_session_completed(session, checkout)
    elif session.mode == 'setup':
        logger.info('Handling %s checkout session for %s', session.mode, session.client_reference_id)
        _do_handle_setup_session_completed(session, checkout)
    else:
        logger.warn('Received an unexpected checkout session mode %s for %s', session.mode, session.client_reference_id)
    
    
