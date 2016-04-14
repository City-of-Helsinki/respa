import hashlib

from .xml import NAMESPACES, T


class ItemID:
    def __init__(self, id, change_key):
        self.id = id
        self.change_key = change_key

    def to_xml(self):
        return T.ItemId(Id=self.id, ChangeKey=self.change_key)

    @classmethod
    def from_tree(cls, tree):
        """
        Get the first Item ID from the given tree (likely a response)

        :param tree:
        :rtype: ItemID
        """
        item_id = tree.find(".//t:ItemId", namespaces=NAMESPACES)
        if item_id is None:
            raise ValueError("Could not find ItemId element in tree %r" % tree)
        return cls(
            id=item_id.attrib["Id"],
            change_key=item_id.attrib.get("ChangeKey")
        )

    @property
    def hash(self):
        """
        The hash of this item id's ID component.

        Used for ExchangeReservation models.

        :return:
        """
        return hashlib.md5(self.id.encode("utf8")).hexdigest()
