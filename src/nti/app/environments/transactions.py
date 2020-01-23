from zope import component
from zope import interface

from ZODB.interfaces import IDatabase

from nti.transactions.transactions import TransactionLoop

logger = __import__('logging').getLogger(__name__)

from .interfaces import ITransactionRunner


# transaction >= 2 < 2.1.1 needs text; Transaction 1 wants
# bytes (generally). Transaction 2.1.1 and above will work with either,
# but text is preferred.
def _tx_string(s):
    return s.decode('utf-8', 'replace') if isinstance(s, bytes) else s


class _RunInTransaction(TransactionLoop):

    _connection = None

    def __init__(self, *args, **kwargs):
        self.job_name = kwargs.pop('job_name')
        self.side_effect_free = kwargs.pop('side_effect_free')
        super(_RunInTransaction, self).__init__(*args, **kwargs)

    def describe_transaction(self, *args, **kwargs):
        if self.job_name:
            return _tx_string(self.job_name)
        # Derive from the function
        func = self.handler
        name = getattr(func, '__name__', '')
        doc = getattr(func, '__doc__', '')
        if name == '_': # "Anonymous" function; transaction convention
            name = ''
        note = None
        if doc:
            note = ((name + '\n\n') if name else '') + doc
        elif name:
            note = name

        note = _tx_string(note) if note else None

        return note

    def run_handler(self, *args, **kwargs): # pylint:disable=arguments-differ
        return self.handler(*args, **kwargs)

    def setUp(self):
        # After the transaction manager has been put into explicit
        # mode, open the connection. This lets it perform certain
        # optimizations.
        db = component.getUtility(IDatabase)
        self._connection = db.open()

    def tearDown(self):
        if self._connection is not None:
            try:
                self._connection.close()
            finally:
                self._connection = None

@interface.provider(ITransactionRunner)
def run_job(func,
                    retries=0,
                    sleep=None,
                    job_name=None,
                    side_effect_free=False):
    """
    Runs the function given in `func` in a transaction 
    See :class:`.ITransactionRunner`

    :return: The value returned by the first successful invocation of `func`.
    """

    return _RunInTransaction(
        func,
        retries=retries,
        sleep=sleep,
        job_name=job_name,
        side_effect_free=side_effect_free
    )()

run_job.__doc__ = ITransactionRunner['__call__'].getDoc()