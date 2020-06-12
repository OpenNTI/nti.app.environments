from zope import interface

from zope.publisher.interfaces.browser import IBrowserRequest

from zope.publisher.interfaces import ISkinType

class IEndUserBrowserRequest(IBrowserRequest):
    """
    A browser request we know to be end users (i.e. not admin tools)
    """
