#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Decorator helpers for :mod:`nti.externalization` that are
used when externalizing for a remote client.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from abc import ABCMeta
from abc import abstractmethod

from zope import interface

from zope.cachedescriptors.property import Lazy
from zope.cachedescriptors.property import readproperty

from zope.location.interfaces import ILocation

from nti.app.authentication import get_remote_user

from nti.externalization.interfaces import StandardExternalFields

from nti.links.links import Link

from nti.ntiids.oids import to_external_ntiid_oid

from nti.property.property import alias

StandardExternalFields_LINKS = StandardExternalFields.LINKS

logger = __import__('logging').getLogger(__name__)


class AbstractRequestAwareDecorator(object):
    """
    A base class providing support for decorators that
    are request-aware. Subclasses can be registered
    as either :class:`.IExternalMappingDecorator` objects
    or :class:`.IExternalObjectDecorator` objects and this
    class will unify the interface.
    """

    __metaclass__ = ABCMeta

    def __init__(self, unused_context, request):
        self.request = request

    def _predicate(self, unused_context, unused_result):
        """
        You may implement this method to check a precondition, return False if no decoration.
        """
        return True

    def decorateExternalMapping(self, context, result):
        if self._predicate(context, result):
            self._do_decorate_external(context, result)

    decorateExternalObject = alias('decorateExternalMapping')

    @abstractmethod
    def _do_decorate_external(self, context, result):
        """
        Implement this to do your actual decoration
        """
        raise NotImplementedError()


class AbstractAuthenticatedRequestAwareDecorator(AbstractRequestAwareDecorator):
    """
    A base class that ensures authenticated requests.

    When you subclass, remember to call this class's
    :meth:`_predicate`. For convenience and speed (to avoid needing
    to use ``super``) that can also be spelled as
    :attr:`_is_authenticated`

    """

    # Notice these two methods have the same implementation
    # but do not call each other, for speed.
    def _predicate(self, unused_context, unused_result):
        return bool(self.authenticated_userid)

    @Lazy
    def _is_authenticated(self):
        return bool(self.authenticated_userid)

    @Lazy
    def remoteUser(self):
        return get_remote_user(self.request)

    @readproperty
    def authenticated_userid(self):
        try:
            return self.request.authenticated_userid
        except AttributeError:
            # request was None, or the authentication policy was
            # not present
            return None


class AbstractTwoStateViewLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):
    """
    A decorator which checks the state of a predicate of two functions
    (the object and username) and adds one of two links depending on
    the value of the predicate. The links are to views on the original
    object having the same name as the ``rel`` attribute of the
    generated link.

    Subclasses define the following attributes:

    .. py:attribute:: link_predicate

            The function of two paramaters (object and username) to call

    .. py:attribute:: false_view

            The name of the view to use when the predicate is false.

    .. py:attribute:: true_view

            The name of the view to use when the predicate is true.

    If the resolved view name (i.e., one of ``false_view`` or
    ``true_view``) is ``None``, then no link will be added.

    .. note:: This may cause the returned objects to be user-specific,
            which may screw with caching.
    """

    false_view = None
    true_view = None
    link_predicate = None

    def _do_decorate_external(self, context, mapping):
        """
        :param extra_elements: A tuple of elements that are unconditionally added to
                the generated link.
        """
        return self._do_decorate_external_link(context, mapping)

    def _do_decorate_external_link(self, context, mapping, extra_elements=()):
        """
        :param extra_elements: A tuple of elements that are unconditionally added to
                the generated link.
        """
        current_username = self.authenticated_userid

        # We only do this for parented objects. Otherwise, we won't
        # be able to render the links. A non-parented object is usually
        # a weakref to an object that has been left around
        # in somebody's stream
        if not context.__parent__:
            return

        predicate_passed = self.link_predicate(context, current_username)
        # We're assuming that because you can see it, you can (un)like it.
        # this matches the views

        rel = self.true_view if predicate_passed else self.false_view
        if rel is None:  # Disabled in this case
            return

        # Use the OID NTIID rather than the 'physical' path because
        # the 'physical' path may not quite be traversable at this
        # point...plus, it's more semantically correct because the OID
        # path points to this exact object, even if moved/renamed
        target_ntiid = to_external_ntiid_oid(context)
        if target_ntiid is None:
            logger.warn("Failed to get ntiid; not adding link %s for %s",
                        rel, context)
            return

        link = Link(target_ntiid,
                    rel=rel,
                    elements=('@@' + rel,) + extra_elements)
        interface.alsoProvides(link, ILocation)
        link.__name__ = ''
        link.__parent__ = context

        _links = mapping.setdefault(StandardExternalFields_LINKS, [])
        _links.append(link)
        return link
