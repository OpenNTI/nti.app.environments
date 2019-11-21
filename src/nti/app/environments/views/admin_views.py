from pyramid.view import view_config
from pyramid import httpexceptions as hexc

from nti.app.environments.models.interfaces import ICustomer
from nti.app.environments.models.interfaces import ICustomersContainer

from nti.app.environments.views.base import BaseTemplateView


def format_date(dt, _format='%Y-%m-%dT%H:%M:%SZ'):
    return dt.strftime(_format) if dt else ''


@view_config(renderer='../templates/admin/customers.pt',
             context=ICustomersContainer,
             request_method='GET',
             name="details")
class CustomersDetailsView(BaseTemplateView):

    def __call__(self):
        items = []
        for x in self.context.values():
            items.append({'email': x.email,
                          'name': x.name,
                          'hubspot': getattr(x.hubspot_contact, 'contact_vid', ''),
                          'created': format_date(x.created),
                          'last_verified': format_date(x.last_verified),
                          'delete_url': self.request.resource_url(x)})
        return {'items': items}


@view_config(renderer='json',
             context=ICustomer,
             request_method='DELETE')
def deleteCustomerView(context, request):
    container = context.__parent__
    del container[context.__name__]
    return hexc.HTTPNoContent()
