from pyramid.view import view_config
from pyramid import httpexceptions as hexc

from zope.cachedescriptors.property import Lazy

from nti.app.environments.models.utils import get_customers_folder
from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import ILMSSitesContainer
from nti.app.environments.models.interfaces import IOnboardingRoot

from nti.app.environments.models.sites import DedicatedEnvironment
from nti.app.environments.models.sites import SharedEnvironment
from nti.app.environments.models.sites import PersistentSite
from nti.app.environments.models.sites import TrialLicense
from nti.app.environments.models.sites import EnterpriseLicense

from nti.app.environments.utils import find_iface
from nti.app.environments.views.base import BaseView
from nti.app.environments.views.utils import raise_json_error
from nti.app.environments.views.utils import parseDate

from nti.app.environments.auth import ACT_CREATE
from nti.app.environments.auth import ACT_DELETE
from nti.app.environments.auth import ACT_UPDATE 
from zope.schema._bootstrapinterfaces import RequiredMissing
from zope.schema._bootstrapinterfaces import ValidationError


class SiteBaseView(BaseView):

    @Lazy
    def params(self):
        try:
            body = self.request.json_body
        except ValueError:
            raise_json_error(hexc.HTTPBadRequest, "Invalid json body.")
        return body

    def _get_value(self, field, params=None, expected_type=None):
        if params is None:
            params = self.params
        val = params.get(field)
        if expected_type is not None and not isinstance(val, (expected_type, None)):
            raise_json_error(hexc.HTTPUnprocessableEntity, "Invalid {}".format(field), field)
        return val.strip() if isinstance(val, str) else val

    def _handle(self, name, value=None):
        if not value:
            raise_json_error(hexc.HTTPUnprocessableEntity, "Missing required field: {}.".format(name))
        return value

    def _handle_owner(self, name, value=None):
        if not value:
            raise_json_error(hexc.HTTPUnprocessableEntity, "Missing required field: email.")

        root = find_iface(self.context, IOnboardingRoot)
        folder = get_customers_folder(root)
        customer = folder.getCustomer(value)
        if customer is None:
            raise_json_error(hexc.HTTPUnprocessableEntity, "Invalid email.")
        return customer

    def _handle_env(self, name, value):
        value = value or {}
        if not isinstance(value, dict):
            raise_json_error(hexc.HTTPUnprocessableEntity, "Invalid {}.".format(name))
        type_ = self._get_value('type', value)
        if type_ not in ('shared', 'dedicated'):
            raise_json_error(hexc.HTTPUnprocessableEntity,
                             "Invalid environment.",
                             name)

        if type_ == 'shared':
            return SharedEnvironment(name=self._get_value('name', value))
        else:
            return DedicatedEnvironment(pod_id=self._get_value('pod_id', value),
                                        host=self._get_value('host', value))

    def _handle_license(self, name, value):
        value = value or {}
        if not isinstance(value, dict):
            raise_json_error(hexc.HTTPUnprocessableEntity, "Invalid {}.".format(name))
        type_ = self._get_value('type', value)
        if type_ not in ('trial', 'enterprise'):
            raise_json_error(hexc.HTTPUnprocessableEntity,
                             "Invalid license.",
                             name)

        kwargs = {'start_date': self._handle_date('start_date', value.get('start_date')),
                  'end_date': self._handle_date('end_date', value.get('end_date'))}
        return TrialLicense(**kwargs) if type_ == 'trial' else EnterpriseLicense(**kwargs) 

    def _handle_date(self, name, value=None):
        try:
            return parseDate(value) if value else None
        except:
            raise_json_error(hexc.HTTPUnprocessableEntity, "Invalid date format for {}".format(name))

    def _generate_kwargs_for_site(self, params=None, allowed = ()):
        params = self.params if params is None else params
        kwargs = {}
        site_id = self._get_value('site_id', params)
        if site_id:
            kwargs['id'] = site_id
        for attr_name, _handle in (('owner', self._handle_owner),
                                   ('environment', self._handle_env),
                                   ('license', self._handle_license),
                                   ('status', self._handle),
                                   ('created', self._handle_date),
                                   ('dns_names', self._handle)):
            if attr_name in params and (not allowed or attr_name in allowed):
                attr_val = params[attr_name]
                if isinstance(attr_val, str):
                    attr_val = attr_val.strip()
                kwargs[attr_name] = _handle(attr_name, attr_val) if _handle else attr_val
        return kwargs


@view_config(renderer='json',
             context=ILMSSitesContainer,
             request_method='POST',
             permission=ACT_CREATE)
class SiteCreationView(SiteBaseView):

    def _create_site(self):
        try:
            kwargs = self._generate_kwargs_for_site()
            site = PersistentSite(**kwargs)
            return site
        except RequiredMissing as e:
            raise_json_error(hexc.HTTPUnprocessableEntity,"Missing required field: {}".format(e))
        except ValidationError as e:
            raise_json_error(hexc.HTTPUnprocessableEntity, str(type(e).__name__))

    def __call__(self):
        site = self._create_site()
        self.context.addSite(site)
        self.request.response.status = 201
        return {}


@view_config(renderer='json',
             context=ILMSSite,
             request_method='PUT',
             permission=ACT_UPDATE)
class SiteUpdateView(SiteBaseView):

    def __call__(self):
        context = self.context
        kwargs = self._generate_kwargs_for_site(allowed=('status', 'dns_names'))
        if kwargs:
            for attr_name, attr_val in kwargs.items():
                if getattr(context, attr_name) != attr_val:
                    setattr(context, attr_name, attr_val)
        return kwargs


@view_config(renderer='json',
             context=ILMSSite,
             request_method='DELETE',
             permission=ACT_DELETE)
def deleteSiteView(context, request):
    container = context.__parent__
    container.deleteSite(context)
    return hexc.HTTPNoContent()
