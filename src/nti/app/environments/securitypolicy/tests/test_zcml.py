import unittest

from io import BytesIO

from zope.configuration.xmlconfig import xmlconfig

from zope.securitypolicy.interfaces import Allow

from zope.securitypolicy.principalrole import principalRoleManager


class TestZcml(unittest.TestCase):

    def test_directives(self):
        zcml = """
        <configure  xmlns="http://namespaces.zope.org/zope"
                    xmlns:zcml="http://namespaces.zope.org/zcml"
                    xmlns:sp="http://nextthought.com/ntp/securitypolicy">

            <include file="meta.zcml" package="zope.component" />
            <include file="meta.zcml" package="zope.security" />
            <include file="meta.zcml" package="nti.app.environments.securitypolicy" />

            <include package="zope.principalregistry" />

            <permission
                id="nti.actions.view_reports"
                title="View reports" />

            <sp:role
                id="nti.roles.admin"
                title="Globally accessible report viewing"/>

            <sp:grant
                permission="nti.actions.view_reports"
                role="nti.roles.admin" />

            <sp:principal
                id="grey.allman@nextthought.com"
                login="grey.allman@nextthought.com"
                title="Grey Allman" />

            <sp:grant principal="grey.allman@nextthought.com"
                      role="nti.roles.admin" />

        </configure>"""

        xmlconfig(BytesIO((zcml).encode("ascii")))

        res = principalRoleManager.getRolesForPrincipal('grey.allman@nextthought.com')
        self.assertEqual(res, [('nti.roles.admin', Allow)])
