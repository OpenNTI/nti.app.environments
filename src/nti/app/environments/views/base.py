import datetime
from pyramid import httpexceptions as hexc

from zope.cachedescriptors.property import Lazy

from zope.schema._bootstrapinterfaces import ValidationError

from nti.app.environments.auth import is_admin_or_account_mgr

from nti.app.environments.models.customers import HubspotContact
from nti.app.environments.models.customers import PersistentCustomer

from nti.app.environments.views.utils import raise_json_error


class BaseView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def _get_param(self, name, params=None, required=True):
        params = self.request.params if params is None else params
        value = params.get(name)
        value = value.strip() if value else None
        if not value and required:
            raise_json_error(hexc.HTTPBadRequest, 'Missing required {}'.format(name))
        return value

    @Lazy
    def body_params(self):
        try:
            body = self.request.json_body
        except ValueError:
            raise_json_error(hexc.HTTPBadRequest, "Invalid json body.")
        return body

    def _get_body_value(self, field, params, expected_type=None, required=False):
        if params is None:
            params = self.body_params
        val = params.get(field)
        if expected_type is not None and not isinstance(val, (expected_type, None)):
            raise_json_error(hexc.HTTPUnprocessableEntity, "Invalid {}".format(field), field)
        if required and val is None:
            raise_json_error(hexc.HTTPUnprocessableEntity,
                             'Missing required field: {}.'.format(field))
        return val.strip() if isinstance(val, str) else val


class BaseTemplateView(BaseView):

    logged_in = None
    is_admin = None

    def __init__(self, context, request):
        super(BaseTemplateView, self).__init__(context, request)
        if self.request.authenticated_userid:
            self.logged_in = True
            self.is_admin = is_admin_or_account_mgr(self.request.authenticated_userid)


class BaseFieldPutView(BaseView):

    def _allowed_attr_names(self, field_value):
        return ()

    def _incoming_field_value(self, params):
        raise NotImplementedError

    def _update_field(self, obj, incoming, attr_names=()):
        for attr_name in attr_names:
            if getattr(obj, attr_name) != getattr(incoming, attr_name):
                setattr(obj, attr_name, getattr(incoming, attr_name))

    def _update_obj(self, context, field_name, field_value, incoming):
        if type(field_value) != type(incoming):
            setattr(context, field_name, incoming)
        else:
            self._update_field(field_value,
                               incoming,
                               attr_names=self._allowed_attr_names(field_value))

    def __call__(self):
        try:
            field_name = self.request.view_name
            obj = getattr(self.context, field_name)
            incoming = self._incoming_field_value(self.body_params)
            self._update_obj(self.context, field_name, obj, incoming)
            return {}
        except ValidationError as err:
            raise_json_error(hexc.HTTPUnprocessableEntity,
                             error=err)


def getOrCreateCustomer(container, email):
    try:
        customer = container[email]
    except KeyError:
        customer = PersistentCustomer()
        customer.email = email
        customer.__name__ = email
        customer.created = datetime.datetime.utcnow()
        container[customer.__name__] = customer
    return customer


def createCustomer(container, email, name, hs_contact_vid):
    customer = getOrCreateCustomer(container, email)
    customer.name = name
    customer.hubspot_contact = HubspotContact(contact_vid=str(hs_contact_vid))
    return customer