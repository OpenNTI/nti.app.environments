from zope import component

from nti.app.environments.models.interfaces import ILMSSiteCreatedEvent

from nti.app.environments.interfaces import ISiteCreatedNotifier

logger = __import__('logging').getLogger(__name__)


@component.adapter(ILMSSiteCreatedEvent)
def _site_created_event(event):
    notifiers = component.subscribers((event.site,), ISiteCreatedNotifier)
    for notifier in notifiers:
        notifier.notify()
