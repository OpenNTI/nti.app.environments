from zope import interface

from nti.app.environments.models.interfaces import ILMSSiteCreatedEvent


@interface.implementer(ILMSSiteCreatedEvent)
class SiteCreatedEvent(object):

    def __init__(self, site):
        self.site = site
