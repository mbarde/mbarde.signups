# -*- coding: utf-8 -*-
from mbarde.signups import _
from mbarde.signups.utils import deferRename
from mbarde.signups.utils import emailToPersonId
from mbarde.signups.utils import getAllExtraFields
from plone import api
from plone.autoform import directives as form
from plone.dexterity.content import Item
from plone.locking.interfaces import ILockable
from plone.supermodel import model
from Products.CMFCore.permissions import ModifyPortalContent
from zope import schema
from zope.interface import implementer


class IUTPerson(model.Schema):

    email = schema.TextLine(title=_("E-Mail"), required=True)

    prename = schema.TextLine(title=_("Prename"), required=True)

    surname = schema.TextLine(title=_("Surname"), required=True)

    note = schema.TextLine(title=_("Note"), required=False)

    signedUpWhileLoggedIn = schema.Bool(
        title=_("Signed up while logged in"),
        description=_(
            "Whether this person signed up while being logged in, as opposed to "
            "anonymously/externally."
        ),
        required=False,
        default=False,
    )
    form.omitted("signedUpWhileLoggedIn")


@implementer(IUTPerson)
class UTPerson(Item):

    # extra infos depend on additional form specified in SignupSheet (`extraFieldsForm`)
    # and get stored as attributes of UTPerson object
    def getExtraInfo(self):
        extraInfo = []
        fields = getAllExtraFields(self)
        for field in fields:
            value = getattr(self, field["name"], "")
            extraInfo.append((field["label"], value))
        return extraInfo

    def getExtraInfoAsString(self):
        extraInfo = []
        fields = getAllExtraFields(self)
        for field in fields:
            value = getattr(self, field["name"], False)
            if value:
                extraInfo.append(field["label"] + ": " + value)
        return "\n".join(extraInfo)


# set id & title on creation and modification
def autoSetID(person, event):
    # only managers are allowed to create / modify persons via forms
    if not api.user.has_permission(ModifyPortalContent, obj=person):
        return
    if person.email is None or person.prename is None or person.surname is None:
        return

    title = "{0} {1}".format(person.prename, person.surname)
    newId = emailToPersonId(person.email)
    if title != person.title or newId != person.id:
        lockable = ILockable(person)
        if lockable.locked():
            if not lockable.can_safely_unlock():
                # can not modify locked object
                return
            lockable.unlock()
        person.title = title
        if newId != person.id:
            deferRename(person, newId)
        else:
            person.reindexObject()
