import gevent

import transaction

from zope import component

from zope.lifecycleevent import IObjectAddedEvent
from zope.lifecycleevent import IObjectRemovedEvent

from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import IDedicatedEnvironment
from nti.app.environments.models.interfaces import ILMSSiteCreatedEvent
from nti.app.environments.models.interfaces import ILMSSiteUpdatedEvent

from nti.app.environments.interfaces import ITransactionRunner

from nti.app.environments.models.interfaces import ILMSSiteCreatedEvent
from nti.app.environments.models.interfaces import SITE_STATUS_PENDING

from nti.app.environments.tasks.interfaces import ICeleryApp

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

def _store_task_results(siteid, result):

    tx_runner = component.getUtility(ITransactionRunner)
    
    def _store():
        def _do_store():
            logger.info('Storing taskid %s for site %s', result, siteid)

        tx_runner(_do_store, retries=5, sleep=0.1)
        

    gevent.spawn(_store)

def _maybe_setup_site(success, app, siteid, client_name, dns_name):
    if not success:
        return
    
    try:
        result = app.tasks['init_env'].apply_async((siteid, client_name, dns_name))
        _store_task_results(siteid, result)
    except:
        logger.exception('Unable to queue site setup for %s' % siteid)

@component.adapter(ILMSSiteCreatedEvent)
def _setup_newly_created_site(event):
    site = event.site
    if site.status != SITE_STATUS_PENDING:
        return

    logger.info('Dispatching setup of site %s', site.id)

    app = component.getUtility(ICeleryApp)
    sid = site.id
    cname = site.client_name
    dns = site.dns_names[0]

    transaction.get().addAfterCommitHook(
            _maybe_setup_site, args=(app, sid, cname, dns), kws=None
    )   

