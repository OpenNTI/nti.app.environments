import os

from pyramid.interfaces import ITranslationDirectories

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.i18n.interfaces import ITranslationDomain


@interface.implementer(ITranslationDirectories)
class ZopeTranslationDirectories(object):
    """
    Implements the readable contract of Pyramid's translation directory
    list by querying for the zope translation domain objects. This way
    we don't have to repeat the configuration.

    .. note:: This queries just once, the first time it is used.

    .. note:: We lose the order or registrations, if that mattered.
    """

    def __iter__(self):
        return iter(self._dirs)

    def __repr__(self):
        return repr(list(self))

    @Lazy
    def _dirs(self):
        dirs = []
        domains = component.getAllUtilitiesRegisteredFor(ITranslationDomain)
        for domain in domains:
            for paths in domain.getCatalogsInfo().values():
                # The catalog info is a dictionary of language to [file]
                if len(paths) == 1 and paths[0].endswith('.mo'):
                    path = paths[0]
                    # strip off the file, go to the directory containing the
                    # language directories
                    path = os.path.sep.join(path.split(os.path.sep)[:-3])
                    if path not in dirs:
                        dirs.append(path)
        return dirs
