from pyramid.view import view_config

from nti.app.environments.api.siteinfo import nt_client

from nti.app.environments.auth import ACT_ADMIN

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
from nti.app.environments.utils import find_iface
from nti.app.environments.models.utils import get_sites_folder


def _format_date(value):
    return value.strftime('%Y-%m-%dT%H:%M:%SZ') if value else ''


@view_config(route_name='admin',
             renderer='../templates/admin/customers.pt',
             request_method='GET',
             context=ICustomersContainer,
             permission=ACT_ADMIN,
             name='list')
class CustomersListView(BaseTemplateView):

    def __call__(self):
        table = make_specific_table(CustomersTable, self.context, self.request)
        return {'table': table,
                'creation_url': self.request.resource_url(self.context, '@@hubspot')}


@view_config(route_name='admin',
             renderer='../templates/admin/customer_detail.pt',
             request_method='GET',
             context=ICustomer,
             permission=ACT_ADMIN,
             name='details')
class CustomerDetailView(BaseTemplateView):

    def _get_sites_folder(self):
        onboarding_root = find_iface(self.context, IOnboardingRoot)
        return get_sites_folder(onboarding_root)

    def __call__(self):
        sites = self._get_sites_folder()
        table = make_specific_table(SitesTable, sites, self.request, email=self.context.email)
        return {'customers_list_link': self.request.route_url('admin', traverse=('customers', '@@list')),
                'customer': {'email': self.context.email,
                             'name': self.context.name,
                             'hubspot': self.context.hubspot_contact.contact_vid if self.context.hubspot_contact else ''},
                'table': table}


@view_config(route_name='admin',
             renderer='../templates/admin/sites.pt',
             request_method='GET',
             context=ILMSSitesContainer,
             permission=ACT_ADMIN,
             name='list')
class SitesListView(BaseTemplateView):

    def __call__(self):
        table = make_specific_table(SitesTable, self.context, self.request)
        return {'table': table,
                'creation_url': self.request.resource_url(self.context),
                'site_status_options': SITE_STATUS_OPTIONS,
                'env_shared_options': SHARED_ENV_NAMES}


@view_config(route_name='admin',
             renderer='../templates/admin/site_detail.pt',
             request_method='GET',
             context=ILMSSite,
             permission=ACT_ADMIN,
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
        return {'type': self._license_type(lic),
                'start_date': _format_date(lic.start_date),
                'end_date': _format_date(lic.end_date)}

    def _format_env(self, env):
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
        extra_info = self._site_extra_info() or {}
        return {'sites_list_link': self.request.route_url('admin', traverse=('sites', '@@list')),
                'site': {'created': _format_date(self.context.created),
                         'owner_username': self.context.owner_username,
                         'owner': self._format_owner(self.context.owner),
                         'site_id': self.context.id,
                         'status': self.context.status,
                         'dns_names': self.context.dns_names,
                         'license': self._format_license(self.context.license),
                         'environment': self._format_env(self.context.environment),
                         **extra_info}}
