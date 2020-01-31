from zope import interface

from zope.interface.interfaces import ObjectEvent

from nti.app.environments.models.interfaces import ILMSSiteCreatedEvent
from nti.app.environments.models.interfaces import ILMSSiteUpdatedEvent
from nti.app.environments.models.interfaces import ILMSSiteSetupFinished
from nti.app.environments.models.interfaces import ICustomerVerifiedEvent

from nti.property.property import alias


@interface.implementer(ILMSSiteCreatedEvent)
class SiteCreatedEvent(object):

    def __init__(self, site):
        self.site = site


@interface.implementer(ILMSSiteUpdatedEvent)
class SiteUpdatedEvent(object):

    def __init__(self, site, original_values, external_values):
        self.site = site
        self.original_values = original_values
        self.external_values = external_values


@interface.implementer(ILMSSiteSetupFinished)
class SiteSetupFinishedEvent(object):

    def __init__(self, site):
        self.site = site


@interface.implementer(ICustomerVerifiedEvent)
class CustomerVerifiedEvent(ObjectEvent):

    customer = alias('object')
