from pyramid.view import view_config

from nti.app.environments.api.siteinfo import nt_client

from nti.app.environments.api.hubspotclient import get_hubspot_profile_url

from nti.app.environments.auth import ACT_READ
from nti.app.environments.auth import ACT_DELETE
from nti.app.environments.auth import ACT_CREATE
from nti.app.environments.auth import ACT_EDIT_SITE_LICENSE
from nti.app.environments.auth import ACT_EDIT_SITE_ENVIRONMENT

from nti.app.environments.models.interfaces import ICustomer
from nti.app.environments.models.interfaces import IEnterpriseLicense
from nti.app.environments.models.interfaces import ISharedEnvironment
from nti.app.environments.models.interfaces import IDedicatedEnvironment
from nti.app.environments.models.interfaces import IOnboardingRoot
from nti.app.environments.models.interfaces import ITrialLicense
from nti.app.environments.models.interfaces import ICustomersContainer
from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import ILMSSitesContainer
from nti.app.environments.models.interfaces import SITE_STATUS_OPTIONS
from nti.app.environments.models.interfaces import SHARED_ENV_NAMES

from nti.app.environments.views.base import BaseTemplateView
from nti.app.environments.views._table_utils import CustomersTable
from nti.app.environments.views._table_utils import SitesTable
from nti.app.environments.views._table_utils import make_specific_table
from nti.app.environments.utils import formatDateToLocal
from nti.app.environments.utils import find_iface
from nti.app.environments.models.utils import get_sites_folder


class _TableMixin(object):

    def _is_deletion_allowed(self, table):
        if table._raw_values:
            return any(bool(self.request.has_permission(ACT_DELETE, x)) for x in table._raw_values)
        return False


@view_config(route_name='admin',
             renderer='../templates/admin/customers.pt',
             request_method='GET',
             context=ICustomersContainer,
             permission=ACT_READ,
             name='list')
class CustomersListView(BaseTemplateView, _TableMixin):

    def __call__(self):
        table = make_specific_table(CustomersTable, self.context, self.request)
        return {'table': table,
                'creation_url': self.request.resource_url(self.context, '@@hubspot') if self.request.has_permission(ACT_CREATE, self.context) else None,
                'is_deletion_allowed': self._is_deletion_allowed(table)}


@view_config(route_name='admin',
             renderer='../templates/admin/customer_detail.pt',
             request_method='GET',
             context=ICustomer,
             permission=ACT_READ,
             name='details')
class CustomerDetailView(BaseTemplateView, _TableMixin):

    def _get_sites_folder(self):
        onboarding_root = find_iface(self.context, IOnboardingRoot)
        return get_sites_folder(onboarding_root)

    def _format_hubspot(self, contact=None):
        return {'contact_vid': contact.contact_vid,
                'profile_url': get_hubspot_profile_url(contact.contact_vid)}

    def __call__(self):
        sites = self._get_sites_folder()
        table = make_specific_table(SitesTable, sites, self.request, email=self.context.email)
        return {'customers_list_link': self.request.route_url('admin', traverse=('customers', '@@list')),
                'customer': {'email': self.context.email,
                             'name': self.context.name,
                             'hubspot': self._format_hubspot(self.context.hubspot_contact) if self.context.hubspot_contact else None},
                'table': table,
                'is_deletion_allowed': self._is_deletion_allowed(table)}


@view_config(route_name='admin',
             renderer='../templates/admin/sites.pt',
             request_method='GET',
             context=ILMSSitesContainer,
             permission=ACT_READ,
             name='list')
class SitesListView(BaseTemplateView, _TableMixin):

    def __call__(self):
        table = make_specific_table(SitesTable, self.context, self.request)
        return {'table': table,
                'creation_url': self.request.resource_url(self.context) if self.request.has_permission(ACT_CREATE, self.context) else None,
                'sites_upload_url': self.request.resource_url(self.context, '@@upload_sites') if self.request.has_permission(ACT_CREATE, self.context) else None,
                'sites_export_url': self.request.resource_url(self.context, '@@export_sites'),
                'trial_site_request_url': self.request.route_url('admin', traverse=('sites', '@@request_trial_site')) if self.request.has_permission(ACT_CREATE, self.context) else None,
                'site_status_options': SITE_STATUS_OPTIONS,
                'env_shared_options': SHARED_ENV_NAMES,
                'is_deletion_allowed': self._is_deletion_allowed(table)}


@view_config(route_name='admin',
             renderer='../templates/admin/site_detail.pt',
             request_method='GET',
             context=ILMSSite,
             permission=ACT_READ,
             name='details')
class SiteDetailView(BaseTemplateView):

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
                'edit_link': edit_link}

    def _format_env(self, env=None):
        if ISharedEnvironment.providedBy(env):
            return {'type': 'shared',
                    'name': env.name}
        elif IDedicatedEnvironment.providedBy(env):
            return {'type': 'dedicated',
                    'pod_id': env.pod_id,
                    'host': env.host}
        raise ValueError('Unknown environment type.')

    def _format_owner(self, owner=None):
        return {'owner': owner,
                'detail_url': self.request.route_url('admin', traverse=('customers', self.context.owner.__name__, '@@details')) if owner else None}

    def __call__(self):
        request = self.request
        extra_info = self._site_extra_info() or {}
        return {'sites_list_link': self.request.route_url('admin', traverse=('sites', '@@list')),
                'env_shared_options': SHARED_ENV_NAMES,
                'site': {'created': formatDateToLocal(self.context.created),
                         'owner': self._format_owner(self.context.owner),
                         'site_id': self.context.id,
                         'status': self.context.status,
                         'dns_names': self.context.dns_names,
                         'license': self._format_license(self.context.license),
                         'environment': self._format_env(self.context.environment) if self.context.environment else None,
                         'environment_edit_link': request.resource_url(self.context, '@@environment') if request.has_permission(ACT_EDIT_SITE_ENVIRONMENT, self.context) else None,
                         'requesting_email': self.context.requesting_email,
                         'client_name': self.context.client_name,
                         **extra_info}}


@view_config(route_name='admin',
             renderer='../templates/admin/request_site.pt',
             request_method='GET',
             context=ILMSSitesContainer,
             permission=ACT_READ,
             name='request_trial_site')
class SiteRequestView(BaseTemplateView):

    def __call__(self):
        return {
            'trial_site_request_url': self.request.resource_url(self.context, '@@request_trial_site') if self.request.has_permission(ACT_CREATE, self.context) else None
        }
