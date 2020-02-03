#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copied from nti.datserver
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from email.utils import parseaddr
from email.utils import formataddr

from zope import component
from zope import interface

from nti.mailer.interfaces import ITemplatedMailer
from nti.mailer.interfaces import IEmailAddressable
from nti.mailer.interfaces import IMailerTemplateArgsUtility

from nti.mailer._default_template_mailer import as_recipient_list

logger = __import__('logging').getLogger(__name__)


@interface.implementer(ITemplatedMailer)
class _BaseFilteredMailer(object):

    @property
    def _default_mailer(self):
        # We look up the utility by name, because we expect
        # to be registered in sub-sites to override the main utility.
        # (Note that we use query here because zope.component arguably has
        # a bug in accessing new random attributes DURING ZCML TIME so registrations
        # are unreliable)
        return component.queryUtility(ITemplatedMailer, name='default')

    def __getattr__(self, name):
        return getattr(self._default_mailer, name)


class NextThoughtOnlyMailer(_BaseFilteredMailer):
    """
    This mailer ensures we only send email to nextthought.com
    addresses. It should only be registered in \"testing\" sites.
    """

    def _transform_recipient(self, addr):
        # support IEmailAddressable. We lose
        # VERP, but that's alright
        addr = getattr(IEmailAddressable(addr, addr), 'email', addr)
        if addr.endswith('@nextthought.com'):
            return addr

        realname, addr = parseaddr(addr)
        # XXX This blows up if we get a malformed
        # email address
        local, _ = addr.split('@')
        addr = 'dummy.email+' + local + '@nextthought.com'
        return formataddr((realname, addr))

    def _should_send_to_addr(self, addr):
        return True

    def create_simple_html_text_email(self,
                                      base_template,
                                      subject='',
                                      request=None,
                                      recipients=(),
                                      template_args=None,
                                      attachments=(),
                                      package=None,
                                      bcc=(),
                                      text_template_extension='.txt',
                                      **kwargs):
        # Implementation wise, we know that all activity
        # gets directed through this method, so we only need to filter
        # here.
        bcc = as_recipient_list(bcc) or ()
        recipients = as_recipient_list(recipients)
        filtered_recip = [self._transform_recipient(a) for a in recipients]
        filtered_recip = [
            a for a in filtered_recip if self._should_send_to_addr(a)]

        filtered_bcc = [self._transform_recipient(a) for a in bcc]
        filtered_bcc = [
            a for a in filtered_bcc if self._should_send_to_addr(a)]

        if '_level' in kwargs:
            kwargs['_level'] = kwargs['_level'] + 1
        else:
            kwargs['_level'] = 4

        if template_args:
            template_args = dict(template_args)
            for args_utility in component.getAllUtilitiesRegisteredFor(IMailerTemplateArgsUtility):
                template_args.update(args_utility.get_template_args(request))

        mailer = self._default_mailer
        return mailer.create_simple_html_text_email(base_template,
                                                    subject=subject,
                                                    request=request,
                                                    recipients=filtered_recip,
                                                    template_args=template_args,
                                                    attachments=attachments,
                                                    bcc=filtered_bcc,
                                                    package=package,
                                                    text_template_extension=text_template_extension,
                                                    **kwargs)
