#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Adapters commonly useful during various rendering pipelines.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import six

from zc.displayname.adapters import convertName
from zc.displayname.adapters import DefaultDisplayNameGenerator

from zc.displayname.interfaces import IDisplayNameGenerator

from pyramid.interfaces import IRequest

from zope import component
from zope import interface

from nti.contentfragments.interfaces import IPlainTextContentFragment

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ITitledContent

from nti.dataserver.users.interfaces import IFriendlyNamed

from nti.ntiids.ntiids import is_valid_ntiid_string

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IDisplayNameGenerator)
@component.adapter(IUser, IRequest)
class UserDisplayNameGenerator(object):
    """
    Get the display name for a user.
    """

    def __init__(self, context, unused_request):
        self.context = context

    def __call__(self, unused_maxlength=None):
        names = IFriendlyNamed(self.context)
        return names.alias or names.realname or self.context.username


@component.adapter(ITitledContent, IRequest)
class TitledContentDisplayNameGenerator(DefaultDisplayNameGenerator):
    """
    Our :class:`.ITitledDescribedContent` is an implementation of
    :class:`.IDCDescriptiveProperties`, but its superclass,
    :class:`.ITitledContent` is not. This display generator
    fixes that: if the object actually has a title, use it, otherwise,
    let the default kick in (if the object can be adapted to
    ``IDCDescriptiveProperties`` use that title, otherwise use the name).
    """

    def __call__(self, maxlength=None):
        title = getattr(self.context, 'title', None)
        if title:
            return convertName(title, self.request, maxlength)

        # No title. Lets try to find a body snippet
        bodylen = maxlength or 30
        body = getattr(self.context, 'body', None)
        if body and isinstance(body[0], six.string_types):
            text = IPlainTextContentFragment(body[0])
            if text:
                return convertName(text, self.request, bodylen)

        default = DefaultDisplayNameGenerator.__call__(self, maxlength)
        if is_valid_ntiid_string(default):
            # Snap, got the ugly name. We never want to display that.
            return u''
