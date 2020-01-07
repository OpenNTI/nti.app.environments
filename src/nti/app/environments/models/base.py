from zope.container.constraints import checkObject

from zope.container.folder import Folder


class BaseFolder(Folder):

    def _setitemf(self, key, value):
        checkObject(self, key, value)
        super(BaseFolder, self)._setitemf(key, value)
