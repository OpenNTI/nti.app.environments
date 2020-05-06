# -*- coding: utf-8 -*-
"""
Utilities for writing command line scripts
against this database.

Largely based off of (read: copied) nti.dataserver.utils
"""

from configparser import ConfigParser
import os
import sys
import logging
import functools

from zope import component
from zope import interface

from zope.component.hooks import setSite
from zope.component.hooks import setHooks

from zope.configuration import xmlconfig, config

from zope.dottedname import resolve as dottedname

import zope.exceptions.log
from zope.exceptions.exceptionformatter import print_exception

from pyramid_zodbconn import get_uris
from pyramid_zodbconn import db_from_uri

from nti.environments.management.config import configure_settings

from nti.app.environments.appserver import OnboardingServer

from nti.app.environments.interfaces import ITransactionRunner
from nti.app.environments.interfaces import IOnboardingServer
from nti.app.environments.interfaces import IOnboardingSettings

logger = __import__('logging').getLogger(__name__)

def _configure(self=None, set_up_packages=(), features=(), context=None, execute=True):
    """
    Configure the zope ConfigurationMachine with the provided packages and features.

    Essentially copied from nti.dataserver.utils.__init__:_configure
    """
    # zope.component.globalregistry conveniently adds
    # a zope.testing.cleanup.CleanUp to reset the globalSiteManager
    if set_up_packages:
        if context is None:
            context = config.ConfigurationMachine()
            xmlconfig.registerCommonDirectives(context)
        for feature in features:
            context.provideFeature(feature)

        for i in set_up_packages:
            __traceback_info__ = (i, self, set_up_packages)
            if isinstance(i, tuple):
                filename = i[0]
                package = i[1]
            else:
                filename = 'configure.zcml'
                package = i

            if isinstance(package, str):
                package = dottedname.resolve(package)
            context = xmlconfig.file(filename, package=package,
                                     context=context, execute=execute)
        return context


_user_function_failed = object() #marker

class _OnboardingSetupFailed(Exception): pass

def run_with_onboarding(settings=None,
                        function=None,
                        as_main=True,
                        verbose=False,
                        config_features=(),
                        xmlconfig_packages=(),
                        context=None,
                        use_transaction_runner=True,
                        logging_verbose_level=logging.INFO):
    """
    Execute the `function` in the (already running) onboarding
    environment configured by 'settings'.

    :keyword string settings: Path to an ini file to load settings from.
    :keyword function function: The function to execute, it will be passed one item, the IOnboardingRoot
    :keyword bool as_main: If ``True`` (the default) assumes this is the main portion
        of a script and configures the complete environment appropriately, including
        setting up logging.
    :keyword bool verbose: If ``True`` (*not* the default), then logging to the console
        will be at a slightly higher level.

    :keyword xmlconfig_packages: A sequence of package objects or
        strings naming packages. These will be configured, in order,
        using ZCML. The ``configure.zcml`` package from each package
        will be loaded. Instead of a package object, each item can be
        a tuple of (filename, package); in that case, the given file
        (usually ``meta.zcml``) will be loaded from the given package. ``nti.app.environments``
        will always be configured first.

    :keyword features: A sequence of strings to be added as features
        before loading the configuration. By default, this is
        nothing; ``devmode`` is one known feature name.

    :return: The results of the `function`
    """

    @functools.wraps(function)
    def run_user_fun_print_exception(root):
        """
        Run the user-given function in the environment; print exceptions
        in this env too.
        """
        try:
            return function(root)
        except Exception:
            print_exception(*sys.exc_info())
            raise

    @functools.wraps(function)  # yes, two layers, but we do wrap `function`
    def run_user_fun_transaction_wrapper():
        try:
            # Setup an IOnboardingServer to execute our function in the context of
            # We leverage utilities from pyramid_zodbconn to easily create the dbs
            # from our settings. It isn't a great separation of concerns, but it's
            # easy and could be easily removed if needed
            settings = component.getUtility(IOnboardingSettings)
            dbs = {}
            for name, uri in get_uris(settings):
                db_from_uri(uri, name, dbs)

            server = OnboardingServer(dbs)
            component.provideUtility(server, IOnboardingServer)
        except Exception:
            # Reraise something we can deal with (in collusion with run), but with the
            # original traceback. This traceback should be safe.
            exc_info = sys.exc_info()

            # TODO, nti.dataserver is raising a tuple here, which
            # isn't supported in python 3
            raise _OnboardingSetupFailed(exc_info[1])

        try:
            if use_transaction_runner:
                runner = component.getUtility(ITransactionRunner)
                return runner(run_user_fun_print_exception)
            else:
                try:
                    conn = server.root_database.open()
                    return run_user_fun_print_exception(server.root_onboarding_folder(conn))
                finally:
                    conn.close()
        except AttributeError:
            # we have seen this if the function closed the dataserver manually, but left
            # the transaction open. Committing then fails. badly.
            try:
                print_exception(*sys.exc_info())
            except:
                pass
            raise
        except Exception:
            # If we get here, we are unlikely to be able to print details from the
            # exception the transaction  will have already terminated, and any
            # __traceback_info__ objects or even the arguments to the exception are
            # possible invalid Persistent objects. Hence the need to print it up there.
            return _user_function_failed
        finally:
            component.getSiteManager().unregisterUtility(server, IOnboardingServer)
            try:
                server.close()
            except:
                pass
    
    if settings is not None:
        config = ConfigParser()
        config.read([settings])

        # Out of convenience we will unwrap the
        # app settings from the pserve configuration
        if 'app:wsgiapp' in config:
            config = config['app:wsgiapp']

        # We've become accustomed to having access to the interpolation variable
        # `here`. TODO should this be the location of the provided file?
        config['here'] = os.getcwd()
        interface.alsoProvides(config, IOnboardingSettings)
        component.getGlobalSiteManager().registerUtility(config, IOnboardingSettings)

        # Setup our lower level nti.environments.management settings. We
        # assume that if we aren't asked to set up settings that this has already been done.
        configure_settings(config)

    return run( function=run_user_fun_transaction_wrapper, as_main=as_main,
                verbose=verbose, config_features=config_features,
                xmlconfig_packages=xmlconfig_packages, context=context,
                _print_exc=False, logging_verbose_level=logging_verbose_level)

def run(function=None, as_main=True, verbose=False, config_features=(),
        xmlconfig_packages=(), context=None, _print_exc=True,
        logging_verbose_level=logging.INFO):
    """
    Execute the `function`, taking care to print exceptions and handle configuration.

    :keyword function function: The function of no parameters to execute.
    :keyword bool as_main: If ``True`` (the default) assumes this is the main portion
        of a script and configures the complete environment appropriately, including
        setting up logging. A failure to do this, or an exception raised from ``function``
        will exit the program.
    :keyword bool verbose: If ``True`` (*not* the default), then logging to the console will
        be at a slightly higher level.

    :keyword xmlconfig_packages: A sequence of package objects or
        strings naming packages. These will be configured, in order,
        using ZCML. The ``configure.zcml`` package from each package
        will be loaded. Instead of a package object, each item can be
        a tuple of (filename, package); in that case, the given file
        (usually ``meta.zcml``) will be loaded from the given package. ``nti.app.environments``
        will always be configured first.

    :keyword features: A sequence of strings to be added as features
        before loading the configuration. By default, this is
        nothing; ``devmode`` is one known feature name.

    :return: The results of the `function`
    """

    if as_main:
        log_format = '[%(name)s] %(levelname)s: %(message)s'
        logging.basicConfig(level=logging.WARN if not verbose else logging_verbose_level)
        logging.root.handlers[0].setFormatter(zope.exceptions.log.Formatter(log_format))

        setHooks()
        if context is None:
            packages = ['nti.app.environments']
            packages.extend(xmlconfig_packages)
        else:
            packages = xmlconfig_packages
        try:
            _configure(set_up_packages=packages, features=config_features, context=context)
        except Exception:
            print_exception(*sys.exc_info())
            sys.exit(5)

    if _print_exc:
        @functools.wraps(function)
        def fun():
            """
            Run the user-given function in the environment; print exceptions
            in this env too.
            """
            try:
                return function()
            except Exception:
                print_exception(*sys.exc_info())
                raise
    else:
        fun = function

    _user_ex = None
    _user_ex_str = None
    _user_ex_repr = None
    try:
        result = fun()
    except _OnboardingSetupFailed:
        raise
    except Exception as _user_ex:
        # If we get here, we are unlikely to be able to print details from the
        # exception; the transaction will have already terminated, and
        # any __traceback_info__ objects or even the arguments to the
        # exception are possible invalid Persistent objects. Hence the need to
        # print it up there.
        result = _user_function_failed
        try:
            _user_ex_str = str(_user_ex)
            _user_ex_repr = str(_user_ex_repr)
        except:
            pass

    if result is _user_function_failed:
        if as_main:
            print("Failed to execute", getattr(fun, '__name__', fun), type(_user_ex),
                  _user_ex_str, _user_ex_repr)
            sys.exit(6)
        # returning none in this case is backwards compatibile behaviour. we'd really
        # like to raise...something
        result = None

    return result

