import datetime
from datetime import timezone

from zope import component
from zope import interface

from zope.annotation.interfaces import IAnnotations

from nti.schema.eqhash import EqHash

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured

from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import ISiteLicenseFactory
from nti.app.environments.models.interfaces import IRestrictedLicense
from nti.app.environments.models.interfaces import LICENSE_FREQUENCY_MONTHLY
from nti.app.environments.models.interfaces import LICENSE_FREQUENCY_YEARLY

from nti.app.environments.models.sites import StarterLicense
from nti.app.environments.models.sites import GrowthLicense

from nti.app.environments.models.utils import get_onboarding_root
from nti.app.environments.models.utils import get_sites_folder

from nti.app.environments.stripe.interfaces import IStripeSubscription
from nti.app.environments.stripe.billing import MinimalStripeSubscription

from .interfaces import IPrice
from .interfaces import IProduct

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
        if subscription.current_period_end:
            license.end_date = datetime.datetime.utcfromtimestamp(subscription.current_period_end)

        if IRestrictedLicense.providedBy(license):
            license.seats = subscription.quantity
            license.frequency = _FREQUENCY_MAP.get(subscription.plan.interval)
        return license

    return _f

starter_factory = make_factory(StarterLicense)
growth_factory = make_factory(GrowthLicense)

@component.adapter(IStripeSubscription)
@interface.implementer(ILMSSite)
def _lookup_site_for_subscription(subscription):
    # Find the site associated with the subscription. We probably
    # want an index for this at some point, right now we have few sites (hundreds)
    # and this is infrequent so we can just iterate.
    for site in get_sites_folder(get_onboarding_root()).values():
        # look for the IStripeSubscription, we don't use the adapter
        # as we don't want to optimistically create these objects
        sub = stripe_subcription_factory(site, create=False)
        if sub and sub.id == subscription.id:
            return site
    return None

@EqHash('id')
@interface.implementer(IPrice)
class RegistryBackedPrice(SchemaConfigured):

    createDirectFieldProperties(IPrice, omit=('product'))

    _prodcut_id = None

    def __init__(self, *args, **kwargs):
        product = kwargs.pop('product', None)
        if product:
            self._product_id = getattr(product, 'id', product)
        super(RegistryBackedPrice, self).__init__(*args, **kwargs)

    @property
    def product(self):
        return component.queryUtility(IProduct, name=self._product_id) if self._product_id else None

    
@EqHash('id')
@interface.implementer(IProduct)
class RegistryBackedProduct(SchemaConfigured):

    createDirectFieldProperties(IProduct, omit=('monthly_plan', 'yearly_plan'))

    _monthly_id = None
    _yearly_id = None

    def __init__(self, *args, **kwargs):
        monthly = kwargs.pop('monthly_price', None)
        yearly = kwargs.pop('yearly_price', None)
        
        if monthly:
            self._monthly_id = getattr(monthly, 'id', monthly)

        if yearly:
            self._yearly_id = getattr(yearly, 'id', yearly)
        super(RegistryBackedProduct, self).__init__(*args, **kwargs)

    @property
    def monthly_price(self):
        return component.queryUtility(IPrice, name=self._monthly_id) if self._monthly_id else None

    @property
    def yearly_price(self):
        return component.queryUtility(IPrice, name=self._yearly_id) if self._yearly_id else None



