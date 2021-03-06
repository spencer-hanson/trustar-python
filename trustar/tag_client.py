# python 2 backwards compatibility
from __future__ import print_function
from builtins import object, str
from future import standard_library
from six import string_types
import logging
import json

# package imports
from .models import Tag

# python 2 backwards compatibility
standard_library.install_aliases()

logger = logging.getLogger(__name__)


class TagClient(object):
    
    def get_enclave_tags(self, report_id, id_type=None):
        """
        Retrieves all enclave tags present in a specific report.

        :param report_id: the ID of the report
        :param id_type: indicates whether the ID is an internal or external ID
        :return: A list of |Tag| objects.
        """

        params = {'idType': id_type}
        resp = self._client.get("reports/%s/tags" % report_id, params=params)
        return [Tag.from_dict(indicator) for indicator in resp.json()]

    def alter_report_tags(self, report_id, added_tags, removed_tags, id_type=None):
        """
        Bulk add/remove tags from a report.

        :param report_id: the ID of the report
        :param added_tags: a list of strings, the names of tags to add
        :param removed_tags: a list of strings, the names of tags to remove
        :return: the ID of the report
        """

        params = {'idType': id_type}
        body = {
            'addedTags': [{'name': tag_name} for tag_name in added_tags],
            'removedTags': [{'name': tag_name} for tag_name in removed_tags]
        }

        resp = self._client.post("reports/{}/alter-tags".format(report_id), params=params, data=json.dumps(body))
        return resp.json().get('id')

    def add_enclave_tag(self, report_id, name, enclave_id=None, id_type=None):
        """
        Adds a tag to a specific report, for a specific enclave.

        NOTE: This function is deprecated.  Use alter_report_tags instead.

        :param report_id: The ID of the report
        :param name: The name of the tag to be added
        :param enclave_id: ID of the enclave where the tag will be added.
            NOTE: This field is deprecated. Report tags are no longer enclave-specific.
            This field will be ignored if it is filled out.
        :param id_type: indicates whether the ID is an internal or external ID
        :return: The ID of the tag that was created.
        """

        # delegate to alter-tags endpoint
        self.alter_report_tags(report_id=report_id,
                               added_tags=[name],
                               removed_tags=[],
                               id_type=id_type)

        # return the tag name to maintain backwards compatibility
        # the old endpoint returned the tag ID, but tag IDs no longer exist
        # the tag name is now used in place of its ID throughout all API endpoints
        return name

    def delete_enclave_tag(self, report_id, tag_id, id_type=None):
        """
        Deletes a tag from a specific report, in a specific enclave.

        NOTE: This function is deprecated.  Use alter_report_tags instead.

        :param string report_id: The ID of the report
        :param string tag_id: name of the tag to delete.
            NOTE: Report tags no longer have IDs, instead the name of the tag serves as its ID.
            Pass the name of the tag to delete in this field.
        :param string id_type: indicates whether the ID internal or an external ID provided by the user
        :return: The ID of the report.
        """

        # delegate to alter-tags endpoint
        return self.alter_report_tags(report_id=report_id,
                                      added_tags=[],
                                      removed_tags=[tag_id],
                                      id_type=id_type)

    def get_all_enclave_tags(self, enclave_ids=None):
        """
        Retrieves all tags present in the given enclaves. If the enclave list is empty, the tags returned include all
        tags for all enclaves the user has access to.

        :param (string) list enclave_ids: list of enclave IDs
        :return: The list of |Tag| objects.
        """

        params = {'enclaveIds': enclave_ids}
        resp = self._client.get("reports/tags", params=params)
        return [Tag.from_dict(indicator) for indicator in resp.json()]

    def get_all_indicator_tags(self, enclave_ids=None):
        """
        Get all indicator tags for a set of enclaves.

        :param (string) list enclave_ids: list of enclave IDs
        :return: The list of |Tag| objects.
        """

        if enclave_ids is None:
            enclave_ids = self.enclave_ids

        params = {'enclaveIds': enclave_ids}
        resp = self._client.get("indicators/tags", params=params)
        return [Tag.from_dict(indicator) for indicator in resp.json()]

    def add_indicator_tag(self, indicator_value, name, enclave_id):
        """
        Adds a tag to a specific indicator, for a specific enclave.

        :param indicator_value: The value of the indicator
        :param name: The name of the tag to be added
        :param enclave_id: ID of the enclave where the tag will be added
        :return: A |Tag| object representing the tag that was created.
        """

        data = {
            'value': indicator_value,
            'tag': {
                'name': name,
                'enclaveId': enclave_id
            }
        }

        resp = self._client.post("indicators/tags", data=json.dumps(data))
        return Tag.from_dict(resp.json())

    def delete_indicator_tag(self, indicator_value, tag_id):
        """
        Deletes a tag from a specific indicator, in a specific enclave.

        :param indicator_value: The value of the indicator to delete the tag from
        :param tag_id: ID of the tag to delete
        """

        params = {
            'value': indicator_value
        }

        self._client.delete("indicators/tags/%s" % tag_id, params=params)
