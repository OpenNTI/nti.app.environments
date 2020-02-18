from urllib.parse import urlunparse
from urllib.parse import urljoin

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from pyramid.threadlocal import get_current_request

from pyramid_mailer.message import Attachment

from six.moves import urllib_parse

from nti.app.environments.authentication import create_auth_token_for_site

from nti.app.environments.views import AUTH_TOKEN_VIEW

from nti.app.environments.interfaces import IOnboardingSettings

from nti.app.environments.models.externalization import SITE_FIELDS_EXTERNAL_FOR_ADMIN_ONLY

from nti.app.environments.models.interfaces import ISharedEnvironment
from nti.app.environments.models.interfaces import ICustomersContainer
from nti.app.environments.models.interfaces import IDedicatedEnvironment

from nti.environments.management.interfaces import ISettings

from nti.externalization import to_external_object

from nti.externalization.interfaces import IExternalObjectRepresenter

from nti.links.externalization import render_link

from nti.links.interfaces import ILinkExternalHrefOnly

from nti.links.links import Link

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

    def __init__(self, context, request=None):
        super(SiteCreatedEmailNotifier, self).__init__(context, request)
        self.site = context

    @Lazy
    def _subject(self):
        result = 'New Site Request [%s]' % self.site.id
        settings = component.getUtility(ISettings)
        try:
            env_name = settings['general']['env_name']
        except KeyError:
            pass
        else:
            if env_name:
                result = '[%s] %s' % (env_name, result)
        return result

    def _recipients(self):
        settings = component.getUtility(IOnboardingSettings)
        return [settings['new_site_request_notification_email']]

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
    """
    Send a setup password email email to the owner in order to finish
    site setup. This will link to an `AuthToken` redemption url that will
    validate (authenticate) the token and allow the user to continue site
    setup.
    """

    _template = 'nti.app.environments:email_templates/site_setup_password'
    _subject = "It's time to setup your password!"

    def __init__(self, context, request=None):
        super(SiteSetupEmailNotifier, self).__init__(context, request)
        self.site = context

    def _recipients(self):
        return [self.site.owner.email]

    def _get_auth_link(self):
        request = self.request
        auth_token = create_auth_token_for_site(self.site.owner, self.site)
        site_url = urljoin(request.application_url, 'sites/{}'.format(self.site.id))
        link = Link(self.site.owner,
                    elements=('@@%s' % AUTH_TOKEN_VIEW,),
                    params={'token': auth_token.token,
                            'success': site_url,
                            'site': self.site.id})
        interface.alsoProvides(link, ILinkExternalHrefOnly)
        auth_token_url = render_link(link)
        return urllib_parse.urljoin(request.application_url, auth_token_url)

    def _template_args(self):
        auth_link = self._get_auth_link()
        template_args = {
            'name': self.site.owner.email,
            'password_setup_link': auth_link
        }
        return template_args


class SiteSetUpFinishedEmailNotifier(BaseEmailNotifier):

    _template = 'nti.app.environments:email_templates/site_setup_success'
    _subject = "Site has been setup successfully"

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
            'site_invite_link': self._invite_href(),
            'site_id': self.site.id,
            'dns_names': ','.join(self.site.dns_names),
            'owner_email': self.site.owner.email,
            'client_name': self.site.client_name
        }
        return template_args


class SiteSetupFailureEmailNotifier(BaseEmailNotifier):

    _template = 'nti.app.environments:email_templates/site_setup_failed'

    def __init__(self, context, request=None):
        super(SiteSetupFailureEmailNotifier, self).__init__(context, request)
        self.site = context

    @Lazy
    def _subject(self):
        result = 'Site setup failed [%s]' % self.site.id
        settings = component.getUtility(ISettings)
        try:
            env_name = settings['general']['env_name']
        except KeyError:
            pass
        else:
            if env_name:
                result = '[%s] %s' % (env_name, result)
        return result

    def _recipients(self):
        settings = component.getUtility(IOnboardingSettings)
        return [settings['site_setup_failure_notification_email']]

    def _get_env_info(self, env):
        result = ''
        if IDedicatedEnvironment.providedBy(env):
            result = '[pod=%s] (id=%s) %s' % (env.pod_id, env.host.id, env.host.host_name)
        elif ISharedEnvironment.providedBy(env):
            result = env.name
        return result

    def _template_args(self):
        state = self.site.setup_state
        env_info = self._get_env_info(self.site.environment)
        template_args = {
            'site_details_link': self.request.resource_url(self.site, '@@details'),
            'site_id': self.site.id,
            'dns_names': ','.join(self.site.dns_names),
            'exception': repr(state.exception),
            'owner_email': self.site.owner.email,
            'client_name': self.site.client_name,
            'env_info': env_info
        }
        return template_args
