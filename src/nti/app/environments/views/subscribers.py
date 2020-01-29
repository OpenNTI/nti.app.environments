import gevent

import time

import transaction

from celery.exceptions import TimeoutError

from zope import component

from zope.event import notify

from zope.lifecycleevent import IObjectAddedEvent
from zope.lifecycleevent import IObjectRemovedEvent

from nti.traversal.traversal import find_interface

from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import IDedicatedEnvironment
from nti.app.environments.models.interfaces import ILMSSiteCreatedEvent
from nti.app.environments.models.interfaces import ILMSSiteUpdatedEvent
from nti.app.environments.models.interfaces import ILMSSiteSetupFinished
from nti.app.environments.models.interfaces import IOnboardingRoot

from nti.environments.management.interfaces import ICeleryApp
from nti.environments.management.interfaces import ISetupEnvironmentTask

from nti.app.environments.interfaces import ITransactionRunner

from nti.app.environments.models.events import SiteSetupFinishedEvent

from nti.app.environments.models.interfaces import SITE_STATUS_PENDING
from nti.app.environments.models.interfaces import ISetupStatePending
from nti.app.environments.models.interfaces import ISetupStateSuccess

from nti.app.environments.models.hosts import get_or_create_host

from nti.app.environments.models.sites import DedicatedEnvironment
from nti.app.environments.models.sites import SetupStatePending
from nti.app.environments.models.sites import SetupStateSuccess
from nti.app.environments.models.sites import SetupStateFailure

from nti.app.environments.models.utils import get_sites_folder
from nti.app.environments.models.utils import get_hosts_folder

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

# TODO The mechanics of actually dispatching the setup task
# and capturing the task for status and results fetching
# needs to be encapulated and moved out of here.
#
# Note the care taken around when we dispatch the task, and how
# we safely capture the result.

_marker = object()

def _store_task_results(siteid, result):
    """
    Given a siteid, which should be a pending site, and a celery
    async result, associate the two. We spin up a greenlet that utilizes
    a TransactionLoop to associate the result (taskid) with the pending site
    in zodb.

    If this fails (including retries) we are left with a pending site that isn't
    linked to it's task. Again we will want to yell loudly and monitor for now.
    """

    tx_runner = component.getUtility(ITransactionRunner)
    
    def _store():
        def _do_store(root):
            logger.info('Storing task state %s for site %s', result, siteid)
            
            site = get_sites_folder(root)[siteid]

            assert site.setup_state is None

            app = component.getUtility(ICeleryApp)
            task = ISetupEnvironmentTask(app)

            pending = SetupStatePending()
            pending.task_state = task.save_task(result)
            site.setup_state = pending

        tx_runner(_do_store, retries=5, sleep=0.1)

        # Query for results every 5 seconds, waiting 1 second each time.
        # Give up after 4 hours

        interval = 5
        wait = 1
        maxwait = 4 * 60 * 60 # 4 hours This is way way longer than we need
        i = 0
        tresult = _marker
        while i < maxwait:
            logger.info('Checking status for site %s', siteid)

            try:
                # Propogate False causes exceptions to return instead of reraise here
                tresult = result.get(timeout=1, propagate=False)
                if result:
                    break
            except TimeoutError:
                pass

            time.sleep(interval)
            i += interval

        if tresult is _marker:
            # Uh oh, we never got a result.
            # In the context of the greenlet we just want to yell and exit.
            # In other contexts raising is probably more appropriate. This is effectively a timeout
            app = component.getUtility(ICeleryApp)
            task = ISetupEnvironmentTask(app)
            logger.error('Spin up task %s for site %s never completed. Abandoned task?', siteid, task.save_state(result))
            return

        # We have a result. now we need to update state
        logger.info('Setup for site %s finished successful=%s', siteid, result.successful())
        def _mark_complete(root):
            logger.info('Updating setup state for site %s finished successful=%s', siteid, result.successful())

            site = get_sites_folder(root)[siteid]

            assert ISetupStatePending.providedBy(site.setup_state)

            failed = isinstance(tresult, Exception)

            state = None
            if failed:
                state = SetupStateFailure()
                state.exception = tresult
            else:
                state = SetupStateSuccess()
                state.site_info = tresult

            assert state

            state.task_state = site.setup_state.task_state

            site.setup_state = state

            notify(SiteSetupFinishedEvent(site))

        # TODO what if this greenlet dies due to a restart.
        tx_runner(_mark_complete, retries=5, sleep=0.1)

    gevent.spawn(_store)

def _maybe_setup_site(success, app, siteid, client_name, dns_name, name, email):
    """
    On succesful commit dispatch a task to setup the site. Note this happens in an after
    commit hook and we are outside of the transaction. We must be very careful that we
    don't do anything here that we expect to happen transactionally. If this fails
    we're left with a site in the pending state that will need to be retriggered. We catch
    this by logging / monitoring for now. A failure here would mostly likely be a coding error
    or an error connecting to the celery broker.

    Unfortunately this isn't as simple as fire and forget. We need to transactionally capture
    the resulting taskid so that we a) know if things were kicked off and b) can fetch
    task status and results. After calling apply_async (i.e. the task is on the queue) we
    kick off a greenlet to store the results.

    We could use a strategy like repoze.sendmail to do this in a transactional way, using
    atomic filesystem renames, but we don't believe that complexity is warranted right now.
    """
    if not success:
        return
    
    try:
        result = ISetupEnvironmentTask(app)(siteid, client_name, dns_name, name, email)
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
    name = site.owner.name
    email = site.owner.email

    # If the transaction was successful we setup the site.
    transaction.get().addAfterCommitHook(
            _maybe_setup_site, args=(app, sid, cname, dns, name, email), kws=None
    )   

@component.adapter(ILMSSiteSetupFinished)
def _associate_site_to_host(event):
    site = event.site
    if not ISetupStateSuccess.providedBy(site.setup_state):
        return

    setup_info = site.setup_state.site_info
    if not setup_info.host:
        return
    
    logger.info('Associating site %s with host %s', site.id, setup_info.host)

    # We have to be careful here b/c we may not be running in a request. Typically
    # when we get the hosts folder we do so with the onboarding root, via the request.
    # we have no request here.
    root = find_interface(site, IOnboardingRoot)
    assert root

    hosts_folder = get_hosts_folder(onboarding_root=root)
    host = get_or_create_host(hosts_folder, setup_info.host)

    # We have our host, setup our dedicated environment.
    # TODO: we are assuming we are setup in a dedicated environment.
    # in the future we need to consult the setup_info for that
    env = DedicatedEnvironment(pod_id=site.id,
                               host=host,
                               load_factor=1)
    site.environment = env
    host.recompute_current_load()
    

    
