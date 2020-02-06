from zope import interface

from zope.interface.interfaces import ObjectEvent

from nti.app.environments.models.interfaces import ILMSSiteCreatedEvent
from nti.app.environments.models.interfaces import ILMSSiteUpdatedEvent
from nti.app.environments.models.interfaces import IHostLoadUpdatedEvent
from nti.app.environments.models.interfaces import ILMSSiteSetupFinished
from nti.app.environments.models.interfaces import ICustomerVerifiedEvent
from nti.app.environments.models.interfaces import ICSVLMSSiteCreatedEvent
from nti.app.environments.models.interfaces import ITrialLMSSiteCreatedEvent
from nti.app.environments.models.interfaces import ISupportLMSSiteCreatedEvent

from nti.property.property import alias


@interface.implementer(IHostLoadUpdatedEvent)
class HostLoadUpdatedEvent(object):

    def __init__(self, host):
        self.host = host


@interface.implementer(ILMSSiteCreatedEvent)
class SiteCreatedEvent(object):

    def __init__(self, site):
        self.site = site


@interface.implementer(ITrialLMSSiteCreatedEvent)
class TrialSiteCreatedEvent(SiteCreatedEvent):
    pass


@interface.implementer(ISupportLMSSiteCreatedEvent)
class SupportSiteCreatedEvent(SiteCreatedEvent):
    pass


@interface.implementer(ICSVLMSSiteCreatedEvent)
class CSVSiteCreatedEvent(SiteCreatedEvent):
    pass


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
