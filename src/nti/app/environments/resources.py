from pyramid.interfaces import IRootFactory

from zope import component
from zope.cachedescriptors.property import Lazy


class AdminResource(object):
    """
    See https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/hybrid.html#hybrid-chapter
    https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/resources.html#overriding-resource-url-generation
    """
    def __init__(self, request):
        self.request = request

    @Lazy
    def root(self):
        return component.getUtility(IRootFactory)(self.request)

    def __getitem__(self, name):
        return self.root.get(name)


def admin_root_factory(request):
    return AdminResource(request)
