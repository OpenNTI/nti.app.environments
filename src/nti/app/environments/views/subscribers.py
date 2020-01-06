from zope import component

from nti.app.environments.models.interfaces import ILMSSiteCreatedEvent

from nti.app.environments.views.notification import SiteCreatedEmailNotifier

logger = __import__('logging').getLogger(__name__)


@component.adapter(ILMSSiteCreatedEvent)
def _site_created_event(event):
    notifier = SiteCreatedEmailNotifier(event.site)
    notifier.notify()
