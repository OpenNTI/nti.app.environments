import time
import urllib.parse

from datetime import datetime

from pyramid.view import view_config

from pyramid import httpexceptions as hexc

from zope.cachedescriptors.property import Lazy

from zope import component

from zope.securitypolicy.interfaces import Allow as zopeAllow
from zope.securitypolicy.interfaces import IPrincipalRoleManager

from nti.mailer.interfaces import ITemplatedMailer

from nti.environments.management.interfaces import ISettings

from nti.app.environments.api.siteinfo import nt_client

from nti.app.environments.api.hubspotclient import get_hubspot_profile_url

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
from nti.app.environments.auth import ADMIN_ROLE
from nti.app.environments.auth import ACCOUNT_MANAGEMENT_ROLE
from nti.app.environments.auth import OPS_ROLE

from nti.app.environments.interfaces import ISiteDomainPolicy
from nti.app.environments.interfaces import IOnboardingSettings

from nti.app.environments.models.adapters import get_site_usage

from nti.app.environments.models.interfaces import ICustomer
from nti.app.environments.models.interfaces import ISharedEnvironment
from nti.app.environments.models.interfaces import IDedicatedEnvironment
from nti.app.environments.models.interfaces import IOnboardingRoot
from nti.app.environments.models.interfaces import ICustomersContainer
from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import ILMSSitesContainer
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
from nti.app.environments.models.interfaces import SITE_STATUS_ACTIVE
from nti.app.environments.models.interfaces import SITE_STATUS_PENDING

from nti.app.environments.models.utils import get_sites_folder
from nti.app.environments.models.utils import get_hosts_folder

from nti.app.environments.resources import DashboardsResource
from nti.app.environments.resources import RolesResource

from nti.app.environments.common import formatDateToLocal

from nti.app.environments.utils import query_setup_state

from nti.app.environments.views.base import BaseTemplateView
from nti.app.environments.views.base import BaseView
from nti.app.environments.views.base import TableViewMixin

from nti.app.environments.views._table_utils import CustomersTable
from nti.app.environments.views._table_utils import RolePrincipalsTable
from nti.app.environments.views._table_utils import SitesTable
from nti.app.environments.views._table_utils import DashboardTrialSitesTable
from nti.app.environments.views._table_utils import DashboardRenewalsTable
from nti.app.environments.views._table_utils import make_specific_table

from nti.app.environments.views.utils import raise_json_error

from nti.traversal.traversal import find_interface
from nti.externalization.interfaces import LocatedExternalDict


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
                'customer': {'customer': self.context,
                             'hubspot': self._format_hubspot(self.context.hubspot_contact) if self.context.hubspot_contact else None},
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

    def _site_extra_info(self):
        hostname = self.context.dns_names[0] if self.context.dns_names else None
        return nt_client.fetch_site_info(hostname) if hostname else None

    def _format_license(self, lic):
        edit_link = self.request.resource_url(self.context, '@@license') if self.request.has_permission(ACT_EDIT_SITE_LICENSE, self.context) else None
        result = {'type': lic.license_name,
                  'start_date': formatDateToLocal(lic.start_date),
                  'edit_link': edit_link,
                  'lastModified': formatDateToLocal(lic.lastModified)}
        if ITrialLicense.providedBy(lic) or IEnterpriseLicense.providedBy(lic):
            result.update({'end_date': formatDateToLocal(lic.end_date)})
            return result
        elif IStarterLicense.providedBy(lic) or IGrowthLicense.providedBy(lic):
            result.update({'frequency': lic.frequency,
                           'seats': lic.seats})
            return result
        raise ValueError("Unknown license type.")

    def _splunk_link(self, env):
        tpl = 'https://splunk.nextthought.com/en-US/app/search/search?q={}'
        if ISharedEnvironment.providedBy(env):
            name = self._shared_env_names.get(env.name)
            return tpl.format(urllib.parse.quote('search index="%s" earliest=-1d' % name, safe='')) if name else None
        elif IDedicatedEnvironment.providedBy(env):
            return tpl.format(urllib.parse.quote('search index="dedicated_environments" host="%s.nti" earliest=-1d' % self.context.id, safe=''))
        return None

    def _format_env(self, env=None):
        if ISharedEnvironment.providedBy(env):
            return {'type': 'shared',
                    'env': env,
                    'lastModified': formatDateToLocal(env.lastModified),
                    'splunk_link': self._splunk_link(env)}
        elif IDedicatedEnvironment.providedBy(env):
            return {'type': 'dedicated',
                    'env': env,
                    'lastModified': formatDateToLocal(env.lastModified),
                    'splunk_link': self._splunk_link(env)}
        raise ValueError('Unknown environment type.')

    def _format_owner(self, owner=None):
        return {'owner': owner,
                'detail_url': self.request.resource_url(owner, '@@details') if owner else None}

    def _format_parent_site(self, parent):
        return {'id': parent.id,
                'dns_names': parent.dns_names,
                'detail_url': self.request.resource_url(parent, '@@details')}

    def _format_usage(self, context):
        usage = get_site_usage(context)
        if usage is None:
            return None
        return {'usage': usage,
                'lastModified': formatDateToLocal(usage.lastModified)}

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
                         'creator': self.context.creator,
                         'owner': self._format_owner(self.context.owner),
                         'site_id': self.context.id,
                         'status': self.context.status,
                         'dns_names': self.context.dns_names,
                         'license': self._format_license(self.context.license),
                         'environment': self._format_env(self.context.environment) if self.context.environment else None,
                         'environment_edit_link': request.resource_url(self.context, '@@environment') if request.has_permission(ACT_EDIT_SITE_ENVIRONMENT, self.context) else None,
                         'site_login_link': request.resource_url(self.context, '@@login') if request.has_permission(ACT_SITE_LOGIN, self.context) else None,
                         'generate_token_link': request.resource_url(self.context, '@@generate_token') if request.has_permission(ACT_ADMIN, self.context) else None,
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
