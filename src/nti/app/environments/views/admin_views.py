import time
import urllib.parse
from urllib.parse import quote_plus

from datetime import datetime
from datetime import timedelta

from pyramid.config import not_

from pyramid.view import view_config
from pyramid.view import view_defaults

from pyramid import httpexceptions as hexc

from stripe.error import InvalidRequestError

from zope.cachedescriptors.property import Lazy

from zope import component

from zope.securitypolicy.interfaces import Allow as zopeAllow
from zope.securitypolicy.interfaces import IPrincipalRoleManager

from nti.common.string import is_true

from nti.mailer.interfaces import ITemplatedMailer

from nti.environments.management.interfaces import ISettings

from nti.app.environments.api.interfaces import ISiteUsageUpdater

from nti.app.environments.api.siteinfo import NTClient

from nti.app.environments.hubspot import get_hubspot_profile_url

from nti.app.environments.auth import ACT_ADMIN
from nti.app.environments.auth import ACT_READ
from nti.app.environments.auth import ACT_UPDATE
from nti.app.environments.auth import ACT_DELETE
from nti.app.environments.auth import ACT_CREATE
from nti.app.environments.auth import ACT_AUTOMATED_REPORTS
from nti.app.environments.auth import ACT_EDIT_SITE_LICENSE
from nti.app.environments.auth import ACT_EDIT_SITE_ENVIRONMENT
from nti.app.environments.auth import ACT_REQUEST_TRIAL_SITE
from nti.app.environments.auth import ACT_SITE_LOGIN
from nti.app.environments.auth import ACT_SITE_JWT_TOKEN
from nti.app.environments.auth import ADMIN_ROLE
from nti.app.environments.auth import ACCOUNT_MANAGEMENT_ROLE
from nti.app.environments.auth import OPS_ROLE

from nti.app.environments.interfaces import ISiteDomainPolicy
from nti.app.environments.interfaces import IOnboardingSettings
from nti.app.environments.interfaces import ISiteLinks

from nti.app.environments.models.adapters import get_site_usage

from nti.app.environments.models.interfaces import ICustomer
from nti.app.environments.models.interfaces import ISharedEnvironment
from nti.app.environments.models.interfaces import IDedicatedEnvironment
from nti.app.environments.models.interfaces import IOnboardingRoot
from nti.app.environments.models.interfaces import ICustomersContainer
from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import ILMSSitesContainer
from nti.app.environments.models.interfaces import IRestrictedScorm
from nti.app.environments.models.interfaces import ISetupStatePending
from nti.app.environments.models.interfaces import ISetupStateSuccess
from nti.app.environments.models.interfaces import ISetupStateFailure
from nti.app.environments.models.interfaces import SITE_STATUS_OPTIONS
from nti.app.environments.models.interfaces import SHARED_ENV_NAMES
from nti.app.environments.models.interfaces import checkEmailAddress
from nti.app.environments.models.interfaces import LICENSE_FREQUENCY_OPTIONS
from nti.app.environments.models.interfaces import ITrialLicense
from nti.app.environments.models.interfaces import IStarterLicense
from nti.app.environments.models.interfaces import IGrowthLicense
from nti.app.environments.models.interfaces import IEnterpriseLicense
from nti.app.environments.models.interfaces import IRestrictedLicense
from nti.app.environments.models.interfaces import ISiteUsage
from nti.app.environments.models.interfaces import SITE_STATUS_ACTIVE
from nti.app.environments.models.interfaces import SITE_STATUS_PENDING

from nti.app.environments.models.utils import get_sites_folder
from nti.app.environments.models.utils import get_hosts_folder

from nti.app.environments.resources import DashboardsResource
from nti.app.environments.resources import RolesResource

from nti.app.environments.common import formatDateToLocal

from nti.app.environments.pendo.interfaces import IPendoAccount

from nti.app.environments.stripe.interfaces import IStripeCustomer
from nti.app.environments.stripe.interfaces import IStripeKey
from nti.app.environments.stripe.interfaces import IStripeSubscription
from nti.app.environments.stripe.interfaces import IStripeSubscriptionBilling

from nti.app.environments.utils.nti_grab_site_usage import _do_fetch_site_usage

from nti.app.environments.tasks.setup import query_setup_state

from nti.app.environments.views.base import BaseTemplateView
from nti.app.environments.views.base import BaseView
from nti.app.environments.views.base import TableViewMixin

from nti.app.environments.views.base_csv import CSVBaseView

from nti.app.environments.views._table_utils import CustomersTable
from nti.app.environments.views._table_utils import RolePrincipalsTable
from nti.app.environments.views._table_utils import SitesTable
from nti.app.environments.views._table_utils import DashboardLicenseAuditTable
from nti.app.environments.views._table_utils import DashboardTrialSitesTable
from nti.app.environments.views._table_utils import DashboardRenewalsTable
from nti.app.environments.views._table_utils import make_specific_table

from nti.app.environments.views.utils import raise_json_error

from nti.traversal.traversal import find_interface

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields


ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL

_ALERTS_DEDICATED_ENVIRONMENT_DASHBOARD = 'https://alerts.nextthought.io/d/q2qY3CGGk/lms-dedicated-environment'

logger = __import__('logging').getLogger(__name__)

def _host_options(onboarding):
    hosts = get_hosts_folder(onboarding)
    return [(x.id, "{} ({}/{})".format(x.host_name, x.current_load or 0, x.capacity)) for x in hosts.values()]


@view_config(renderer='../templates/admin/customers.pt',
             request_method='GET',
             context=ICustomersContainer,
             permission=ACT_READ,
             name='list')
class CustomersListView(BaseTemplateView, TableViewMixin):

    def __call__(self):
        table = make_specific_table(CustomersTable, self.context, self.request)
        has_create_perm = self.request.has_permission(ACT_CREATE, self.context)
        return {'table': table,
                'creation_url': self.request.resource_url(self.context) if has_create_perm else None,
                'create_via_hubspot': self.request.resource_url(self.context, '@@hubspot') \
                                            if has_create_perm and self._hubspot_client is not None else None,
                'is_deletion_allowed': self._is_deletion_allowed(table)}


@view_config(renderer='../templates/admin/customer_detail.pt',
             request_method='GET',
             context=ICustomer,
             permission=ACT_READ,
             name='details')
class CustomerDetailView(BaseTemplateView, TableViewMixin):

    def _get_sites_folder(self):
        onboarding_root = find_interface(self.context, IOnboardingRoot)
        return get_sites_folder(onboarding_root)

    def _format_hubspot(self, contact=None):
        return {'contact_vid': contact.contact_vid,
                'profile_url': get_hubspot_profile_url(contact.contact_vid)}

    def __call__(self):
        sites = self._get_sites_folder()
        table = make_specific_table(SitesTable, sites, self.request, email=self.context.email)
        return {'customers_list_link': self.request.resource_url(self.context.__parent__, '@@list'),
                'customer':
                {
                    'customer': self.context,

                    'hubspot': self._format_hubspot(self.context.hubspot_contact) if self.context.hubspot_contact else None,
                    'stripe': IStripeCustomer(self.context)
                },
                'table': table,
                'is_deletion_allowed': self._is_deletion_allowed(table),
                'format_date': formatDateToLocal}


@view_config(
             renderer='../templates/admin/sites.pt',
             request_method='GET',
             context=ILMSSitesContainer,
             permission=ACT_READ,
             name='list')
class SitesListView(BaseTemplateView, TableViewMixin):

    def __call__(self):
        table = make_specific_table(SitesTable, self.context, self.request)
        return {'table': table,
                'creation_url': self.request.resource_url(self.context) if self.request.has_permission(ACT_CREATE, self.context) else None,
                'sites_upload_url': self.request.resource_url(self.context, '@@upload_sites') if self.request.has_permission(ACT_CREATE, self.context) else None,
                'sites_export_url': self.request.resource_url(self.context, '@@export_sites'),
                'trial_site_request_url': self.request.resource_url(self.context, '@@request_trial_site') if self.request.has_permission(ACT_REQUEST_TRIAL_SITE, self.context) else None,
                'site_status_options': SITE_STATUS_OPTIONS,
                'env_shared_options': SHARED_ENV_NAMES,
                'hosts_options': _host_options(self._onboarding_root),
                'license_frequency_options': LICENSE_FREQUENCY_OPTIONS}


@view_config(renderer='rest',
             request_method='GET',
             context=ILMSSite,
             permission=ACT_READ,
             name='pendo_account_link')
class SitePendoAccountDetails(BaseTemplateView):

    def __call__(self):
        if self.context.status != SITE_STATUS_ACTIVE:
            raise hexc.HTTPNotFound()

        pendo = IPendoAccount(self.context)
        location = pendo.account_web_url

        return hexc.HTTPSeeOther(location=location)

@view_config(renderer='../templates/admin/site_detail.pt',
             request_method='GET',
             context=ILMSSite,
             permission=ACT_READ,
             name='details')
class SiteDetailView(BaseTemplateView):

    _shared_env_names = {
        'prod': 'prod',
        'hrpros': 'prod_hrpros',
        'assoc': 'prod_assoc',
        'alpha': 'alpha_v3'
    }

    def format_date(self, datetime):
        return formatDateToLocal(datetime)

    def format_currency(self, amount):
        # TODO assuming usd here
        return "$%.2f" % round(amount/100,2)

    def _site_extra_info(self):
        if self.context.status != SITE_STATUS_ACTIVE:
            return None

        nt_client = NTClient(self.context)
        return nt_client.fetch_site_info()

    def _format_license(self, lic):
        edit_link = self.request.resource_url(self.context, '@@license') if self.request.has_permission(ACT_EDIT_SITE_LICENSE, self.context) else None
        result = {'type': lic.license_name,
                  'start_date': formatDateToLocal(lic.start_date),
                  'end_date': formatDateToLocal(lic.end_date),
                  'edit_link': edit_link,
                  'lastModified': formatDateToLocal(lic.lastModified)}
        if ITrialLicense.providedBy(lic) or IEnterpriseLicense.providedBy(lic):
            result.update({'end_date': formatDateToLocal(lic.end_date)})
            return result
        elif IStarterLicense.providedBy(lic) or IGrowthLicense.providedBy(lic):
            result.update({'frequency': lic.frequency,
                           'seats': lic.seats,
                           'additional_instructor_seats': lic.additional_instructor_seats})
            return result
        raise ValueError("Unknown license type.")

    @Lazy
    def _settings(self):
        return component.getUtility(IOnboardingSettings)

    def _splunk_link(self, env):
        tpl = 'https://splunk.nextthought.com/en-US/app/search/search?q=%s'
        query = None
        if ISharedEnvironment.providedBy(env):
            name = self._shared_env_names.get(env.name)
            query = 'search index="%s" earliest=-1d' % name if name else None
        elif IDedicatedEnvironment.providedBy(env):
            index = self._settings.get('splunk_dedicated_environment_index', 'dedicated_environments')
            query = f'search index="{index}" host="{self.context.id}.nti" earliest=-1d'
        return tpl % urllib.parse.quote(query, safe='') if query else None

    def _monitor_link(self, env):
        if IDedicatedEnvironment.providedBy(env):
            base = self._settings.get('monitoring_dedicated_environment_dashboard',
                                      _ALERTS_DEDICATED_ENVIRONMENT_DASHBOARD)
            params = {
                'refresh': '10s',
                'orgId': "1",
                'var-Site': self.context.id
            }
            url_parts = list(urllib.parse.urlparse(base))
            query = dict(urllib.parse.parse_qsl(url_parts[4]))
            query.update(params)
            url_parts[4] = urllib.parse.urlencode(query)
            return urllib.parse.urlunparse(url_parts)
        else:
            return None

    def _format_env(self, env=None):
        formatted_env = {'env': env,
                         'lastModified': formatDateToLocal(env.lastModified),
                         'splunk_link': self._splunk_link(env),
                         'monitor_link': self._monitor_link(env)}

        if self.context.status == SITE_STATUS_ACTIVE:
            formatted_env['pendo_account_link'] = self.request.resource_url(self.context, '@@pendo_account_link')

        if ISharedEnvironment.providedBy(env):
            formatted_env['type'] = 'shared'
        elif IDedicatedEnvironment.providedBy(env):
            formatted_env['type'] = 'dedicated'
        else:
            raise ValueError('Unknown environment type.')

        return formatted_env

    def _format_owner(self, owner=None):
        return {'owner': owner,
                'detail_url': self.request.resource_url(owner, '@@details') if owner else None}

    def _format_parent_site(self, parent):
        return {'id': parent.id,
                'dns_names': parent.dns_names,
                'detail_url': self.request.resource_url(parent, '@@details')}

    def _format_usage(self, context):
        usage = get_site_usage(context)
        return {'usage': usage,
                'historical': 'https://alerts.nextthought.io/d/KrY-wPRGk/site-usage?var-Site=%s' % context.id,
                'lastModified': formatDateToLocal(usage.lastModified) if usage else None}

    def _format_setup_state(self, state):
        result = {'state_name': state.state_name,
                  'start_time': formatDateToLocal(state.start_time) if state.start_time else '',
                  'end_time': formatDateToLocal(state.end_time) if state.end_time else '',
                  'elapsed_time': (state.end_time - state.start_time).total_seconds() if state.start_time and state.end_time else ''}

        if ISetupStateSuccess.providedBy(state):
            site_info = state.site_info
            result['task_start_time'] = formatDateToLocal(site_info.start_time) if site_info.start_time else ''
            result['task_end_time'] = formatDateToLocal(site_info.end_time) if site_info.end_time else ''
            result['task_elapsed_time'] = site_info.elapsed_time if site_info.elapsed_time is not None else ''
            if state.invite_accepted_date:
                result['invite_accepted_date'] = formatDateToLocal(state.invite_accepted_date)
                result['invitation_status'] = 'accepted'
            else:
                result['invitation_status'] = 'pending' if state.invitation_active else 'inactive'
        elif ISetupStateFailure.providedBy(state):
            result['exception'] = str(state.exception)
        elif not ISetupStatePending.providedBy(state):
            raise_json_error(hexc.HTTPUnprocessableEntity,
                             "Unknown setup_state: {}.".format(state))
        return result

    def _format_stripe(self):
        sub = IStripeSubscription(self.context, None)
        if sub is None or not sub.id:
            return None

        billing = IStripeSubscriptionBilling(component.queryUtility(IStripeKey), None)
        if billing is None:
            return None

        try:
            sub = billing.get_subscription(sub)
            upcoming = billing.get_upcoming_invoice(sub)
        except InvalidRequestError:
            logger.exception('Unable to get upcoming invoice')
            upcoming = None

        return {
            'subscription': sub,
            'upcoming_invoice': upcoming
        }

    def __call__(self):
        request = self.request
        extra_info = self._site_extra_info() or {}

        # may have side effects.
        query_setup_state([self.context],
                          request=self.request,
                          side_effects=True)

        return {'sites_list_link': self.request.resource_url(self.context.__parent__, '@@list'),
                'env_shared_options': SHARED_ENV_NAMES,
                'site_status_options': SITE_STATUS_OPTIONS,
                'hosts_options': _host_options(self._onboarding_root),
                'license_frequency_options': LICENSE_FREQUENCY_OPTIONS,
                'site': {'created': formatDateToLocal(self.context.created),
                         'ds_site_id': self.context.ds_site_id,
                         'creator': self.context.creator,
                         'owner': self._format_owner(self.context.owner),
                         'site_id': self.context.id,
                         'status': self.context.status,
                         'dns_names': self.context.dns_names,
                         'license': self._format_license(self.context.license),
                         'stripe': self._format_stripe(),
                         'environment': self._format_env(self.context.environment) if self.context.environment else None,
                         'environment_edit_link': request.resource_url(self.context, '@@environment') if request.has_permission(ACT_EDIT_SITE_ENVIRONMENT, self.context) else None,
                         'site_login_link': request.resource_url(self.context, '@@login') if request.has_permission(ACT_SITE_LOGIN, self.context) else None,
                         'generate_token_link': request.resource_url(self.context, '@@generate_token') if request.has_permission(ACT_SITE_JWT_TOKEN, self.context) else None,
                         'client_name': self.context.client_name,
                         'site_edit_link': request.resource_url(self.context) if request.has_permission(ACT_UPDATE, self.context) else None,
                         'site_delete_link': request.resource_url(self.context) if request.has_permission(ACT_DELETE, self.context) else None,
                         'lastModified': formatDateToLocal(self.context.lastModified),
                         'parent_site': self._format_parent_site(self.context.parent_site) if self.context.parent_site else None,
                         'usage': self._format_usage(self.context),
                         'setup_state': self._format_setup_state(self.context.setup_state) if self.context.setup_state else None,
                         **extra_info}}


@view_config(renderer='../templates/admin/request_site.pt',
             request_method='GET',
             context=ILMSSitesContainer,
             permission=ACT_REQUEST_TRIAL_SITE,
             name='request_trial_site')
class SiteRequestView(BaseTemplateView):

    def __call__(self):
        return {
            'trial_site_request_url': self.request.resource_url(self.context, '@@request_trial_site'),
            'base_domain': component.getUtility(ISiteDomainPolicy).base_domain,
            'client_name': {
                'max_length': ILMSSite['client_name'].max_length
            }
        }


@view_config(route_name='dashboards',
             renderer='../templates/admin/dashboard_trialsites.pt',
             request_method='GET',
             context=DashboardsResource,
             permission=ACT_READ,
             name='trialsites')
class DashboardTrialSitesView(BaseTemplateView):

    def __call__(self):
        table = make_specific_table(DashboardTrialSitesTable,
                                    get_sites_folder(request=self.request),
                                    self.request)
        return {'table': table}


@view_config(route_name='dashboards',
             renderer='../templates/admin/dashboard_renewals.pt',
             request_method='GET',
             context=DashboardsResource,
             permission=ACT_READ,
             name='renewals')
class DashboardRenewalsView(BaseTemplateView):

    def __call__(self):
        table = make_specific_table(DashboardRenewalsTable,
                                    get_sites_folder(request=self.request),
                                    self.request)
        return {'table': table}


class _RoleMixin(object):

    _role_names_map = {
        ADMIN_ROLE: 'Admin Role',
        ACCOUNT_MANAGEMENT_ROLE: 'Account Management Role',
        OPS_ROLE: 'Operations Management Role'
    }

    def _is_email_valid(self, email):
        return checkEmailAddress(email)

    @Lazy
    def principal_role_manager(self):
        onboarding = IOnboardingRoot(self.request)
        return IPrincipalRoleManager(onboarding)


@view_config(route_name='roles',
             renderer='../templates/admin/role.pt',
             request_method='GET',
             permission=ACT_READ,
             context=RolesResource)
class RoleView(BaseTemplateView, _RoleMixin):

    def _get_role_name(self, name):
        if name not in self._role_names_map:
            raise hexc.HTTPNotFound()
        return self._role_names_map[name]

    def __call__(self):
        role_name = self.request.params.get('role_name')
        role_display_name = self._get_role_name(role_name)
        principals = self.principal_role_manager.getPrincipalsForRole(role_name)
        principals = [x[0] for x in principals if x[1] == zopeAllow]
        table = make_specific_table(RolePrincipalsTable,
                                    principals,
                                    self.request)
        return {'table': table,
                'creation_url': self.request.route_url('roles', traverse=('@@assign',)),
                'role_name': role_name,
                'role_display_name': role_display_name,
                'is_deletion_allowed': self.request.has_permission(ACT_DELETE, self.context)}


@view_config(route_name='roles',
             renderer='json',
             request_method='POST',
             context=RolesResource,
             permission=ACT_CREATE,
             name="assign")
class AssignRoleToPrincipalView(BaseView, _RoleMixin):

    def __call__(self):
        role_name = self.body_params.get('role_name')
        if role_name not in self._role_names_map:
            raise_json_error(hexc.HTTPBadRequest, 'Unknown role_name.')

        email = self.body_params.get('email')
        if not email:
            raise_json_error(hexc.HTTPBadRequest, 'Email is required.')
        if not self._is_email_valid(email):
            raise_json_error(hexc.HTTPBadRequest, 'Invalid Email.')

        self.principal_role_manager.assignRoleToPrincipal(role_name, email)
        return {}


@view_config(route_name='roles',
             renderer='json',
             request_method='DELETE',
             context=RolesResource,
             permission=ACT_DELETE,
             name="remove")
class RemoveRoleToPrincipalView(BaseView, _RoleMixin):

    def __call__(self):
        params = self.request.params
        role_name = self._get_param('role_name', params)
        if role_name not in self._role_names_map:
            raise_json_error(hexc.HTTPBadRequest, 'Unknown role_name.')

        email = self._get_param('email', params)
        if not self._is_email_valid(email):
            raise_json_error(hexc.HTTPBadRequest, 'Invalid Email.')

        self.principal_role_manager.unsetRoleForPrincipal(role_name, email)
        return {}


@view_config(renderer='rest',
             request_method='POST',
             context=IOnboardingRoot,
             permission=ACT_AUTOMATED_REPORTS,
             name="trial_sites_digest_email")
class TrialSitesDigestEmailView(BaseView):
    """
    Will send two emails, one email is about trial sites that were created in the last 7 days,
    the other email is about trial sites that were past due or ending in the upcoming 7 days.
    """
    @Lazy
    def trial_sites(self):
        sites_folder = get_sites_folder(self.context)
        return [x for x in sites_folder.values() if ITrialLicense.providedBy(x.license)]

    @Lazy
    def active_trial_sites(self):
        return [x for x in self.trial_sites if x.status in (SITE_STATUS_ACTIVE, SITE_STATUS_PENDING, )]

    @Lazy
    def prefix(self):
        settings = component.getUtility(ISettings)
        try:
            env_name = settings['general']['env_name']
        except KeyError:
            env_name = None
        return env_name

    @Lazy
    def recipients(self):
        return self._get_setting_value_as_list('trial_sites_digest_email_recipients')

    @Lazy
    def cc(self):
        return self._get_setting_value_as_list('trial_sites_digest_email_cc')

    @Lazy
    def _mailer(self):
        return component.getUtility(ITemplatedMailer, name='default')

    def _send_mail(self, template, subject, template_args):
        self._mailer.queue_simple_html_text_email(template,
                                                  subject=subject,
                                                  recipients=self.recipients,
                                                  template_args=template_args,
                                                  cc=self.cc,
                                                  text_template_extension='.mak')

    def _generate_subject(self, title):
        return "[%s] %s" % (self.prefix, title) if self.prefix else title

    def _get_setting_value_as_list(self, field):
        settings = component.getUtility(IOnboardingSettings)
        value = [x.strip() for x in settings[field].split(',')]
        return [x for x in value if x]

    def _format_site(self, site):
        return {
            'site_name': site.dns_names[0],
            'site_id': site.id,
            'owner': site.owner.email,
            'creator': site.creator,
            'createdTime': formatDateToLocal(site.createdTime),
            'site_details_link': self.request.resource_url(site, '@@details'),
            'owner_details_link': self.request.resource_url(site.owner, '@@details') if site.owner else ''
        }

    def get_newly_created_trial_sites(self, notBefore, notAfter):
        """
        Fetch all trial sites since from a specific time if since is provided,
        and sorted by createdTime in descending order.
        """
        items = []
        for x in self.trial_sites:
            if notBefore <= x.createdTime and x.createdTime <= notAfter:
                items.append(self._format_site(x))
        items = sorted(items, key=lambda x: x['createdTime'], reverse=True)
        return items

    def get_ending_trial_sites(self, notBefore, notAfter):
        """
        Get all trial sites that are ending in the next 7 days,
        sorted by ending date in ascending order.
        """
        items = []
        for x in self.active_trial_sites:
            if x.license.end_date > notBefore and x.license.end_date <= notAfter:
                item = self._format_site(x)
                item['end_date'] = formatDateToLocal(x.license.end_date)
                items.append(item)
        items = sorted(items, key=lambda x: x['end_date'])
        return items

    def get_past_due_trial_sites(self, notAfter):
        """
        Get all trial sites that were past due,
        sorted by end_date in descending order.
        """
        items = []
        for x in self.active_trial_sites:
            if x.license.end_date <= notAfter:
                item = self._format_site(x)
                item['end_date'] = formatDateToLocal(x.license.end_date)
                items.append(item)
        items = sorted(items, key=lambda x: x['end_date'], reverse=True)
        return items

    def send_newly_created_trial_sites(self, template_args):
        self._send_mail(template="nti.app.environments:email_templates/newly_created_trial_sites",
                        subject=self._generate_subject("Trial Sites Created Last Week"),
                        template_args=template_args)

    def send_past_due_and_ending_trial_sites(self, template_args):
        self._send_mail(template="nti.app.environments:email_templates/trial_sites_digest_email",
                        subject=self._generate_subject("Weekly Trial Site Digest"),
                        template_args=template_args)

    def __call__(self):
        current_time = time.time()
        current_date = datetime.utcfromtimestamp(current_time)

        # Newly created trial sites
        items = self.get_newly_created_trial_sites(notBefore=current_time-7*24*60*60,
                                                   notAfter=current_time)
        self.send_newly_created_trial_sites(template_args={'items': items})

        # Past due and ending trial sites.
        ending_items = self.get_ending_trial_sites(notBefore=current_date,
                                                   notAfter=datetime.utcfromtimestamp(current_time + 7*24*60*60))
        past_items = self.get_past_due_trial_sites(notAfter=current_date)
        self.send_past_due_and_ending_trial_sites(template_args={
                                                    'ending_items': ending_items,
                                                    'past_items': past_items
                                                    })

        result = LocatedExternalDict()
        result.__name__ = self.context.__name__
        result.__parent__ = self.context.__parent__
        result.update({
            "new": len(items),
            "ending": len(ending_items),
            "past_due": len(past_items)
        })
        return result

@view_defaults(renderer='rest',
               request_method='GET',
               context=ILMSSitesContainer,
               permission=ACT_READ,
               name="license_audit")
class LicenseAuditView(CSVBaseView):
    """
    Loop through ACTIVE sites and check their licenses.
    We check if the license date is within
    x days based on provided query params. For IRestrictedLicense
    we poll their usage and compare that to the configured seats.

    # TODO check stripe subscription status when necessary
    """

    DEFAULT_THRESHOLD_DAYS = 5 #5 Days

    @property
    def sites(self):
        return self.context

    @Lazy
    def now(self):
        return datetime.utcnow()

    @Lazy
    def query_usage(self):
        return is_true(self.request.params.get('query_usage'))

    @Lazy
    def default_threshold(self):
        return int(self.request.params.get(f'threshold_days', self.DEFAULT_THRESHOLD_DAYS))

    def threshold_for_license(self, license):
        ln = license.license_name
        return int(self.request.params.get(f'{ln}_threshold_days', self.default_threshold))

    def audit_site(self, siteid):
        site = self.sites[siteid]
        if site.status != SITE_STATUS_ACTIVE:
            return None

        if self.query_usage:
            try:
                _do_fetch_site_usage(siteid,
                                     'onboarding@nextthought.com',
                                     'Onboarding Usage',
                                     'onboarding@nextthought.com',
                                     find_interface(self.context, IOnboardingRoot))
            except:
                logger.warn('Unable to query usage for %s', siteid)

        issues = []

        audit = {}

        days_threshold = self.threshold_for_license(site.license)
        if self.now > site.license.end_date - timedelta(days=days_threshold):
            issues.append(('site.license.end_date past threshold of %i days' % days_threshold))


        usage = ISiteUsage(site)

        if IRestrictedLicense.providedBy(site.license) \
           and usage.instructor_count != None \
           and usage.admin_count != None:
            
            # Validate we have enough licensed seats for admins
            if usage.admin_count > site.license.seats:
                issues.append(('Admin count %i exceeds limit %i' % (usage.admin_count, site.license.seats)))

            allowed_instructors = max(site.license.seats - usage.admin_count, 0)
            allowed_instructors += (site.license.additional_instructor_seats or 0)
            if usage.instructor_count > allowed_instructors:
               issues.append(('Instructor count %i exceeds limit %i' % (usage.instructor_count, allowed_instructors)))

        
        if IRestrictedScorm.providedBy(site.license):
            if usage.scorm_package_count != None and usage.scorm_package_count > site.license.max_scorm_packages:
                issues.append(('Scorm package count %i exceeds limit %i' % (usage.scorm_package_count,
                                                                            site.license.max_scorm_packages)))

        if issues:
            audit['Site'] = site
            audit['License'] = site.license
            audit['Usage'] = usage
            audit['Issues'] = issues

        return audit if issues else None

    def _do_generate_alerts(self):
        failed_sites = {}

        for sid in self.sites:
            res = self.audit_site(sid)
            if res:
                failed_sites[sid] = res
        return failed_sites

    def header(self, params=None):
        return ["id", "dns", "License",
                "Seats", "Instructor Addon Seats",
                "Issues", "End Date", "Admins", "Instructors", "Admin Count", "Instructor Count", "Scorm Package Limit", "Scorm Package Usage"]

    def filename(self):
        return 'license_audit.csv'

    def records(self, params):
        return self._do_generate_alerts().values()

    def row_data_for_record(self, record):
        site = record['Site']
        usage = ISiteUsage(site)
        license = site.license
        links = component.queryMultiAdapter((site, self.request), ISiteLinks)
        data = [site.id, links.preferred_dns, license.license_name]
        seats = ''
        addons = ''
        if IRestrictedLicense.providedBy(license):
            seats = license.seats
            addons = license.additional_instructor_seats or ''
        data.extend([seats, addons])
        data.append(', '.join(record['Issues']))

        end_date = license.end_date or ''
        data.append(end_date)

        admins = ''
        if usage.admin_usernames:
            admins = ', '.join(usage.admin_usernames)

        instructors = ''
        if usage.instructor_usernames:
            instructors = ', '.join(usage.instructor_usernames)

        admin_count = usage.admin_count if usage.admin_count != None else ''
        instructor_count = usage.instructor_count if usage.instructor_count != None else ''

        data.extend([admins, instructors, admin_count, instructor_count])

        scorm_package_limit = ''
        scorm_package_usage = ''
        if IRestrictedScorm.providedBy(site.license):
            scorm_package_limit = site.license.max_scorm_packages
            scorm_package_usage = usage.scorm_package_count if usage.scorm_package_count != None else ''
        data.extend([scorm_package_limit, scorm_package_usage])
        
        return {k[0]:k[1] for k in zip(self.header(), data)}

    @view_config(request_param="format=csv",
                 accept='text/csv')
    def csv(self):
        return self()
        
    @view_config(accept='application/json',
                 request_param=not_("format=csv"))
    def json(self):
        failed_sites = self._do_generate_alerts()
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.context
        result[ITEMS] = failed_sites
        result[TOTAL] = len(failed_sites)
        return result

@view_config(route_name='dashboards',
             renderer='../templates/admin/dashboard_license_audit.pt',
             request_method='GET',
             context=DashboardsResource,
             permission=ACT_READ,
             name='license_audit')
class DashboardLicenseAuditView(BaseTemplateView, LicenseAuditView):

    DEFAULT_THRESHOLD_DAYS = 0

    @property
    def sites(self):
        return get_sites_folder(request=self.request)

    def __call__(self):

        failed_sites = {}
        for sid in self.sites:
            res = self.audit_site(sid)
            if res:
                failed_sites[sid] = res

        table = make_specific_table(DashboardLicenseAuditTable,
                                    self.sites,
                                    self.request,
                                    alerts=failed_sites)

        export = self.request.resource_url(self.sites,
                                           '@@license_audit',
                                           query={'threshold_days': self.DEFAULT_THRESHOLD_DAYS,
                                                  'format':'csv'})
        
        return {
            'table': table,
            'audit_export_url': export
        }
