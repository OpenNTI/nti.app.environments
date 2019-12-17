import csv
import datetime

from pyramid.view import view_config
from pyramid import httpexceptions as hexc

from zope.cachedescriptors.property import Lazy

from zope.schema._bootstrapinterfaces import RequiredMissing
from zope.schema._bootstrapinterfaces import ValidationError

from nti.app.environments.models.utils import get_customers_folder
from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import ILMSSitesContainer
from nti.app.environments.models.interfaces import IOnboardingRoot
from nti.app.environments.models.interfaces import SITE_STATUS_UNKNOWN

from nti.app.environments.models.sites import DedicatedEnvironment
from nti.app.environments.models.sites import SharedEnvironment
from nti.app.environments.models.sites import PersistentSite
from nti.app.environments.models.sites import TrialLicense
from nti.app.environments.models.sites import EnterpriseLicense

from nti.app.environments.utils import find_iface
from nti.app.environments.views.base import BaseView
from nti.app.environments.views.utils import raise_json_error
from nti.app.environments.views.utils import parseDate
from nti.app.environments.views.utils import convertToUTC

from nti.app.environments.auth import ACT_CREATE
from nti.app.environments.auth import ACT_DELETE
from nti.app.environments.auth import ACT_UPDATE 

from nti.app.environments.api.hubspotclient import get_hubspot_client

from .base import createCustomer
from .base import getOrCreateCustomer

logger = __import__('logging').getLogger(__name__)


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


@view_config(renderer='json',
             context=ILMSSitesContainer,
             request_method='POST',
             permission=ACT_CREATE,
             name="upload_sites")
class SitesUploadCSVView(SiteBaseView):
    """
    Create sites with csv file.
    @param delimiter, csv delimiter, default to comma.
    @param sites, filename
    """
    _default_owner_email = 'tony.tarleton@nextthought.com'
    _default_site_created = convertToUTC(datetime.datetime(2011, 4, 1, 0, 0, 0))
    _default_site_status = SITE_STATUS_UNKNOWN
    _default_license_start_date = convertToUTC(datetime.datetime(2011, 4, 1, 0, 0, 0))
    _default_license_end_date = convertToUTC(datetime.datetime(2029, 12, 31, 0, 0, 0))
    _default_environment_host = 'host3.4pp'

    @Lazy
    def _customers(self):
        root = find_iface(self.context, IOnboardingRoot)
        folder = get_customers_folder(root)
        return folder

    @Lazy
    def _client(self):
        return get_hubspot_client()

    def _process_license(self, dic):
        licenseType = dic['License Type'].strip()
        start_date = parseDate(dic['LicenseStartDate'].strip()) if dic.get('LicenseStartDate') else self._default_license_start_date
        end_date = parseDate(dic['LicenseEndDate'].strip()) if dic.get('LicenseEndDate') else self._default_license_end_date
        if licenseType == 'trial':
            return TrialLicense(start_date=start_date,
                                end_date=end_date)
        elif licenseType == 'enterprise':
            return EnterpriseLicense(start_date=start_date,
                                     end_date=end_date)
        elif licenseType == 'internal':
            return EnterpriseLicense(start_date=start_date,
                                     end_date=end_date)
        raise ValueError("Unknown license type: {}.".format(licenseType))

    def _process_environment(self, dic):
        contents = dic['Environment'].split(':')
        if len(contents) != 2:
            raise ValueError('Invalid Environment.')
        _type, _id = contents[0].strip(), contents[1].strip()
        if _type not in ('shared', 'dedicated'):
            raise ValueError("Invalid Environment.")

        if _type == 'shared':
            return SharedEnvironment(name=_id)

        host = dic['Host Machine'].strip() or self._default_environment_host
        return DedicatedEnvironment(pod_id=_id,
                                    host=host)

    def _process_dns(self, dic):
        site_url = dic['nti_site'].strip()
        extra_site_url = dic['nti_URL'].strip() or None
        return [site_url, extra_site_url] if extra_site_url else [site_url]

    def _process_owner(self, dic, created=True):
        email = dic['Hubspot Contact'].strip() or self._default_owner_email
        customer = self._customers.getCustomer(email)
        if customer is None:
            if created is False:
                raise ValueError("No customer found for email: {}.".format(email))
            contact = self._client.fetch_contact_by_email(email)
            if contact:
                customer = createCustomer(self._customers,
                                          email=email,
                                          name=contact['name'],
                                          hs_contact_vid=contact['canonical-vid'])
            else:
                customer = getOrCreateCustomer(self._customers, email)
        return customer

    def _process_row(self, row, createdCustomer=True):
        try:
            kwargs = dict()
            kwargs['owner'] = self._process_owner(row, created=createdCustomer)
            kwargs['license'] = self._process_license(row)
            kwargs['environment'] = self._process_environment(row)
            kwargs['dns_names'] = self._process_dns(row)
            kwargs['created'] = parseDate(row['Site Created Date']) if row['Site Created Date'] else self._default_site_created
            kwargs['status'] = row['Status'] or self._default_site_status

            try:
                # Use pod_id as the site id if it's dedicated environment,
                # this may conflicts, for now just raise error.
                siteId = kwargs['environment'].pod_id if isinstance(kwargs['environment'], DedicatedEnvironment) else None
                site = PersistentSite(**kwargs)
                self.context.addSite(site, siteId=siteId)
            except KeyError as e:
                raise ValueError("Existing site id: {}.".format(siteId))
        except KeyError as e:
            raise_json_error(hexc.HTTPUnprocessableEntity, 'Missing field {}.'.format(str(e)))
        except ValueError as e:
            raise_json_error(hexc.HTTPUnprocessableEntity, str(e))

    def _is_empty(self, line):
        return not line or line == len(line) * ','

    def __call__(self):
        post = self.request.POST

        createdCustomerIfNotExists = post.get('created_customer') or True
        delimiter = str('\t') if post.get("delimiter") == "tab" else str(',')
        field = post.get('sites')
        if field is None or not field.file:
            raise_json_error(hexc.HTTPUnprocessableEntity, "Must provide a named file.")

        logger.info("Begin processing sites creation.")
        contents = field.value.decode('utf-8')
        contents = [x for x in contents.splitlines() if not self._is_empty(x)]
        rows = csv.DictReader(contents, delimiter=delimiter)

        total = 0
        skipped = 0
        for row in rows:
            logger.debug('Processing line %s', total+1)
            if row['Parent Site']:
                skipped += 1
                continue
            self._process_row(row, createdCustomer=createdCustomerIfNotExists)
            total += 1

        result = dict()
        result['total_sites'] = total
        result['skip_sites'] = skipped
        logger.info("End processing sites creation.")
        return result
