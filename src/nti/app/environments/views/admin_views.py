from pyramid.view import view_config
from pyramid import httpexceptions as hexc

from nti.app.environments.models.interfaces import ICustomer
from nti.app.environments.models.interfaces import ICustomersContainer
from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import ILMSSitesContainer

from nti.app.environments.views.base import BaseTemplateView
from nti.app.environments.views._table_utils import CustomersTable
from nti.app.environments.views._table_utils import SitesTable
from nti.app.environments.views._table_utils import make_specific_table


def _format_date(value):
    return value.strftime('%Y-%m-%dT%H:%M:%SZ') if value else ''


@view_config(route_name='admin',
             renderer='../templates/admin/customers.pt',
             request_method='GET',
             context=ICustomersContainer,
             name='details')
class CustomersDetailsView(BaseTemplateView):

    def __call__(self):
        table = make_specific_table(CustomersTable, self.context, self.request)
        return {'table': table}


@view_config(renderer='json',
             context=ICustomer,
             request_method='DELETE')
def deleteCustomerView(context, request):
    container = context.__parent__
    del container[context.__name__]
    return hexc.HTTPNoContent()


@view_config(route_name='admin',
             renderer='../templates/admin/sites.pt',
             request_method='GET',
             context=ILMSSitesContainer,
             name='details')
class SitesDetailsView(BaseTemplateView):

    def __call__(self):
        table = make_specific_table(SitesTable, self.context, self.request)
        return {'table': table}


@view_config(route_name='admin',
             renderer='../templates/admin/site_detail.pt',
             request_method='GET',
             context=ILMSSite,
             name='details')
class SiteDetailView(BaseTemplateView):

    def __call__(self):
        return {'sites_list_link': self.request.route_url('admin', traverse=('sites', '@@details')),
                'site': {'created': _format_date(self.context.created),
                         'owner_username': self.context.owner_username}}
