from urllib.parse import urlunparse
from urllib.parse import urljoin

from zope import component

from zope.cachedescriptors.property import Lazy

from pyramid.threadlocal import get_current_request

from pyramid_mailer.message import Attachment

from nti.app.environments.settings import NEW_SITE_REQUEST_NOTIFICATION_EMAIL
from nti.app.environments.settings import SITE_SETUP_FAILURE_NOTIFICATION_EMAIL

from nti.app.environments.models.externalization import SITE_FIELDS_EXTERNAL_FOR_ADMIN_ONLY

from nti.app.environments.models.interfaces import ICustomersContainer

from nti.externalization import to_external_object

from nti.externalization.interfaces import IExternalObjectRepresenter

from nti.mailer.interfaces import ITemplatedMailer

from nti.traversal.traversal import find_interface


def _mailer():
    return component.getUtility(ITemplatedMailer, name='default')


class BaseEmailNotifier(object):

    _template = None
    _subject = None

    def __init__(self, context, request=None):
        self.context = context
        self.request = request or get_current_request()

    def _recipients(self):
        return []

    def _template_args(self):
        return {}

    def _attachments(self):
        return None

    def notify(self):
        mailer = _mailer()
        mailer.queue_simple_html_text_email(self._template,
                                            subject=self._subject,
                                            recipients=self._recipients(),
                                            template_args=self._template_args(),
                                            attachments=self._attachments(),
                                            text_template_extension='.mak')


class SiteCreatedEmailNotifier(BaseEmailNotifier):

    _template = 'nti.app.environments:email_templates/new_site_request'
    _subject = 'New Site Request'

    def __init__(self, context, request=None):
        super(SiteCreatedEmailNotifier, self).__init__(context, request)
        self.site = context

    def _recipients(self):
        return [NEW_SITE_REQUEST_NOTIFICATION_EMAIL]

    def _template_args(self):
        template_args = {
            'requesting_user': self.request.authenticated_userid,
            'site_id': self.site.id,
            'client': self.site.client_name,
            'email': self.site.owner.email,
            'url': self.site.dns_names[0] if self.site.dns_names else '',
            'site_detail_link': self.request.resource_url(self.site, '@@details')
        }
        return template_args

    def _attachments(self):
        external = to_external_object(self.site)
        external['site_detail_link'] = self.request.resource_url(self.site, '@@details')
        for attr_name in SITE_FIELDS_EXTERNAL_FOR_ADMIN_ONLY:
            if attr_name not in external:
                external[attr_name] = to_external_object(getattr(self.site, attr_name))

        data = component.getUtility(IExternalObjectRepresenter, name='json').dump(external)
        attachment = Attachment(filename='NewSiteRequest_{}.json'.format(self.site.id),
                                content_type="application/json",
                                data=data)
        return [attachment]


class SiteSetupEmailNotifier(BaseEmailNotifier):

    _template = 'nti.app.environments:email_templates/site_setup_completed'
    _subject = "It's time to setup your password!"

    def __init__(self, context, request=None):
        super(SiteSetupEmailNotifier, self).__init__(context, request)
        self.site = context

    def _recipients(self):
        return [self.site.owner.email]

    def _template_args(self):
        template_args = {
            'name': self.site.owner.email,
            'site_domain_link': "http://{dns_name}/".format(dns_name=self.site.dns_names[0]),
            'password_setup_link': urljoin(self.request.application_url, 'sites/{}'.format(self.site.id))
        }
        return template_args


class SiteSetUpFinishedEmailNotifier(BaseEmailNotifier):

    _template = 'nti.app.environments:email_templates/site_setup_success'
    _subject = "Your site is set up successfully"

    def __init__(self, context, request=None):
        super(SiteSetUpFinishedEmailNotifier, self).__init__(context, request)
        self.site = context

    @Lazy
    def _customers_folder(self):
        return find_interface(self.site.owner, ICustomersContainer)

    def _recipients(self):
        return [self.site.creator]

    def _name(self):
        creator = self.site.creator
        customer = self._customers_folder.getCustomer(creator)
        return customer.name if customer is not None else creator

    def _invite_href(self):
        target_app_url = urlunparse(('https', self.site.dns_names[0], '/app', None, None, None))
        return urljoin(target_app_url,
                       self.site.setup_state.site_info.admin_invitation)

    def _template_args(self):
        template_args = {
            'name': self._name(),
            'site_details_link': self.request.resource_url(self.site, '@@details'),
            'site_invite_link': self._invite_href()
        }
        return template_args


class SiteSetupFailureEmailNotifier(BaseEmailNotifier):

    _template = 'nti.app.environments:email_templates/site_setup_failed'
    _subject = "Site setup failed"

    def __init__(self, context, request=None):
        super(SiteSetupEmailNotifier, self).__init__(context, request)
        self.site = context
        self._subject = 'Site setup failed [%s]' % context.id

    def _recipients(self):
        return [SITE_SETUP_FAILURE_NOTIFICATION_EMAIL]

    def _template_args(self):
        state = self.site.setup_state
        site_info = state.site_info
        template_args = {
            'name': self.site.owner.email,
            'dns_name': site_info.dns_name,
            'exception': state.exception,
            'host': state.site_info.host,
            'owner': self.site.owner,
            'environment': self.site.environment
        }
        return template_args
