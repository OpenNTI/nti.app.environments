import urllib.parse

from pyramid.view import view_config

from pyramid import httpexceptions as hexc

from zope.cachedescriptors.property import Lazy

from zope import component

from zope.securitypolicy.interfaces import Allow as zopeAllow
from zope.securitypolicy.interfaces import IPrincipalRoleManager

from nti.app.environments.api.siteinfo import nt_client

from nti.app.environments.api.hubspotclient import get_hubspot_profile_url

from nti.app.environments.auth import ACT_READ
from nti.app.environments.auth import ACT_UPDATE
from nti.app.environments.auth import ACT_DELETE
from nti.app.environments.auth import ACT_CREATE
from nti.app.environments.auth import ACT_EDIT_SITE_LICENSE
from nti.app.environments.auth import ACT_EDIT_SITE_ENVIRONMENT
from nti.app.environments.auth import ACT_REQUEST_TRIAL_SITE
from nti.app.environments.auth import ADMIN_ROLE
from nti.app.environments.auth import ACCOUNT_MANAGEMENT_ROLE

from nti.app.environments.interfaces import ISiteDomainPolicy

from nti.app.environments.models.adapters import get_site_usage

from nti.app.environments.models.interfaces import ICustomer
from nti.app.environments.models.interfaces import IEnterpriseLicense
from nti.app.environments.models.interfaces import ISharedEnvironment
from nti.app.environments.models.interfaces import IDedicatedEnvironment
from nti.app.environments.models.interfaces import IOnboardingRoot
from nti.app.environments.models.interfaces import ITrialLicense
from nti.app.environments.models.interfaces import ICustomersContainer
from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import ILMSSitesContainer
from nti.app.environments.models.interfaces import ISetupStatePending
from nti.app.environments.models.interfaces import ISetupStateSuccess
from nti.app.environments.models.interfaces import ISetupStateFailure
from nti.app.environments.models.interfaces import SITE_STATUS_OPTIONS
from nti.app.environments.models.interfaces import SHARED_ENV_NAMES
from nti.app.environments.models.interfaces import checkEmailAddress

from nti.app.environments.models.utils import get_sites_folder
from nti.app.environments.models.utils import get_hosts_folder

from nti.app.environments.resources import DashboardsResource
from nti.app.environments.resources import RolesResource

from nti.app.environments.utils import formatDateToLocal
from nti.app.environments.utils import find_iface

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
from nti.app.environments.views.utils import query_setup_state


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
                'create_via_hubspot': self.request.resource_url(self.context, '@@hubspot') if has_create_perm else None,
                'is_deletion_allowed': self._is_deletion_allowed(table)}


@view_config(renderer='../templates/admin/customer_detail.pt',
             request_method='GET',
             context=ICustomer,
             permission=ACT_READ,
             name='details')
class CustomerDetailView(BaseTemplateView, TableViewMixin):

    def _get_sites_folder(self):
        onboarding_root = find_iface(self.context, IOnboardingRoot)
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
                'is_deletion_allowed': self._is_deletion_allowed(table)}


@view_config(
             renderer='../templates/admin/sites.pt',
             request_method='GET',
             context=ILMSSitesContainer,
             permission=ACT_READ,
             name='list')
class SitesListView(BaseTemplateView, TableViewMixin):

    def _format_hosts(self):
        hosts = get_hosts_folder(self._onboarding_root)
        return [(x.host_id, "{} ({}/{})".format(x.host_id, x.current_load, x.capacity)) for x in hosts.values()]

    def __call__(self):
        # may have side effects.
        query_setup_state(self.context.values(), self.request, side_effects=True)

        table = make_specific_table(SitesTable, self.context, self.request)
        return {'table': table,
                'creation_url': self.request.resource_url(self.context) if self.request.has_permission(ACT_CREATE, self.context) else None,
                'sites_upload_url': self.request.resource_url(self.context, '@@upload_sites') if self.request.has_permission(ACT_CREATE, self.context) else None,
                'sites_export_url': self.request.resource_url(self.context, '@@export_sites'),
                'trial_site_request_url': self.request.resource_url(self.context, '@@request_trial_site') if self.request.has_permission(ACT_REQUEST_TRIAL_SITE, self.context) else None,
                'site_status_options': SITE_STATUS_OPTIONS,
                'env_shared_options': SHARED_ENV_NAMES,
                'is_deletion_allowed': self._is_deletion_allowed(table),
                'hosts_options': _host_options(self._onboarding_root)}


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

    def _license_type(self, lic):
        if ITrialLicense.providedBy(lic):
            return 'trial'
        elif IEnterpriseLicense.providedBy(lic):
            return 'enterprise'
        raise ValueError('Unknown license type.')

    def _format_license(self, lic):
        edit_link = self.request.resource_url(self.context, '@@license') if self.request.has_permission(ACT_EDIT_SITE_LICENSE, self.context) else None
        return {'type': self._license_type(lic),
                'start_date': formatDateToLocal(lic.start_date),
                'end_date': formatDateToLocal(lic.end_date),
                'edit_link': edit_link,
                'lastModified': formatDateToLocal(lic.lastModified)}

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
        res = {}
        for iface, status in ((ISetupStatePending, 'pending'),
                              (ISetupStateSuccess, 'success'),
                              (ISetupStateFailure, 'failure')):
            if iface.providedBy(state):
                res['status'] = status
        if res:
            res['setup_state'] = state
            return res

        raise_json_error(hexc.HTTPUnprocessableEntity,
                         "Unknown setup_state: {}.".format(state))

    def __call__(self):
        request = self.request
        extra_info = self._site_extra_info() or {}

        # may have site effects.
        query_setup_state([self.context], self.request, side_effects=True)

        return {'sites_list_link': self.request.resource_url(self.context.__parent__, '@@list'),
                'env_shared_options': SHARED_ENV_NAMES,
                'site_status_options': SITE_STATUS_OPTIONS,
                'hosts_options': _host_options(self._onboarding_root),
                'site': {'created': formatDateToLocal(self.context.created),
                         'creator': self.context.creator,
                         'owner': self._format_owner(self.context.owner),
                         'site_id': self.context.id,
                         'status': self.context.status,
                         'dns_names': self.context.dns_names,
                         'license': self._format_license(self.context.license),
                         'environment': self._format_env(self.context.environment) if self.context.environment else None,
                         'environment_edit_link': request.resource_url(self.context, '@@environment') if request.has_permission(ACT_EDIT_SITE_ENVIRONMENT, self.context) else None,
                         'client_name': self.context.client_name,
                         'site_edit_link': request.resource_url(self.context) if request.has_permission(ACT_UPDATE, self.context) else None,
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
            'base_domain': component.getUtility(ISiteDomainPolicy).base_domain 
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
        ACCOUNT_MANAGEMENT_ROLE: 'Account Management Role'
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
