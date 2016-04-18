import hashlib

from django.utils.encoding import force_text
from django.utils.functional import cached_property

from .xml import NAMESPACES, T


class ItemID:
    """
    Encapsulates an Exchange Item ID (a pair of ID and change key)
    """

    def __init__(self, id, change_key):
        """
        Initialize the ItemID. You probably shouldn't call this by hand.
        """
        self._id = force_text(id)
        self._change_key = force_text(change_key)

    @property
    def change_key(self):
        """
        Get the change key for this item ID.

        As I understand things, the change key is sort of a
        timestamp/lock for change control.

        :rtype: str
        """
        return self._change_key

    @property
    def id(self):
        """
        Get the ID part of this item ID.

        This is assumed to be invariant.

        :rtype: str
        """
        return self._id

    def to_xml(self):
        """
        Return an <ItemId> XML element for this item ID.

        :return: XML element
        :rtype: lxml.etree.Element
        """
        return T.ItemId(Id=self.id, ChangeKey=self.change_key)

    @classmethod
    def from_tree(cls, tree):
        """
        Get the first Item ID from the given XML tree (likely a response)

        :type tree: lxml.etree.Element
        :rtype: ItemID
        """
        item_id = tree.find(".//t:ItemId", namespaces=NAMESPACES)
        if item_id is None:
            raise ValueError("Could not find ItemId element in tree %r" % tree)
        return cls(
            id=item_id.attrib["Id"],
            change_key=item_id.attrib.get("ChangeKey")
        )

    @cached_property
    def hash(self):
        """
        The hash of this item id's ID component.

        Used for ExchangeReservation models.

        :return:
        """
        return hashlib.md5(self.id.encode("utf8")).hexdigest()
