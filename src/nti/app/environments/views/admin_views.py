from pyramid.view import view_config

from nti.app.environments.auth import ACT_ADMIN

from nti.app.environments.models.interfaces import ICustomer, IOnboardingRoot
from nti.app.environments.models.interfaces import ICustomersContainer
from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import ILMSSitesContainer

from nti.app.environments.views.base import BaseTemplateView
from nti.app.environments.views._table_utils import CustomersTable
from nti.app.environments.views._table_utils import SitesTable
from nti.app.environments.views._table_utils import make_specific_table
from nti.app.environments.views.utils import find_iface
from nti.app.environments.models import get_sites


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
        return {'table': table}


@view_config(route_name='admin',
             renderer='../templates/admin/customer_detail.pt',
             request_method='GET',
             context=ICustomer,
             permission=ACT_ADMIN,
             name='details')
class CustomerDetailView(BaseTemplateView):

    def _get_sites_folder(self):
        onboarding_root = find_iface(self.context, IOnboardingRoot)
        return get_sites(onboarding_root)

    def __call__(self):
        sites = self._get_sites_folder()
        table = make_specific_table(SitesTable, sites, self.request, email=self.context.email)
        return {'customers_list_link': self.request.route_url('admin', traverse=('customers', '@@list')),
                'customer': {'email': self.context.email,
                             'name': self.context.name},
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
                'creation_url': self.request.resource_url(self.context)}


@view_config(route_name='admin',
             renderer='../templates/admin/site_detail.pt',
             request_method='GET',
             context=ILMSSite,
             permission=ACT_ADMIN,
             name='details')
class SiteDetailView(BaseTemplateView):

    def __call__(self):
        return {'sites_list_link': self.request.route_url('admin', traverse=('sites', '@@list')),
                'site': {'created': _format_date(self.context.created),
                         'owner_username': self.context.owner_username,
                         'owner': self.context.owner,
                         'dns_names': self.context.dns_names,
                         'license': self.context.license,
                         'environment': self.context.environment}}
