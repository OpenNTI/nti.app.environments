from zope import interface

from nti.app.environments.models.interfaces import ILMSSiteCreatedEvent
from nti.app.environments.models.interfaces import ILMSSiteUpdatedEvent


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
