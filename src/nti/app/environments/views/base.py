import copy

from pyramid import httpexceptions as hexc

from zope.cachedescriptors.property import Lazy

from zope.interface import Invalid

from zope.interface.interfaces import ComponentLookupError

from zope.schema._bootstrapinterfaces import ValidationError

from nti.externalization import new_from_external_object
from nti.externalization import update_from_external_object

from nti.app.environments.api.hubspotclient import get_hubspot_client

from nti.app.environments.auth import ACT_READ
from nti.app.environments.auth import ACT_DELETE
from nti.app.environments.auth import ADMIN_ROLE
from nti.app.environments.auth import ACCOUNT_MANAGEMENT_ROLE
from nti.app.environments.auth import is_admin
from nti.app.environments.auth import is_admin_or_account_manager

from nti.app.environments.models.customers import HubspotContact
from nti.app.environments.models.customers import PersistentCustomer

from nti.app.environments.models.interfaces import InvalidSiteError

from nti.app.environments.models.utils import get_onboarding_root
from nti.app.environments.models.utils import get_customers_folder
from nti.app.environments.models.utils import get_sites_folder
from nti.app.environments.models.utils import get_hosts_folder

from nti.app.environments.views.utils import raise_json_error

logger = __import__('logging').getLogger(__name__)


class BaseView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @Lazy
    def _hubspot_client(self):
        return get_hubspot_client()

    def _get_param(self, name, params=None, required=True):
        params = self.request.params if params is None else params
        value = params.get(name)
        value = value.strip() if value else None
        if not value and required:
            raise_json_error(hexc.HTTPBadRequest,
                             'Missing {}.'.format(name),
                             field=name)
        return value

    @Lazy
    def body_params(self):
        try:
            body = self.request.json_body
        except ValueError:
            raise_json_error(hexc.HTTPBadRequest, "Invalid json body.")
        return body

    def _get_value(self, field, params=None, expected_type=None, required=False):
        if params is None:
            params = self.body_params
        val = params.get(field)
        if expected_type is not None and not isinstance(val, (expected_type, None)):
            raise_json_error(hexc.HTTPUnprocessableEntity, "Invalid {}".format(field), field)
        if required and val is None:
            raise_json_error(hexc.HTTPUnprocessableEntity,
                             'Missing {}.'.format(field),
                             field=field)
        return val.strip() if isinstance(val, str) else val


class BaseTemplateView(BaseView):

    logged_in = None
    is_dashboard_visible = None
    is_customers_visible = None
    is_sites_visible = None
    is_roles_visible = None
    is_hosts_visible = None
    role_names = ((ADMIN_ROLE, 'Admin'),
                  (ACCOUNT_MANAGEMENT_ROLE, 'Account Management'))

    @Lazy
    def _onboarding_root(self):
        return get_onboarding_root(self.request)

    def __init__(self, context, request):
        super(BaseTemplateView, self).__init__(context, request)
        if self.request.authenticated_userid:
            self.logged_in = True
            self.is_customers_visible = self.request.has_permission(ACT_READ, get_customers_folder(self._onboarding_root, request))
            self.is_sites_visible = self.request.has_permission(ACT_READ, get_sites_folder(self._onboarding_root, request))
            self.is_dashboard_visible = is_admin_or_account_manager(self.request.authenticated_userid, request)
            self.is_roles_visible = is_admin(self.request.authenticated_userid, request)
            self.is_hosts_visible = self.request.has_permission(ACT_READ, get_hosts_folder(self._onboarding_root, request))


class ObjectCreateUpdateViewMixin(object):

    def readInput(self):
        try:
            return self.request.json_body
        except ValueError:
            raise_json_error(hexc.HTTPBadRequest, "Invalid json body.")

    def _createOrUpdateObjectWithExternal(self, contained=None, external=None):
        try:
            external = self.readInput() if external is None else external
            return new_from_external_object(external) if contained is None \
                                else update_from_external_object(contained, external)
        except ValidationError as err:
            raise_json_error(hexc.HTTPUnprocessableEntity, err)
        except ComponentLookupError as err:
            raise_json_error(hexc.HTTPUnprocessableEntity, str(err))
        except Invalid as err:
            raise_json_error(hexc.HTTPUnprocessableEntity, str(err))
        except InvalidSiteError as err:
            raise_json_error(hexc.HTTPUnprocessableEntity, str(err))

    def createObjectWithExternal(self, external=None, creator=True):
        obj = self._createOrUpdateObjectWithExternal(external=external)
        if creator and self.request.authenticated_userid:
            obj.creator = self.request.authenticated_userid
        return obj

    def updateObjectWithExternal(self, contained, external=None):
        return self._createOrUpdateObjectWithExternal(contained, external)


class TableViewMixin(object):

    def _is_deletion_allowed(self, table, permission=ACT_DELETE):
        return any(bool(self.request.has_permission(permission, x)) for x in table._raw_values)


class BaseFieldPutView(BaseView, ObjectCreateUpdateViewMixin):

    def post_handler(self, field_name, original_field_value, new_field_value):
        pass

    def __call__(self):
        try:
            external = self.readInput()
            field_name = self.request.view_name
            field_value = getattr(self.context, field_name)
            new_field_value = self.createObjectWithExternal(external)

            if type(field_value) != type(new_field_value):
                original_field_value = field_value
                self.updateObjectWithExternal(self.context, {field_name: new_field_value})
            else:
                # Here failed to use copy.deepcopy, but copy.copy is enough.
                original_field_value = copy.copy(field_value)
                self.updateObjectWithExternal(field_value, external)
                self.context.updateLastModIfGreater(field_value.lastModified)

            self.post_handler(field_name, original_field_value, new_field_value)
            self._log(external)
            return {}
        except ValidationError as err:
            raise_json_error(hexc.HTTPUnprocessableEntity,
                             error=err)


def createCustomer(container, email, name, organization=None, hs_contact_vid=None):
    try:
        customer = PersistentCustomer(email=email,
                                      name=name,
                                      organization=organization)
        if hs_contact_vid:
            customer.hubspot_contact = HubspotContact(contact_vid=str(hs_contact_vid))
        container.addCustomer(customer)
    except ValueError as err:
        raise_json_error(hexc.HTTPUnprocessableEntity,
                         str(err))
    return customer


def getOrCreateCustomer(container, email, name, organization=None, hs_contact_vid=None):
    try:
        customer = container[email]
    except KeyError:
        customer = createCustomer(container, email, name, organization=organization, hs_contact_vid=hs_contact_vid)
    return customer
