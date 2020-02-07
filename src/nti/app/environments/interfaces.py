from zope import interface

from nti.schema.field import ValidTextLine

from zope.securitypolicy.interfaces import IPrincipalRoleManager


class IOTPGenerator(interface.Interface):
    """
    An object capable of generating a secure one-time user passphrase
    """

    def generate_passphrase():
        """
        Returns an appropriate passphrase or one time challenge
        """

class IOnboardingServer(interface.Interface):
    pass


class IOnboardingRootPrincipalRoleManager(IPrincipalRoleManager):
    pass


class ITransactionRunner(interface.Interface):
    """
    Something that runs code within a transaction, properly setting up
    the ZODB and the environment.

    Based in large part on nti.site.interfaces.ISiteTransactionRunner
    """

    def __call__(func, retries=0, sleep=None, side_effect_free=False):
        """
        Runs the function given in `func` in a transaction and application local
        site manager (defaulting to the current site manager).

        :param function func: A function of zero parameters to run. If
            it has a docstring, that will be used as the transactions
            note. A transaction will be begun before this function
            executes, and committed after the function completes. This
            function may be rerun if retries are requested, so it
            should be prepared for that.

        :keyword int retries: The number of times to retry the
            transaction and execution of `func` if
            :class:`transaction.interfaces.TransientError` is raised
            when committing. Defaults to zero (so the job runs once).
            If you specify None, an implementation-specific
            number of retries will be used.

        :keyword float sleep: If not none, then the greenlet running
            this function will sleep for this long between retry
            attempts.

        :keyword bool side_effect_free: If true (not the default), then
            the function is assummed to have no side effects that need
            to be committed; the transaction runner is free to abort/rollback
            or commit the transaction at its leisure.

        :return: The value returned by the first successful invocation of `func`.
        """


class ICollection(interface.Interface):
    pass


class ISitesCollection(ICollection):
    pass


class ISiteLinks(interface.Interface):
    """
    Important links related to a site. Typically registered as an adapter
    on ILMSSite, IRequest
    """

    application_url = ValidTextLine(title='The application url')

    complete_account_url = ValidTextLine(title='The url to follow to finish setting up an account.')

    
class ISiteDomainPolicy(interface.Interface):
    """
    An object that provides base domain, and dns_name checking.
    """
