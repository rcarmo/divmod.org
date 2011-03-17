# -*- test-case-name: xmantissa.test.test_recordattr -*-

"""
Utility support for attributes on items which compose multiple Axiom attributes
into a single epsilon.structlike.record attribute.  This can be handy when
composing a simple, common set of columns that several tables share into a
recognizable object that is not an item itself.  For example, the pair of
'localpart', 'domain' into a user object, or the triple of 'realname',
'nickname', 'hostmask', 'network' into an IRC nickname.  This functionality is
currently used to make L{sharing.Identifier} objects.

This is a handy utility that should really be moved to L{axiom.attributes} and
made public as soon as a few conditions are met:

    * L{WithRecordAttributes} needs to be integrated into L{Item}, or
      otherwise made obsolete such that normal item instantiation works and
      users don't need to call a bogus classmethod.

    * L{RecordAttribute} needs to implement the full set of comparison
      operators required by the informal axiom constraint language (__gt__,
      __lt__, __ge__, __le__, probably some other stuff).  It would also be
      great if that informal language got documented somewhere.

"""

from axiom.attributes import AND

class RecordAttribute(object):
    """
    A descriptor which maps a group of axiom attributes into a single attribute
    which returns a record composing them all.

    Use this within an Item class definition, like so::

        class Address(record('localpart domain')):
            'An email address.'

        class Email(Item, WithRecordAttributes):
            senderLocalpart = text()
            senderDomain = text()
            receipientLocalpart = text()
            recipientDomain = text()
            body = text()

            sender = RecordAttribute(Address, senderLocalpart, senderDomain)
            recipient = RecordAttribute(Address, recipientLocalpart,
                                        recipientDomain)
        # ...

        myEmail = Email._recordCreate(sender=Address(localpart=u'hello',
                                                     domain=u'example.com'),
                                      recipient=Address(localpart=u'goodbye',
                                                        domain=u'example.com'))
        print myEmail.sender.localpart

    Note: the ugly _recordCreate method is required to create items which use
    this feature due to some problems with Axiom's initialization order.  See
    L{WithRecordAttributes} for details.
    """

    def __init__(self, recordType, attrs):
        """
        Create a L{RecordAttribute} for a certain record type and set of Axiom
        attributes.

        @param recordType: the result, or a subclass of the result, of
        L{axiom.structlike.record}.

        @param attrs: a tuple of L{axiom.attributes.SQLAttribute} instances
        that were defined as part of the schema on the same item type.
        """
        self.recordType = recordType
        self.attrs = attrs


    def __get__(self, oself, type=None):
        """
        Retrieve this compound attribute from the given item.

        @param oself: an L{axiom.item.Item} instance, of a type which has this
        L{RecordAttribute}'s L{attrs} defined in its schema.
        """
        if oself is None:
            return self
        constructData = {}
        for n, attr in zip(self.recordType.__names__, self.attrs):
            constructData[n] = attr.__get__(oself, type)
        return self.recordType(**constructData)


    def _decompose(self, value):
        """
        Decompose an instance of our record type into a dictionary mapping
        attribute names to values.

        @param value: an instance of self.recordType

        @return: L{dict} containing the keys declared on L{record}.
        """
        data = {}
        for n, attr in zip(self.recordType.__names__, self.attrs):
            data[attr.attrname] = getattr(value, n)
        return data


    def __set__(self, oself, value):
        """
        Set each component attribute of this L{RecordAttribute} in turn.

        @param oself: an instance of the type where this attribute is defined.

        @param value: an instance of self.recordType whose values should be
        used.
        """
        for n, attr in zip(self.recordType.__names__, self.attrs):
            attr.__set__(oself, getattr(value, n))


    def __eq__(self, other):
        """
        @return: a comparison object resulting in all of the component
        attributes of this attribute being equal to all of the attribute values
        on the other object.

        @rtype: L{IComparison}
        """
        return AND(*[attr == getattr(other, name)
                     for attr, name
                     in zip(self.attrs, self.recordType.__names__)])


    def __ne__(self, other):
        """
        @return: a comparison object resulting in all of the component
        attributes of this attribute being unequal to all of the attribute
        values on the other object.

        @rtype: L{IComparison}
        """
        return AND(*[attr != getattr(other, name)
                     for attr, name
                     in zip(self.attrs, self.recordType.__names__)])



class WithRecordAttributes(object):
    """
    Axiom has an unfortunate behavior, which is a rather deep-seated bug in the
    way Item objects are initialized.  Default parameters are processed before
    the attributes in the constructor's dictionary are actually set.  In other
    words, if you have a custom descriptor like L{RecordAttribute}, it can't be
    passed in the constructor; if the public way to fill in a required
    attribute's value is via such an API, it becomes impossible to properly
    construct an object.

    This mixin implements a temporary workaround, by adding a classmethod for
    creating instances of classes that use L{RecordAttribute} by explicitly
    decomposing the structured record instances into their constitutent values
    before actually passing them on to L{Item.__init__}.

    This workaround needs to be promoted to a proper resolution before this can
    be a public API; users should be able to create their own descriptors that
    modify underlying database state and have them behave in the expected way
    during item creation.
    """

    def create(cls, **kw):
        """
        Create an instance of this class, first cleaning up the keyword
        arguments so they will fill in any required values.

        @return: an instance of C{cls}
        """
        for k, v in kw.items():
            attr = getattr(cls, k, None)
            if isinstance(attr, RecordAttribute):
                kw.pop(k)
                kw.update(attr._decompose(v))
        return cls(**kw)
    create = classmethod(create)
