import os

from zope import component
from zope import interface

from zope.component.zcml import utility

from zope.configuration.exceptions import ConfigurationError

from zope.schema import TextLine

from nti.app.environments.interfaces import IOnboardingSettings

from .interfaces import IInstallableCourseArchive

from .sites import NonPeristentFileSystemBackedInstallableCourseArchive

logger = __import__('logging').getLogger(__name__)

class IRegisterInstallableContentArchive(interface.Interface):

    name = TextLine(title="The name of the archive",
                    required=False)

    filename = TextLine(title="The file name of the archive relative to installable_content_archive_dir",
                        required=True)

def registerInstallableContentArchive(_context, filename, name=None):
    
    if name is None:
        name = os.path.splitext(filename)[0]
    archive = NonPeristentFileSystemBackedInstallableCourseArchive(name=name, filename=filename)
    try:
        if not os.path.isfile(archive.absolute_path):
            raise ConfigurationError('Archive at path %s does not exist' % archive.absolute_path)
    except KeyError:
        raise ConfigurationError('Unable to build path to archive "%s". Missing installable_content_archive_dir setting?' % name)

    utility(_context, provides=IInstallableCourseArchive, component=archive, name=name)
        
