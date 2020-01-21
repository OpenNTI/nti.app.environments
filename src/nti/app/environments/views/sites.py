import csv
import datetime

from nti.externalization.interfaces import LocatedExternalDict
from pyramid import httpexceptions as hexc
from pyramid.view import view_config
from zope.cachedescriptors.property import Lazy
from zope.container.interfaces import InvalidItemType
from zope.event import notify

from nti.app.environments.api.hubspotclient import get_hubspot_client
from nti.app.environments.auth import ACT_CREATE
from nti.app.environments.auth import ACT_DELETE
from nti.app.environments.auth import ACT_EDIT_SITE_ENVIRONMENT
from nti.app.environments.auth import ACT_EDIT_SITE_LICENSE
from nti.app.environments.auth import ACT_READ
from nti.app.environments.auth import ACT_REQUEST_TRIAL_SITE
from nti.app.environments.auth import ACT_UPDATE
from nti.app.environments.models.events import SiteCreatedEvent
from nti.app.environments.models.events import SiteUpdatedEvent
from nti.app.environments.models.hosts import PersistentHost
from nti.app.environments.models.interfaces import IDedicatedEnvironment
from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import ILMSSitesContainer
from nti.app.environments.models.interfaces import IOnboardingRoot
from nti.app.environments.models.interfaces import ISharedEnvironment
from nti.app.environments.models.interfaces import ISiteUsage
from nti.app.environments.models.interfaces import ITrialLicense
from nti.app.environments.models.interfaces import SITE_STATUS_PENDING
from nti.app.environments.models.interfaces import SITE_STATUS_UNKNOWN
from nti.app.environments.models.interfaces import checkEmailAddress
from nti.app.environments.models.sites import DedicatedEnvironment
from nti.app.environments.models.sites import EnterpriseLicense
from nti.app.environments.models.sites import PersistentSite
from nti.app.environments.models.sites import SharedEnvironment
from nti.app.environments.models.sites import TrialLicense
from nti.app.environments.models.utils import get_customers_folder
from nti.app.environments.models.utils import get_hosts_folder
from nti.app.environments.utils import convertToUTC
from nti.app.environments.utils import find_iface
from nti.app.environments.utils import formatDateToLocal
from nti.app.environments.utils import parseDate
from nti.app.environments.views.utils import raise_json_error

from .base import BaseFieldPutView
from .base import BaseView
from .base import ObjectCreateUpdateViewMixin
from .base import createCustomer
from .base import getOrCreateCustomer
from .base_csv import CSVBaseView

logger = __import__('logging').getLogger(__name__)


class SiteBaseView(BaseView):

    @Lazy
    def _customers(self):
        root = find_iface(self.context, IOnboardingRoot)
        folder = get_customers_folder(root)
        return folder

    @Lazy
    def _client(self):
        return get_hubspot_client()

    def _handle_owner(self, value, created=False):
        """
        Create a new customer if customer is not found and created is True.
        """
        if not value:
            raise_json_error(hexc.HTTPUnprocessableEntity, "Missing email.")

        if not checkEmailAddress(value):
            raise_json_error(hexc.HTTPUnprocessableEntity, "Invalid email.")

        folder = self._customers
        customer = folder.getCustomer(value)
        if customer is None and created is True:
            contact = self._client.fetch_contact_by_email(value)
            if contact:
                customer = createCustomer(folder,
                                          email=value,
                                          name=contact['name'],
                                          hs_contact_vid=contact['canonical-vid'])
            else:
                customer = getOrCreateCustomer(folder, value)

        if customer is None:
            raise_json_error(hexc.HTTPUnprocessableEntity,
                             "No customer found with email: {}.".format(value))

        return customer


@view_config(renderer='json',
             context=ILMSSitesContainer,
             request_method='POST',
             permission=ACT_CREATE)
class SiteCreationView(SiteBaseView, ObjectCreateUpdateViewMixin):

    def readInput(self):
        params = super(SiteCreationView, self).readInput()
        if params.get('id') is None:
            params.pop('id', None)
        params['owner'] = self._handle_owner(params.get('owner'))
        return params

    def __call__(self):
        try:
            site = self.createObjectWithExternal()
            self.context.addSite(site)
            self.request.response.status = 201
            logger.info("%s created a new site, site id: %s.",
                        self.request.authenticated_userid,
                        site.id)
            return {}
        except InvalidItemType:
            raise_json_error(hexc.HTTPUnprocessableEntity, "Invalid site type.")
        except KeyError as err:
            raise_json_error(hexc.HTTPConflict,
                             "Existing site: {}.".format(str(err)))


@view_config(renderer='json',
             context=ILMSSitesContainer,
             request_method='POST',
             permission=ACT_REQUEST_TRIAL_SITE,
             name="request_trial_site")
class RequestTrialSiteView(SiteBaseView, ObjectCreateUpdateViewMixin):

    def readInput(self):
        params = super(RequestTrialSiteView, self).readInput()

        kwargs = {}
        for attr_name in ('client_name', 'owner', 'dns_names'):
            if attr_name in params:
                kwargs[attr_name] = params[attr_name]

        kwargs['owner'] = self._handle_owner(kwargs.get('owner'), created=True)

        if not kwargs.get('dns_names') \
            or (isinstance(kwargs.get('dns_names'), (list, tuple)) and len(kwargs['dns_names'])==0):
            raise_json_error(hexc.HTTPUnprocessableEntity,
                            'Please provide at least one site url.')

        _now = datetime.datetime.utcnow()
        kwargs.update({'status': SITE_STATUS_PENDING,
                       'license': TrialLicense(start_date=_now,
                                               end_date=_now + datetime.timedelta(days=90))})
        return kwargs

    def __call__(self):
        try:
            site = PersistentSite()
            site.creator = self.request.authenticated_userid
            site = self.updateObjectWithExternal(site, self.readInput())
            self.context.addSite(site)
            # send email, etc.
            notify(SiteCreatedEvent(site))

            logger.info("%s has requested a new trial site be created, site id: %s.",
                        self.request.authenticated_userid,
                        site.id)

            self.request.response.status = 201
            return {'redirect_url': self.request.resource_url(site, '@@details')}
        except InvalidItemType:
            raise_json_error(hexc.HTTPUnprocessableEntity, "Invalid site type.")


@view_config(renderer='json',
             context=ILMSSite,
             request_method='PUT',
             permission=ACT_UPDATE)
class SiteUpdateView(SiteBaseView, ObjectCreateUpdateViewMixin):

    _allowed_fields = ('status', 'dns_names', 'owner', 'parent_site')

    def readInput(self):
        incoming = super(SiteUpdateView, self).readInput()
        res = {}
        for field in self._allowed_fields:
            if field in incoming:
                res[field] = incoming[field]

        if 'owner' in res:
            res['owner'] = self._handle_owner(res['owner'])

        return res

    def _log(self, external):
        msg = []
        for k,v in external.items():
            if k == 'owner':
                msg.append('{}={}'.format(k, v.email))
            elif k=='parent_site':
                msg.append('{}={}'.format(k, getattr(v, 'id', v)))
            else:
                msg.append('{}={}'.format(k, v))
        if msg:
            logger.info("%s has updated site (%s) with (%s).",
                        self.request.authenticated_userid,
                        self.context.id,
                        msg)

    def __call__(self):
        external = self.readInput()
        self.updateObjectWithExternal(self.context, external=external)
        self._log(external)
        return {}


class BaseSiteFieldPutView(BaseFieldPutView):

    def _log(self, external):
        msg = ",".join(["{}={}".format(k, v) for k,v in external.items() if k not in ('MimeType',)]) if external else ''
        if msg:
            logger.info("%s has updated site (%s) with (%s).",
                        self.request.authenticated_userid,
                        self.context.id,
                        msg)


@view_config(renderer='json',
             context=ILMSSite,
             request_method='PUT',
             permission=ACT_EDIT_SITE_ENVIRONMENT,
             name="environment")
class SiteEnvironmentPutView(BaseSiteFieldPutView):

    def post_handler(self, field_name, original_field_value, new_field_value):
        notify(SiteUpdatedEvent(site=self.context,
                                original_values = {field_name: original_field_value},
                                external_values = {field_name: new_field_value}))


@view_config(renderer='json',
             context=ILMSSite,
             request_method='PUT',
             permission=ACT_EDIT_SITE_LICENSE,
             name="license")
class SiteLicensePutView(BaseSiteFieldPutView):

    def _handle_date(self, name, value):
        try:
            return parseDate(value) if value is not None else None
        except:
            raise_json_error(hexc.HTTPUnprocessableEntity,
                             "Invalid date format for {}.".format(name))

    def readInput(self):
        external = super(BaseFieldPutView, self).readInput()
        external['start_date'] = self._handle_date('start_date', self._get_body_value('start_date', external, required=True))
        external['end_date'] = self._handle_date('end_date', self._get_body_value('end_date', external, required=True))
        return external


@view_config(renderer='json',
             context=ILMSSite,
             request_method='DELETE',
             permission=ACT_DELETE)
def deleteSiteView(context, request):
    container = context.__parent__
    container.deleteSite(context)
    logger.info("%s deleted site (%s).",
                request.authenticated_userid,
                context.id)
    return hexc.HTTPNoContent()


@view_config(renderer='json',
             context=ILMSSitesContainer,
             request_method='POST',
             permission=ACT_CREATE,
             name="upload_sites")
class SitesUploadCSVView(SiteBaseView, ObjectCreateUpdateViewMixin):
    """
    Create sites with csv file.
    @param delimiter, csv delimiter, default to comma.
    @param sites, filename
    """
    _default_owner_email = 'tony.tarleton@nextthought.com'
    _default_site_created = convertToUTC(datetime.datetime(2011, 4, 1, 0, 0, 0), toTimeStamp=True)
    _default_site_status = SITE_STATUS_UNKNOWN
    _default_license_start_date = convertToUTC(datetime.datetime(2011, 4, 1, 0, 0, 0))
    _default_license_end_date = convertToUTC(datetime.datetime(2029, 12, 31, 0, 0, 0))
    _default_environment_host = 'host3.4pp'

    @Lazy
    def _hosts_folder(self):
        return get_hosts_folder(request=self.request)

    def _get_or_create_hosts(self, host_name):
        try:
            hosts = self._hosts_names
        except AttributeError:
            hosts = self._hosts_names = dict()
            for x in self._hosts_folder.values():
                # This shouldn't happen in practice.
                if x.host_name in hosts:
                    raise_json_error(hexc.HTTPConflict,
                                     "Existing identical host_name in different hosts: {}.".format(x.host_name))
                hosts[x.host_name] = x

        # Create one if it does not exist.
        if host_name not in hosts:
            logger.info("Host %s not found, creating it.", host_name)
            hosts[host_name] = self._hosts_folder.addHost(PersistentHost(host_name=host_name,
                                                                         capacity=20))
        return hosts[host_name]

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

        host_name = dic['Host Machine'].strip() or self._default_environment_host
        host = self._get_or_create_hosts(host_name)
        try:
            load_factor = int(dic.get('Load Factor') or 1)
        except ValueError:
            raise ValueError("Load Factor should be integer.")
        return DedicatedEnvironment(pod_id=_id,
                                    host=host,
                                    load_factor=load_factor)

    def _add_to_dns_names(self, site, names):
        for x in site.dns_names or ():
            if x in names:
                raise_json_error(hexc.HTTPConflict,
                                 "Existing identical dns_name in different sites: {}.".format(x))
            names.add(x)

    def _get_or_update_dns_names(self, site=None):
        # Make sure no identical dns_names happen when uploading.
        try:
            _names = self._existing_site_dns_names
        except AttributeError:
            _names = self._existing_site_dns_names = set()
            for x in self.context.values():
                self._add_to_dns_names(x, _names)
        else:
            if site is not None:
                self._add_to_dns_names(site, _names)
        return _names

    def _process_dns(self, dic):
        site_url = dic['nti_site'].strip().lower()
        extra_site_url = dic['nti_URL'].strip().lower()
        res = []
        for x in (site_url, extra_site_url):
            if x and x not in res:
                if x in self._get_or_update_dns_names():
                    raise_json_error(hexc.HTTPConflict,
                                     'Existing dns_names: {}.'.format(x))
                res.append(x)
        return res

    def _process_owner(self, dic, created=True):
        email = dic['Hubspot Contact'].strip() or self._default_owner_email
        return self._handle_owner(email, created=created)

    def _add_to_parent_sites_ids(self, site, _ids):
        for _dns in site.dns_names or ():
            if _dns in _ids:
                raise_json_error(hexc.HTTPConflict,
                                 "Identical dns_name ({}) in different sites, ({} <-> {}).".format(_dns, _ids[_dns], site.id))
            _ids[_dns] = site.id

    def _get_or_update_parent_sites_ids(self, site=None):
        try:
            _ids = self._parent_sites_ids
        except AttributeError:
            _ids = self._parent_sites_ids = dict()
            for x in self.context.values():
                if x.parent_site is not None:
                    continue
                # Here we suppose all dns_names between different sites are totally unique.
                self._add_to_parent_sites_ids(x, _ids)
        else:
            # If a site has parent site,
            # we think it should not be a parent site of another site for now.
            if site is not None and site.parent_site is None:
                self._add_to_parent_sites_ids(site, _ids)
        return _ids

    def _process_parent_site(self, dns_name):
        dns_name = dns_name.strip() if dns_name else None
        if not dns_name:
            return None

        site_ids = self._get_or_update_parent_sites_ids()
        site_id = site_ids.get(dns_name)
        site = self.context.get(site_id) if site_id else None
        if not site:
            raise_json_error(hexc.HTTPUnprocessableEntity,
                             "Parent site not found: {}.".format(dns_name))
        return site

    def _process_row(self, row, createdCustomer=True, remoteUser=None):
        try:
            kwargs = dict()
            kwargs['owner'] = self._process_owner(row, created=createdCustomer)
            kwargs['license'] = self._process_license(row)
            kwargs['environment'] = self._process_environment(row)
            kwargs['dns_names'] = self._process_dns(row)
            kwargs['status'] = row['Status'] or self._default_site_status
            kwargs['parent_site'] = self._process_parent_site(row['Parent Site'])

            createdTime = parseDate(row['Site Created Date'], toTimeStamp=True) if row['Site Created Date'] else self._default_site_created

            try:
                # Use pod_id as the site id if it's dedicated environment,
                # this may conflicts, for now just raise error.
                siteId = kwargs['environment'].pod_id if isinstance(kwargs['environment'], DedicatedEnvironment) else None
                site = PersistentSite()
                site.createdTime = createdTime
                site.creator = remoteUser or self.request.authenticated_userid
                site = self.updateObjectWithExternal(site, kwargs)
                self.context.addSite(site, siteId=siteId)
                self._get_or_update_dns_names(site)
                self._get_or_update_parent_sites_ids(site)
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

        remoteUser = self.request.authenticated_userid

        logger.info("Begin processing sites creation.")
        contents = field.value.decode('utf-8')
        contents = [x for x in contents.splitlines() if not self._is_empty(x)]
        rows = csv.DictReader(contents, delimiter=delimiter)

        total = 0
        for row in rows:
            logger.debug('Processing line %s', total+1)
            self._process_row(row, createdCustomer=createdCustomerIfNotExists, remoteUser=remoteUser)
            total += 1

        result = dict()
        result['total_sites'] = total
        logger.info("End processing sites creation.")
        return result


@view_config(context=ILMSSitesContainer,
             request_method='GET',
             permission=ACT_READ,
             name="export_sites")
class SiteCSVExportView(CSVBaseView):

    def header(self, params):
        return ['Site', 'Owner', 'License', 'License Start Date', 'License End Date',
                'Environment', 'Host Machine',
                'Status', 'DNS Names', 'Created Time', 'Last Modified', 'Parent Site']

    def filename(self):
        return 'sites.csv'

    def records(self, params):
        return self.context.values()

    def _format_env(self, envir):
        if envir is None:
            return ''
        return "{}:{}".format('shared' if ISharedEnvironment.providedBy(envir) else 'dedicated',
                              envir.name if ISharedEnvironment.providedBy(envir) else envir.pod_id)

    def row_data_for_record(self, record):
        return {'Site': record.id,
                'Owner': record.owner.email,
                'License': 'trial' if ITrialLicense.providedBy(record.license) else 'enterprise',
                'License Start Date': formatDateToLocal(record.license.start_date),
                'License End Date': formatDateToLocal(record.license.end_date),
                'Environment': self._format_env(record.environment),
                'Host Machine': record.environment.host.host_id if IDedicatedEnvironment.providedBy(record.environment) else '',
                'Status': record.status,
                'DNS Names': ','.join(record.dns_names),
                'Created Time': formatDateToLocal(record.created),
                'Last Modified': formatDateToLocal(record.lastModified),
                'Parent Site': record.parent_site.id if record.parent_site else ''}


@view_config(renderer='rest',
             context=ILMSSitesContainer,
             request_method='POST',
             permission=ACT_UPDATE,
             name="usages")
class SiteUsagesBulkUpdateView(BaseView, ObjectCreateUpdateViewMixin):

    def __call__(self):
        incoming = self.readInput()
        if not isinstance(incoming, list):
            incoming = [incoming]

        try:
            for item in incoming:
                site_id = item.pop('site_id')
                if not site_id or not isinstance(site_id, str):
                    raise ValueError("site_id should be non-empty string: {}.".format(site_id))

                site = self.context.get(site_id)
                if site is None:
                    raise ValueError("No site found: {}.".format(site_id))

                usage = ISiteUsage(site)
                self.updateObjectWithExternal(usage, item)
        except KeyError:
            raise_json_error(hexc.HTTPUnprocessableEntity, 'Invalid data format.')
        except ValueError as err:
            raise_json_error(hexc.HTTPUnprocessableEntity, str(err))

        result = LocatedExternalDict()
        result.__name__ = self.context.__name__
        result.__parent__ = self.context.__parent__
        result['total_updated'] = len(incoming)
        return result
