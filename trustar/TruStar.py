from __future__ import print_function

import json
import sys
import time
from datetime import datetime

import configparser
import dateutil.parser
import pytz
import requests
import requests.auth
from builtins import object
from future import standard_library
from tzlocal import get_localzone

standard_library.install_aliases()


class TruStar(object):
    """
    Main class you to instantiate the TruStar API
    """

    def __init__(self, config_file="trustar.conf", config_role="trustar"):

        self.enclaveIds = []

        config_parser = configparser.RawConfigParser()
        config_parser.read(config_file)

        try:
            # parse required properties
            self.auth = config_parser.get(config_role, 'auth_endpoint')
            self.base = config_parser.get(config_role, 'api_endpoint')
            self.apikey = config_parser.get(config_role, 'user_api_key')
            self.apisecret = config_parser.get(config_role, 'user_api_secret')

            # parse enclaves
            if config_parser.has_option(config_role, 'enclave_ids'):
                self.enclaveIds = [i for i in config_parser.get(config_role, 'enclave_ids').split(',') if i is not None]
        except Exception as e:
            print("Problem reading config file: %s", e)
            sys.exit(1)

    @staticmethod
    def normalize_timestamp(date_time):
        """
        Attempt to convert a string timestamp in to a TruSTAR compatible format for submission.
        Will return current time with UTC time zone if None
        :param date_time: int that is epoch time, or string/datetime object containing date, time, and ideally timezone
        examples of supported timestamp formats: 1487890914, 1487890914000, "2017-02-23T23:01:54", "2017-02-23T23:01:54+0000"
        """
        datetime_dt = datetime.now()

        # get current time in seconds-since-epoch
        current_time = int(time.time())

        try:
            # identify type of timestamp and convert to datetime object
            if isinstance(date_time, int):

                # if timestamp has more than 10 digits, it is in ms
                if date_time > 9999999999:
                    date_time /= 1000

                # if timestamp is incorrectly forward dated, set to current time
                if date_time > current_time:
                    date_time = current_time
                datetime_dt = datetime.fromtimestamp(date_time)
            elif isinstance(date_time, str):
                datetime_dt = dateutil.parser.parse(date_time)
            elif isinstance(date_time, datetime):
                datetime_dt = date_time

        # if timestamp is none of the formats above, error message is printed and timestamp is set to current time by default
        except Exception as e:
            print(e)
            datetime_dt = datetime.now()

        # if timestamp is timezone naive, add timezone
        if not datetime_dt.tzinfo:
            timezone = get_localzone()

            # add system timezone
            datetime_dt = timezone.localize(datetime_dt)

            # convert to UTC
            datetime_dt = datetime_dt.astimezone(pytz.utc)

        # converts datetime to iso8601
        return datetime_dt.isoformat()

    def get_token(self, verify=True):
        """
        Retrieves the OAUTH token generated by your API key and API secret.
        this function has to be called before any API calls can be made
        :param verify: boolean - ignore verifying the SSL certificate if you set verify to False
        """
        client_auth = requests.auth.HTTPBasicAuth(self.apikey, self.apisecret)
        post_data = {"grant_type": "client_credentials"}
        resp = requests.post(self.auth, auth=client_auth, data=post_data, verify=verify)
        resp.raise_for_status()
        token_json = resp.json()
        return token_json["access_token"]

    def get_reports(self, access_token, from_time=None, to_time=None, distribution_type=None, submitted_by=None,
                    enclave_ids=None, verify=True):
        """
        Retrieves reports filtering by time window, distribution type, ownership, and enclave association
        :param access_token: OAuth API token
        :param from_time: Optional start of time window (Unix timestamp - seconds since epoch)
        :param to_time: Optional end of time window (Unix timestamp - seconds since epoch)
        :param distribution_type: Optional, restrict reports to specific distribution type
        (by default all accessible reports are returned). Possible values are: 'COMMUNITY' and 'ENCLAVE'
        :param submitted_by: Optional, restrict reports by ownership (by default all accessible reports are returned).
        Possible values are: 'me' and 'others'
        :param enclave_ids: Optional comma separated list of enclave ids, restrict reports to specific enclaves
        (by default reports from all enclaves are returned)
        :param verify: Optional server SSL verification, default True

        """

        headers = {"Authorization": "Bearer " + access_token}
        params = {'from': from_time, 'to': to_time, 'distributionType': distribution_type,
                  'submittedBy': submitted_by, 'enclaveIds': enclave_ids}
        resp = requests.get(self.base + "/reports", params=params, headers=headers, verify=verify)

        resp.raise_for_status()
        return json.loads(resp.content.decode('utf8'))

    def get_report_details(self, access_token, report_id, id_type=None, verify=True):
        """
        Retrieves the report details dictionary
        :param access_token: OAuth API token
        :param report_id: Incident Report ID
        :param id_type: indicates if ID is internal report guid or external ID provided by the user
        :param verify: boolean - ignore verifying the SSL certificate if you set verify to False
        :return Incident report dictionary if found, else exception.
        """

        url = "%s/report/%s" % (self.base, report_id)
        headers = {"Authorization": "Bearer " + access_token}
        params = {'idType': id_type}
        resp = requests.get(url, params=params, headers=headers, verify=verify)

        resp.raise_for_status()
        return json.loads(resp.content.decode('utf8'))

    def update_report(self, access_token, report_id, id_type=None, title=None, report_body=None, time_began=None,
                      external_url=None, distribution=None, enclave_ids=None, verify=True):
        """
        Updates report with the given id, overwrites any fields that are provided
        :param access_token: OAuth API token
        :param report_id: Incident Report ID
        :param id_type: indicates if ID is internal report guid or external ID provided by the user
        :param title: new title for report
        :param report_body: new body for report
        :param time_began: new time_began for report
        :param distribution: new distribution type for report
        :param enclave_ids: new list of enclave ids that the report will belong to
        :param external_url: external url of report, optional and is associated with the original source of this report 
        :param verify: boolean - ignore verifying the SSL certificate if you set verify to False
        """

        url = "%s/report/%s" % (self.base, report_id)
        headers = {'Authorization': 'Bearer ' + access_token, 'content-Type': 'application/json'}
        params = {'idType': id_type}

        # if enclave_ids field is not null, parse into array of strings
        if enclave_ids:
            enclave_ids = [i for i in enclave_ids.split(',') if i is not None]

        payload = {'incidentReport': {'title': title,
                                      'reportBody': report_body,
                                      'timeBegan': self.normalize_timestamp(time_began),
                                      'distributionType': distribution,
                                      'externalUrl': external_url},
                   'enclaveIds': enclave_ids}
        resp = requests.put(url, json.dumps(payload), params=params, headers=headers, verify=verify)
        resp.raise_for_status()

        return json.loads(resp.content.decode('utf8'))

    def delete_report(self, access_token, report_id, id_type=None, verify=True):
        """
        Deletes the report for the given id
        :param access_token: OAuth API token
        :param report_id: Incident Report ID
        :param id_type: indicates if ID is internal report guid or external ID provided by the user
        :param verify: boolean - ignore verifying the SSL certificate if you set verify to False
        """

        url = "%s/report/%s" % (self.base, report_id)
        headers = {"Authorization": "Bearer " + access_token}
        params = {'idType': id_type}
        resp = requests.delete(url, params=params, headers=headers, verify=verify)
        resp.raise_for_status()

        return resp

    def query_latest_indicators(self, access_token, source, indicator_types, limit, interval_size, verify=True):
        """
        Finds all latest indicators
        :param access_token: OAUTH access token
        :param source: source of the indicators which can either be INCIDENT_REPORT or OSINT
        :param indicator_types: a list of indicators or a string equal to "ALL" to query all indicator types extracted
        by TruSTAR
        :param limit: limit on the number of indicators. Max is set to 5000
        :param interval_size: time interval on returned indicators. Max is set to 24 hours
        :param verify: Optional server SSL verification, default True
        :return json response of the result
        """

        headers = {"Authorization": "Bearer " + access_token}
        payload = {'source': source, 'types': indicator_types, 'limit': limit, 'intervalSize': interval_size}
        resp = requests.get(self.base + "/indicators/latest", params=payload, headers=headers, verify=verify)

        resp.raise_for_status()
        return json.loads(resp.content.decode('utf8'))

    def get_community_trends(self, access_token, type, from_time, to_time, page_size, start_page, verify=True):
        """
        Find community trending indicators.
        :param access_token: OAUTH access token
        :param type: the type of indicators.  3 types are supported: "malware", "cve" (vulnerabilities), "other" (all
        other types of indicators)
        :param from_time: Optional start of time window (Unix timestamp - seconds since epoch)
        :param to_time: Optional end of time window (Unix timestamp - seconds since epoch)
        :param page_size: # of results on returned page
        :param start_page: page to start returning results on
        :param verify: Optional server SSL verification, default True
        :return: json response of the result
        """

        headers = {"Authorization": "Bearer " + access_token}
        payload = {
            'type': type,
            'from': from_time,
            'to': to_time,
            'pageSize': page_size,
            'startPage': start_page
        }
        resp = requests.get("{}/community-indicators/trending".format(self.base),
                            params=payload, headers=headers, verify=verify)
        return json.loads(resp.content.decode('utf8'))

    def get_correlated_reports(self, access_token, indicator, verify=True):
        """
        Retrieves all TruSTAR reports that contain the searched indicator. You can specify multiple indicators
        separated by commas
        :param access_token:  OAuth API token
        :param indicator:
        :param verify: Optional server SSL verification, default True

        """

        headers = {"Authorization": "Bearer " + access_token}
        payload = {'q': indicator}
        resp = requests.get(self.base + "/reports/correlate", params=payload, headers=headers, verify=verify)
        resp.raise_for_status()
        return json.loads(resp.content.decode('utf8'))

    def query_indicators(self, access_token, indicators, limit, verify=True):
        """
        Finds all reports that contain the indicators and returns correlated indicators from those reports.
        you can specify the limit of indicators returned.
        :param access_token: OAuth API token
        :param indicators: list of space-separated indicators to search for
        :param limit: max number of results to return
        :param verify: Optional server SSL verification, default True
        """

        headers = {"Authorization": "Bearer " + access_token}
        payload = {'q': indicators, 'limit': limit}

        resp = requests.get(self.base + "/indicators", params=payload, headers=headers, verify=verify)
        resp.raise_for_status()
        return json.loads(resp.content.decode('utf8'))

    def submit_report(self, access_token, report_body, title, external_id=None, external_url=None, time_began=datetime.now(),
                      enclave=False, verify=True):
        """
        Wraps supplied text as a JSON-formatted TruSTAR Incident Report and submits it to TruSTAR Station
        By default, this submits to the TruSTAR community. To submit to your enclave(s), set enclave parameter to True,
        and ensure that the target enclaves' ids are specified in the config file field enclave_ids.
        :param access_token: OAuth API token
        :param report_body: body of report
        :param title: title of report
        :param external_id: external tracking id of report, optional if user doesn't have their own tracking id that they want associated with this report
        :param external_url: external url of report, optional and is associated with the original source of this report 
        :param time_began: time report began
        :param enclave: boolean - whether or not to submit report to user's enclaves (see 'enclave_ids' config property)
        :param verify: boolean - ignore verifying the SSL certificate if you set verify to False
        """

        distribution_type = 'ENCLAVE' if enclave else 'COMMUNITY'
        if distribution_type == 'ENCLAVE' and len(self.enclaveIds) < 1:
            raise Exception("Must specify one or more enclave IDs to submit enclave reports into")

        headers = {'Authorization': 'Bearer ' + access_token, 'content-Type': 'application/json'}

        payload = {'incidentReport': {'title': title,
                                      'externalTrackingId': external_id,
                                      'externalUrl': external_url,
                                      'timeBegan': self.normalize_timestamp(time_began),
                                      'reportBody': report_body,
                                      'distributionType': distribution_type},
                   'enclaveIds': self.enclaveIds}

        resp = requests.post(self.base + "/report", json.dumps(payload), headers=headers, timeout=60, verify=verify)
        resp.raise_for_status()
        return resp.json()

    def get_enclave_tags(self, access_token, report_id, id_type=None, verify=True):
        """
        Retrieves the enclave tags present in a specific report
        :param access_token: OAuth API token
        :param report_id: Incident Report ID
        :param id_type: Optional, indicates if ID is internal report guid or external ID provided by the user
        (default Internal)
        :param verify: Optional server SSL verification, default True
        """

        url = "%s/reports/%s/enclave-tags" % (self.base, report_id)
        headers = {"Authorization": "Bearer " + access_token}
        params = {'idType': id_type}

        resp = requests.get(url, params=params, headers=headers, verify=verify)
        resp.raise_for_status()
        return json.loads(resp.content.decode('utf8'))

    def add_enclave_tag(self, access_token, report_id, name, enclave_id, id_type=None, verify=True):
        """
        Adds a tag to a specific report, in a specific enclave
        :param access_token: OAuth API token
        :param report_id: Incident Report ID
        :param name: name of the tag to be added
        :param enclave_id: id of the enclave where the tag will be added
        :param id_type: Optional, indicates if ID is internal report guid or external ID provided by the user
        (default Internal)
        :param verify: Optional server SSL verification, default True
        """

        url = "%s/reports/%s/enclave-tags" % (self.base, report_id)
        headers = {"Authorization": "Bearer " + access_token}
        params = {'idType': id_type, 'name': name, 'enclaveId': enclave_id}

        resp = requests.post(url, params=params, headers=headers, verify=verify)
        resp.raise_for_status()
        return json.loads(resp.content.decode('utf8'))

    def delete_enclave_tag(self, access_token, report_id, name, enclave_id, id_type=None, verify=True):
        """
        Deletes a tag from a specific report, in a specific enclave
        :param access_token: OAuth API token
        :param report_id: Incident Report ID
        :param name: name of the tag to be deleted
        :param enclave_id: id of the enclave where the tag will be deleted
        :param id_type: Optional, indicates if ID is internal report guid or external ID provided by the user
        (default Internal)
        :param verify: Optional server SSL verification, default True
        """

        url = "%s/reports/%s/enclave-tags" % (self.base, report_id)
        headers = {"Authorization": "Bearer " + access_token}
        params = {'idType': id_type, 'name': name, 'enclaveId': enclave_id}

        resp = requests.delete(url, params=params, headers=headers, verify=verify)
        resp.raise_for_status()
        return resp.content.decode('utf8')

    def get_report_url(self, report_id):
        """
        Build direct URL to report from its ID
        :param report_id: Incident Report (IR) ID, e.g., as returned from `submit_report`
        :return URL
        """

        # Check environment for URL
        base_url = 'https://station.trustar.co' if ('https://api.trustar.co' in self.base) else \
            self.base.split('/api/')[0]

        return "%s/constellation/reports/%s" % (base_url, report_id)

    def get_enclave_ids(self):
        """
        Exposes the enclave ids as fetched from the configuration file
        :return: list of enclave ids
        """
        return self.enclaveIds
