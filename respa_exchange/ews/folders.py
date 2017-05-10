from .xml import T


def get_distinguished_folder_id_element(principal, folder_id):
    """
    Build a DistinguishedFolderId element.

    :param principal: The principal (email) whose folder is requested.
    :param folder_id: The distinguished folder name. (See MSDN.)
    :return: XML element
    """
    return T.DistinguishedFolderId(
        {"Id": folder_id},
        T.Mailbox(
            T.EmailAddress(principal)
        )
    )
