from zope import component

from zope.lifecycleevent import IObjectAddedEvent
from zope.lifecycleevent import IObjectRemovedEvent

from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import IDedicatedEnvironment
from nti.app.environments.models.interfaces import ILMSSiteCreatedEvent
from nti.app.environments.models.interfaces import ILMSSiteUpdatedEvent

from nti.app.environments.views.notification import SiteCreatedEmailNotifier

logger = __import__('logging').getLogger(__name__)


@component.adapter(ILMSSiteCreatedEvent)
def _site_created_event(event):
    notifier = SiteCreatedEmailNotifier(event.site)
    notifier.notify()


@component.adapter(ILMSSite, IObjectAddedEvent)
def _update_host_load_on_site_added(site, unused_event):
    if IDedicatedEnvironment.providedBy(site.environment):
        site.environment.host.recompute_current_load()


@component.adapter(ILMSSite, IObjectRemovedEvent)
def _update_host_load_on_site_removed(site, unused_event):
    if IDedicatedEnvironment.providedBy(site.environment):
        site.environment.host.recompute_current_load(exclusive_site=site)


@component.adapter(ILMSSiteUpdatedEvent)
def _update_host_load_on_site_environment_updated(event):
    if 'environment' not in event.external_values:
        return

    original_env = event.original_values['environment']
    external_env = event.external_values['environment']

    old_host = original_env.host if IDedicatedEnvironment.providedBy(original_env) else None
    old_load = original_env.load_factor if IDedicatedEnvironment.providedBy(original_env) else None
    new_host = external_env.host if IDedicatedEnvironment.providedBy(external_env) else None
    new_load = external_env.load_factor if IDedicatedEnvironment.providedBy(external_env) else None

    if old_host == new_host and old_load == new_load:
        return

    for host in set([old_host, new_host]):
        if host:
            host.recompute_current_load()
