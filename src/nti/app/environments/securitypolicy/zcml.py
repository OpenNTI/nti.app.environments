from zope import interface
from zope.principalregistry.metadirectives import IDefinePrincipalDirective as _IDefinePrincipalDirective

from zope.schema import TextLine

from zope.security.zcml import Permission
from zope.security.zcml import IPermissionDirective


class IGrantAllDirective(interface.Interface):
    """
    Grant Permissions to roles and principals and roles to principals.
    """
    principal = TextLine(title="Principal",
                         description="Specifies the Principal to be mapped.",
                         required=False)

    role = TextLine(title="Role",
                    description="Specifies the Role to be mapped.",
                    required=False)


class IGrantDirective(IGrantAllDirective):
    """
    Grant Permissions to roles and principals and roles to principals.
    """
    permission = Permission(title="Permission",
                            description="Specifies the Permission to be mapped.",
                            required=False)


class IDefineRoleDirective(IPermissionDirective):

    id = TextLine(title="Id",
                  description="Id as which this object will be known and used.",
                  required=True)


class IDefinePrincipalDirective(_IDefinePrincipalDirective):

    id = TextLine(title="Id",
                  description="Id as which this object will be known and used.",
                  required=True)

    password = TextLine( title="Password",
                         description="Specifies the Principal's Password.",
                         default='',
                         required=True)

    password_manager = TextLine(title="Password Manager Name",
                                description="Name of the password manager will be used for encode/check the password",
                                default="This Manager Does Not Exist",
                                required=False)
