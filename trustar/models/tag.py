# python 2 backwards compatibility
from __future__ import print_function
from builtins import object, super
from future import standard_library
from six import string_types

# package imports
from .base import ModelBase


class Tag(ModelBase):
    """
    Models a |Tag_resource|.

    :ivar name: The name of the tag, i.e. "malicious".
    :ivar id: The ID of the tag.
    :ivar enclave_id: The :class:`Enclave` object representing the enclave that the tag belongs to.
    """

    def __init__(self, name, id=None, enclave_id=None):
        """
        Constructs a tag object.

        :param name: The name of the tag, i.e. "malicious".
        :param id: The ID of the tag.
        :param enclave_id: The ID of the enclave the tag belongs to.
        """

        self.name = name
        self.id = id
        self.enclave_id = enclave_id

    @classmethod
    def from_dict(cls, tag):
        """
        Create a tag object from a dictionary.  This method is intended for internal use, to construct a
        :class:`Tag` object from the body of a response json.  It expects the keys of the dictionary to match those
        of the json that would be found in a response to an API call such as ``GET /enclave-tags``.

        :param tag: The dictionary.
        :return: The :class:`Tag` object.
        """

        return Tag(name=tag.get('name'),
                   id=tag.get('guid'),
                   enclave_id=tag.get('enclaveId'))

    def to_dict(self, remove_nones=False):
        """
        Creates a dictionary representation of the tag.

        :param remove_nones: Whether ``None`` values should be filtered out of the dictionary.  Defaults to ``False``.
        :return: A dictionary representation of the tag.
        """

        if remove_nones:
            d = super(Tag, self).to_dict(remove_nones=True)
        else:
            d = {
                'name': self.name,
                'id': self.id,
                'enclaveId': self.enclave_id
            }

        return d
