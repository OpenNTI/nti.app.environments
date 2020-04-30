from zope import interface

from zope.interface.interfaces import ObjectEvent

from nti.app.environments.models.interfaces import IHostKnownSitesEvent
from nti.app.environments.models.interfaces import ILMSSiteCreatedEvent
from nti.app.environments.models.interfaces import ILMSSiteUpdatedEvent
from nti.app.environments.models.interfaces import IHostLoadUpdatedEvent
from nti.app.environments.models.interfaces import ILMSSiteSetupFinished
from nti.app.environments.models.interfaces import ICustomerVerifiedEvent
from nti.app.environments.models.interfaces import ICSVLMSSiteCreatedEvent
from nti.app.environments.models.interfaces import ITrialLMSSiteCreatedEvent
from nti.app.environments.models.interfaces import ISupportLMSSiteCreatedEvent
from nti.app.environments.models.interfaces import ILMSSiteOwnerCompletedSetupEvent

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

@interface.implementer(ILMSSiteOwnerCompletedSetupEvent)
class SiteOwnerCompletedSetupEvent(ObjectEvent):

    site = alias('object')

    @property
    def completed_at(self):
        return self.site.setup_state.invite_accepted_date


@interface.implementer(ICustomerVerifiedEvent)
class CustomerVerifiedEvent(ObjectEvent):

    customer = alias('object')


@interface.implementer(IHostKnownSitesEvent)
class HostKnownSitesEvent(object):

    def __init__(self, host, site_ids):
        self.host = host
        self.site_ids = site_ids
