import json

from zope import component

from pyramid.threadlocal import get_current_request

from pyramid_mailer.message import Attachment

from nti.app.environments.settings import NEW_SITE_REQUEST_NOTIFICATION_EMAIL

from nti.externalization import to_external_object

from nti.mailer.interfaces import ITemplatedMailer


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
        mailer = component.getUtility(ITemplatedMailer, name='default')
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
            'url': self.site.dns_names[0],
            'site_detail_link': self.request.resource_url(self.site, '@@details')
        }
        return template_args

    def _attachments(self):
        data = to_external_object(self.site)
        data['site_detail_link'] = self.request.resource_url(self.site, '@@details')
        attachment = Attachment(filename='NewSiteRequest_{}.json'.format(self.site.id),
                                content_type="application/json",
                                data=json.dumps(data))
        return [attachment]
