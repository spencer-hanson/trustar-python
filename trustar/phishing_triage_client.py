# python 2 backwards compatibility
from __future__ import print_function
from builtins import object, str
from future import standard_library

# external imports
import json
import functools
import logging

# package imports
from .models import CursorPage, PhishingIndicator, PhishingSubmission

# python 2 backwards compatibility
standard_library.install_aliases()

logger = logging.getLogger(__name__)


class PhishingTriageClient(object):

    @staticmethod
    def remove_nones(d):
        """
        Removes None values from a dictionary.

        :param dict d: A dictionary
        """
        return {k: v for k, v in d.items() if v is not None}

    def get_phishing_submissions(self, from_time=None, to_time=None, priority_event_score=None,
                                 enclave_ids=None, status=None, cursor=None):
        """
        Fetches all phishing submissions that fit a given criteria.

        :param int from_time: Start of time window in milliseconds since epoch (optional)
        :param int to_time: End of time window in milliseconds since epoch (optional)
        :param list(int) priority_event_score: List of desired scores of phishing submission on a scale of 0-3
                                             (default: [3]).
        :param list(string) enclave_ids: List of enclave ids to pull submissions from.
                                         (defaults to all of a user's enclaves).
        :param list(string) status: List of statuses to filter submissions by. Options are 'UNRESOLVED', 'CONFIRMED',
                                    and 'IGNORED'. (default: ['UNRESOLVED']).
        :param string cursor: A Base64-encoded string that contains information on how to retrieve the next page.
                              If a cursor isn't passed, it will default to pageSize: 25, pageNumber: 0
        :return: CursorPage.generator - A generator object which can be used to paginate through |PhishingSubmission| data.
        """

        phishing_submissions_page_generator = self._get_phishing_submissions_page_generator(
            from_time=from_time,
            to_time=to_time,
            priority_event_score=priority_event_score,
            enclave_ids=enclave_ids,
            status=status,
            cursor=cursor
        )

        return CursorPage.get_generator(page_generator=phishing_submissions_page_generator)

    def _get_phishing_submissions_page_generator(self, from_time=None, to_time=None, priority_event_score=None,
                                                 enclave_ids=None, status=None, cursor=None):
        """
        Creates a generator from the |get_indicators_page| method that returns each successive page.

        :param int from_time: Start of time window in milliseconds since epoch (optional).
        :param int to_time: End of time window in milliseconds since epoch (optional).
        :param list(int) priority_event_score: List of desired scores of phishing submission on a scale of 0-3
                                                  (default: [3]).
        :param list(string) enclave_ids: A list of enclave IDs to filter by. (defaults to all of a user's enclaves)
        :param list(string) status: List of statuses to filter submissions by. Options are 'UNRESOLVED', 'CONFIRMED',
                                    and 'IGNORED'. (default: ['UNRESOLVED']).
        :param string cursor: A Base64-encoded string that contains information on how to retrieve the next page.
                              If a cursor isn't passed, it will default to pageSize: 25, pageNumber: 0
        """

        get_page = functools.partial(
            self.get_phishing_submissions_page,
            from_time=from_time,
            to_time=to_time,
            priority_event_score=priority_event_score,
            enclave_ids=enclave_ids,
            status=status,
        )

        return CursorPage.get_cursor_based_page_generator(get_page, cursor=cursor)

    def get_phishing_submissions_page(self, from_time=None, to_time=None, priority_event_score=None,
                                      enclave_ids=None, status=None, cursor=None):
        """
        Get a page of phishing submissions that match the given criteria.

        :param int from_time: Start of time window in milliseconds since epoch (optional).
        :param int to_time: End of time window in milliseconds since epoch (optional).
        :param list(int) priority_event_score: List of desired scores of phishing submission on a scale of 0-3
                                             (default: [3]).
        :param list(string) enclave_ids: A list of enclave IDs to filter by. (defaults to all of a user's enclaves)
        :param list(string) status: List of statuses to filter submissions by. Options are 'UNRESOLVED', 'CONFIRMED',
                                    and 'IGNORED'. (default: ['UNRESOLVED']).
        :param string cursor: A Base64-encoded string that contains information on how to retrieve the next page.
                              If a cursor isn't passed, it will default to pageSize: 25, pageNumber: 0
        :return: |CursorPage| - An object representing a single page of |PhishingSubmission| objects.
        """

        data = self.remove_nones({
            'from': from_time,
            'to': to_time,
            'priorityEventScore': priority_event_score,
            'enclaveIds': enclave_ids,
            'status': status,
            'cursor': cursor
        })

        resp = self._client.post("triage/submissions", data=json.dumps(data))

        return CursorPage.from_dict(resp.json(), content_type=PhishingSubmission)

    def mark_triage_status(self, submission_id=None, status=None):
        """
        Marks a phishing email submission with one of the phishing namespace tags.

        :param string submission_id: ID of the email submission.
        :param string status: Triage status of submission.
        """

        if submission_id is None or not isinstance(submission_id, str):
            raise Exception("Please include ID of phishing email submission to mark triage status")

        params = {'status': status}

        return self._client.post("triage/submissions/{submission_id}/status"
                                 .format(submission_id=submission_id), params=params)

    def get_phishing_indicators(self, from_time=None, to_time=None, normalized_indicator_score=None,
                                priority_event_score=None, status=None, enclave_ids=None, cursor=None):
        """
        Get a page of phishing indicators that match the given criteria.

        :param int from_time: Start of time window in milliseconds since epoch (optional).
        :param int to_time: End of time window in milliseconds since epoch (optional).
        :param list(int) normalized_indicator_score: List of desired scores of intel sources on a scale of 0-3
                                                  (default: [3]).
        :param list(int) priority_event_score: List of desired scores of phishing indicators on a scale of 0-3
                                                  (default: [3]).
        :param list(string) enclave_ids: A list of enclave IDs to filter by. (defaults to all of a user's enclaves)
        :param list(string) status: List of statuses to filter indicators by. Options are 'UNRESOLVED', 'CONFIRMED',
                                    and 'IGNORED'. (default: ['UNRESOLVED']).
        :param string cursor: A Base64-encoded string that contains information on how to retrieve the next page.
                              If a cursor isn't passed, it will default to pageSize: 25, pageNumber: 0
        :return: CursorPage.generator - A generator object which can be used to paginate through |PhishingIndicator| data.
        """

        phishing_indicators_page_generator = self._get_phishing_indicators_page_generator(
            from_time=from_time,
            to_time=to_time,
            normalized_indicator_score=normalized_indicator_score,
            priority_event_score=priority_event_score,
            enclave_ids=enclave_ids,
            status=status,
            cursor=cursor
        )

        return CursorPage.get_generator(page_generator=phishing_indicators_page_generator)

    def _get_phishing_indicators_page_generator(self, from_time=None, to_time=None, normalized_indicator_score=None,
                                                priority_event_score=None, enclave_ids=None, status=None,
                                                cursor=None):
        """
        Creates a generator from the |get_indicators_page| method that returns each successive page.

        :param int from_time: Start of time window in milliseconds since epoch (optional).
        :param int to_time: End of time window in milliseconds since epoch (optional).
        :param list(int) normalized_indicator_score: List of desired scores of intel sources on a scale of 0-3
                                                  (default: [3]).
        :param list(int) priority_event_score: List of desired scores of phishing indicators on a scale of 0-3
                                                  (default: [3]).
        :param list(string) enclave_ids: A list of enclave IDs to filter by. (defaults to all of a user's enclaves)
        :param list(string) status: List of statuses to filter indicators by. Options are 'UNRESOLVED', 'CONFIRMED',
                                    and 'IGNORED'. (default: ['UNRESOLVED']).
        :param string cursor: A Base64-encoded string that contains information on how to retrieve the next page.
                              If a cursor isn't passed, it will default to pageSize: 25, pageNumber: 0
        """

        get_page = functools.partial(
            self.get_phishing_indicators_page,
            from_time=from_time,
            to_time=to_time,
            normalized_indicator_score=normalized_indicator_score,
            priority_event_score=priority_event_score,
            enclave_ids=enclave_ids,
            status=status,
        )

        return CursorPage.get_cursor_based_page_generator(get_page, cursor=cursor)

    def get_phishing_indicators_page(self, from_time=None, to_time=None, normalized_indicator_score=None,
                                     priority_event_score=None, enclave_ids=None, status=None, cursor=None):
        """
        Get a page of phishing indicators that match the given criteria.

        :param int from_time: Start of time window in milliseconds since epoch (optional).
        :param int to_time: End of time window in milliseconds since epoch (optional).
        :param list(int) normalized_indicator_score: List of desired scores of intel sources on a scale of 0-3
                                                  (default: [3]).
        :param list(int) priority_event_score: List of desired scores of phishing indicators on a scale of 0-3
                                             (default: [3]).
        :param list(string) enclave_ids: A list of enclave IDs to filter by.
        :param list(string) status: List of statuses to filter indicators by. Options are 'UNRESOLVED', 'CONFIRMED',
                                    and 'IGNORED'. (default: ['UNRESOLVED']).
        :param string cursor: A Base64-encoded string that contains information on how to retrieve the next page.
                              If a cursor isn't passed, it will default to pageSize: 25, pageNumber: 0
        :return: |CursorPage| - An object representing a single page of |PhishingIndicator| objects.
        """

        data = self.remove_nones({
            'from': from_time,
            'to': to_time,
            'normalizedIndicatorScore': normalized_indicator_score,
            'priorityEventScore': priority_event_score,
            'enclaveIds': enclave_ids,
            'status': status,
            'cursor': cursor
        })

        resp = self._client.post("triage/indicators", data=json.dumps(data))

        return CursorPage.from_dict(resp.json(), content_type=PhishingIndicator)
