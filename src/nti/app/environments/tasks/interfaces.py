from zope import interface

class ICeleryApp(interface.Interface):
    """
    A celery.Celery application. Tasks that are dispatched via the
    normal celery methods are dispatched immediately and in a non
    transactional manner. Special care must be taken when using this
    inside the broader pyramid/zope architecture, especially with respect
    to the transactional nature of the system. For example how does your usage
    of this react to TransactionLoop retries, the two phase commit process, etc.
    """
    pass
