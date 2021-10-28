from zope import component
from zope import interface

from pyramid.threadlocal import get_current_request

from nti.mailer.interfaces import ITemplatedMailer

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
