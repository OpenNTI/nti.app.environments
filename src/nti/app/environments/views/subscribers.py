import time
import gevent
import transaction

from datetime import datetime

from perfmetrics import statsd_client

from zope import component

from zope.lifecycleevent import IObjectAddedEvent
from zope.lifecycleevent import IObjectRemovedEvent

from nti.app.environments.api.hubspotclient import get_hubspot_client

from nti.app.environments.interfaces import ITransactionRunner
from nti.app.environments.interfaces import IOnboardingSettings

from nti.app.environments.models.interfaces import SITE_STATUS_PENDING
from nti.app.environments.models.interfaces import SITE_STATUS_ACTIVE
from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import ICustomer
from nti.app.environments.models.interfaces import ISetupStateSuccess
from nti.app.environments.models.interfaces import ILMSSiteCreatedEvent
from nti.app.environments.models.interfaces import ILMSSiteUpdatedEvent
from nti.app.environments.models.interfaces import IDedicatedEnvironment
from nti.app.environments.models.interfaces import ILMSSiteSetupFinished
from nti.app.environments.models.interfaces import IHostLoadUpdatedEvent
from nti.app.environments.models.interfaces import ICustomerVerifiedEvent
from nti.app.environments.models.interfaces import INewLMSSiteCreatedEvent
from nti.app.environments.models.interfaces import ITrialLMSSiteCreatedEvent

from nti.app.environments.models.customers import HubspotContact

from nti.app.environments.models.hosts import get_or_create_host

from nti.app.environments.models.sites import SetupStatePending
from nti.app.environments.models.sites import DedicatedEnvironment

from nti.app.environments.models.utils import get_sites_folder
from nti.app.environments.models.utils import get_hosts_folder
from nti.app.environments.models.utils import get_onboarding_root

from nti.app.environments.views.notification import SiteSetupEmailNotifier
from nti.app.environments.views.notification import SiteCreatedEmailNotifier
from nti.app.environments.views.notification import SiteSetupFailureEmailNotifier
from nti.app.environments.views.notification import SiteSetUpFinishedEmailNotifier

from nti.environments.management.interfaces import ICeleryApp
from nti.environments.management.interfaces import ISetupEnvironmentTask

from nti.externalization.interfaces import IObjectModifiedFromExternalEvent

logger = __import__('logging').getLogger(__name__)


@component.adapter(ICustomerVerifiedEvent)
def _customer_verified_event(event):
    customer = event.customer
    if customer.last_verified is not None:
        return

    # update last_verified
    _now = time.time()
    customer.last_verified = datetime.utcfromtimestamp(_now)
    customer.updateLastModIfGreater(_now)

    # upsert contact to hubspot
    client = get_hubspot_client()
    result = client.upsert_contact(customer.email,
                                   customer.name)
    if result is None:
        return

    if customer.hubspot_contact is None:
        logger.info("Setting the contact_vid for customer (%s) with %s.",
                    customer.email,
                    result['contact_vid'])
        customer.hubspot_contact = HubspotContact(contact_vid=result['contact_vid'])
    elif customer.hubspot_contact.contact_vid != result['contact_vid']:
        logger.info("Updating the contact_vid for customer (%s) from %s to %s.",
                    customer.email,
                    customer.hubspot_contact.contact_vid,
                    result['contact_vid'])
        customer.hubspot_contact.contact_vid = result['contact_vid']


@component.adapter(ITrialLMSSiteCreatedEvent)
def _site_created_event(event):
    notifier = SiteCreatedEmailNotifier(event.site)
    notifier.notify()


@component.adapter(ITrialLMSSiteCreatedEvent)
def _notify_owner_on_site_created(event):
    site = event.site
    if not site.owner or not site.dns_names:
        return

    if site.creator != site.owner.email:
        return

    logger.info("Notifying user to set up password for site : %s", site.dns_names[0])

    notifier = SiteSetupEmailNotifier(site)
    notifier.notify()


@component.adapter(ILMSSiteCreatedEvent)
def _update_host_load_on_site_added(event):
    site = event.site
    if IDedicatedEnvironment.providedBy(site.environment):
        site.environment.host.recompute_current_load()


@component.adapter(ILMSSite, IObjectRemovedEvent)
def _update_host_load_on_site_removed(site, unused_event):
    if IDedicatedEnvironment.providedBy(site.environment):
        site.environment.host.recompute_current_load(exclusive_site=site)


@component.adapter(ILMSSiteCreatedEvent)
def _update_stats_on_site_added(event):
    client = statsd_client()
    if client is not None:
        lms_site = event.site
        client.gauge('nti.onboarding.lms_site_count',
                     len(lms_site.__parent__))
        _update_site_status_stats(lms_site.__parent__.values())


@component.adapter(ILMSSite, IObjectRemovedEvent)
def _update_stats_on_site_removed(lms_site, unused_event):
    client = statsd_client()
    if client is not None:
        # This event is before removal
        client.gauge('nti.onboarding.lms_site_count',
                     len(lms_site.__parent__) - 1)
        all_sites = (x for x in lms_site.__parent__.values() if x != lms_site)
        _update_site_status_stats(all_sites)


def _get_site_stat_status_str(status):
    return 'nti.onboarding.lms_site_status_count.%s' % status.lower()


def _get_site_setup_stat_status_str(setup_state):
    return 'nti.onboarding.lms_site_setup_status_count.%s' % setup_state.state_name.lower()


def _update_site_status_stats(all_sites):
    client = statsd_client()
    buffer = []
    if client is not None:
        stat_to_count = {}
        for lms_site in all_sites:
            if lms_site.status:
                status_str = _get_site_stat_status_str(lms_site.status)
                if status_str not in stat_to_count:
                    stat_to_count[status_str] = 0
                stat_to_count[status_str] += 1
            if lms_site.setup_state:
                status_str = _get_site_setup_stat_status_str(lms_site.setup_state)
                if status_str not in stat_to_count:
                    stat_to_count[status_str] = 0
                stat_to_count[status_str] += 1
        for key, val in stat_to_count.items():
            client.gauge(key, val, buf=buffer)
    if buffer:
        client.sendbuf(buffer)


@component.adapter(ILMSSite, IObjectModifiedFromExternalEvent)
def _update_stats_on_site_updated(lms_site, event):
    if 'status' in event.external_value:
        _update_site_status_stats(lms_site.__parent__.values())


def _update_customer_stats(customer):
    client = statsd_client()
    if client is not None:
        client.gauge('nti.onboarding.customer_count', len(customer.__parent__))


@component.adapter(ICustomer, IObjectAddedEvent)
def _update_stats_on_customer_added(customer, unused_event):
    _update_customer_stats(customer)


@component.adapter(ICustomer, IObjectRemovedEvent)
def _update_stats_on_customer_removed(customer, unused_event):
    _update_customer_stats(customer)


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


@component.adapter(IHostLoadUpdatedEvent)
def _update_host_load_stats(host_load_event):
    client = statsd_client()
    if client is not None:
        host = host_load_event.host
        client.gauge('nti.onboarding.host_capacity.%s' % host.host_name,
                     host.capacity)
        client.gauge('nti.onboarding.host_current_load.%s' % host.host_name,
                     host.current_load)


# TODO The mechanics of actually dispatching the setup task
# and capturing the task for status and results fetching
# needs to be encapulated and moved out of here.
#
# Note the care taken around when we dispatch the task, and how
# we safely capture the result.

_marker = object()

def _store_task_results(siteid, task_results):
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
            logger.info('Storing task state %s for site %s', task_results, siteid)

            site = get_sites_folder(root)[siteid]

            assert site.setup_state is None

            app = component.getUtility(ICeleryApp)
            task = ISetupEnvironmentTask(app)

            pending = SetupStatePending()
            pending.task_state = task.save_task(task_results)
            pending.start_time = datetime.utcnow()
            site.setup_state = pending

        tx_runner(_do_store, retries=5, sleep=0.1)

    gevent.spawn(_store)


def _maybe_setup_site(success, app, siteid, client_name, dns_name, name, email):
    """
    On successful commit dispatch a task to setup the site. Note this happens in an after
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


@component.adapter(INewLMSSiteCreatedEvent)
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

    # Name is required by our setup scripts but not yet in the iface
    # Blow up here if we have no name
    assert name

    # If the transaction was successful we setup the site.
    transaction.get().addAfterCommitHook(
            _maybe_setup_site, args=(app, sid, cname, dns, name, email), kws=None
    )


def _email_on_setup_error(site):
    """
    On site setup error, email a notification to configured entities.
    """
    settings = component.getUtility(IOnboardingSettings)
    if not settings.get('site_setup_failure_notification_email'):
        return
    notifier = SiteSetupFailureEmailNotifier(site)
    notifier.notify()


def _store_site_setup_stats(setup_state):
    """
    Store site setup timings in statsd.
    """
    client = statsd_client()
    if client is not None and setup_state.elapsed_time:
        time_in_ms = setup_state.elapsed_time * 1000
        client.timing('nti.onboarding.lms_site_setup_time.%s' % setup_state.state_name,
                      time_in_ms)
        try:
            time_in_ms = setup_state.site_info.elapsed_time * 1000
            client.timing('nti.onboarding.lms_site_task_setup_time.%s' % setup_state.state_name,
                          time_in_ms)
        except (AttributeError, TypeError):
            pass


@component.adapter(ILMSSiteSetupFinished)
def _on_site_setup_finished(event):
    """
    On site setup finish, send out emails and update our site status. We also
    clean up and recompute host load here.
    """
    site = event.site
    _store_site_setup_stats(site.setup_state)
    _update_site_status_stats(site.__parent__.values())
    if not ISetupStateSuccess.providedBy(site.setup_state):
        _email_on_setup_error(site)
        return

    if site.status == SITE_STATUS_PENDING:
        site.status = SITE_STATUS_ACTIVE

    setup_info = site.setup_state.site_info
    if not setup_info.host:
        return

    logger.info('Associating site %s with host %s', site.id, setup_info.host)

    root = get_onboarding_root()
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


@component.adapter(ILMSSiteSetupFinished)
def _notify_user_for_site_setup_finished(event):
    """
    On site setup on behalf of another user, send the success
    email to our internal user (the creator).
    """
    site = event.site
    if not ISetupStateSuccess.providedBy(site.setup_state):
        return

    if not site.setup_state.site_info.admin_invitation:
        return

    if not site.owner or site.owner.email == site.creator:
        return

    logger.info("Notifying creator site is finished (%s) (%s)",
                site.id, site.creator)

    notifier = SiteSetUpFinishedEmailNotifier(site)
    notifier.notify()
