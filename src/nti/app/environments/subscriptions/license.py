import datetime

from zope import component
from zope import interface

from zope.annotation.interfaces import IAnnotations

from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import ISiteLicenseFactory
from nti.app.environments.models.interfaces import IRestrictedLicense
from nti.app.environments.models.interfaces import LICENSE_FREQUENCY_MONTHLY
from nti.app.environments.models.interfaces import LICENSE_FREQUENCY_YEARLY

from nti.app.environments.models.sites import StarterLicense
from nti.app.environments.models.sites import GrowthLicense

from nti.app.environments.stripe.interfaces import IStripeSubscription
from nti.app.environments.stripe.billing import MinimalStripeSubscription

STRIPE_SUBSCRIPTION_ANNOTATION_KEY = 'stripe_subscription'

@component.adapter(ILMSSite)
@interface.implementer(IStripeSubscription)
def stripe_subcription_factory(site, create=True):
    result = None
    annotations = IAnnotations(site)
    try:
        result = annotations[STRIPE_SUBSCRIPTION_ANNOTATION_KEY]
    except KeyError:
        if create:
            result = MinimalStripeSubscription()
            annotations[STRIPE_SUBSCRIPTION_ANNOTATION_KEY] = result
            result.__name__ = STRIPE_SUBSCRIPTION_ANNOTATION_KEY
            result.__parent__ = site
    return result

_FREQUENCY_MAP = {
    'month': LICENSE_FREQUENCY_MONTHLY,
    'year': LICENSE_FREQUENCY_YEARLY
}

def make_factory(factory):

    def _f(subscription):
        license = factory()
        license.start_date = datetime.datetime.utcfromtimestamp(subscription.start_date)
        if IRestrictedLicense.providedBy(license):
            license.seats = subscription.quantity
            license.frequency = _FREQUENCY_MAP.get(subscription.plan.interval)
        return license

    return _f

starter_factory = make_factory(StarterLicense)
growth_factory = make_factory(GrowthLicense)

