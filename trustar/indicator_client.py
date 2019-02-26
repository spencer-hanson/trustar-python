# python 2 backwards compatibility
from __future__ import print_function
from builtins import object, str
from future import standard_library
from six import string_types

# external imports
import functools
import json
import logging

# package imports
from .models import Indicator, Page, Tag

# python 2 backwards compatibility
standard_library.install_aliases()

logger = logging.getLogger(__name__)


class IndicatorClient(object):

    def submit_indicators(self, indicators, enclave_ids=None, tags=None):
        """
        Submit indicators directly.  The indicator field ``value`` is required; all other metadata fields are optional:
        ``firstSeen``, ``lastSeen``, ``sightings``, ``notes``, and ``source``. The submission must specify enclaves for
        the indicators to be submitted to, and can optionally specify tags to assign to all the indicators in the
        submission, and/or include individual tags in each Indicator (which will take precedence over the submission tags).
        The tags can be existing or new, and are identified by ``name`` and ``enclaveId``.
        (Passing the GUID of an existing tag is not allowed.  ``name`` and ``enclaveId`` must be specified for each tag.)

        This function uses the API endpoint discussed here:  https://docs.trustar.co/api/v13/indicators/submit_indicators.html
        Note that |Indicator| class attribute names are often slightly different from the API endpoint's parameters.
        (EX: The |Indicator| class's ``first_seen`` attribute corresponds to the API endpoint's ``firstSeen`` parameter.)

        :param list(Indicator) indicators: a list of |Indicator| objects.  Indicator's ``value`` is required, all other
            attributes can be Null.  These |Indicator| attributes can be modified / updated using this function:
            ``value``, ``first_seen``, ``last_seen``, ``sightings``, ``source``, ``notes``, and ``tags``.  No other |Indicator| attributes
            can be modified in TruSTAR by using this function.
        :param list(string) enclave_ids: a list of enclave IDs.
        :param list(string) tags: a list of |Tag| objects that will be applied to ALL indicators in the submission.
        """

        if enclave_ids is None:
            enclave_ids = self.enclave_ids

        if tags is not None:
            tags = [tag.to_dict() for tag in tags]

        body = {
            "enclaveIds": enclave_ids,
            "content": [indicator.to_dict() for indicator in indicators],
            "tags": tags
        }
        self._client.post("indicators", data=json.dumps(body))

    def get_indicators(self, from_time=None, to_time=None, enclave_ids=None,
                       included_tag_ids=None, excluded_tag_ids=None,
                       start_page=0, page_size=None):
        """
        Creates a generator from the |get_indicators_page| method that returns each successive indicator as an
        |Indicator| object containing values for the 'value' and 'type' attributes only; all
        other |Indicator| object attributes will contain Null values.

        :param int from_time: start of time window in milliseconds since epoch (defaults to 7 days ago).
        :param int to_time: end of time window in milliseconds since epoch (defaults to current time).
        :param list(string) enclave_ids: a list of enclave IDs from which to get indicators from. 
        :param list(string) included_tag_ids: only indicators containing ALL of these tag GUIDs will be returned.
        :param list(string) excluded_tag_ids: only indicators containing NONE of these tags GUIDs be returned. 
        :param int start_page: see 'page_size' explanation.
        :param int page_size: Passing the integer 1000 as the argument to this parameter should result in your script 
        making fewer API calls because it returns the largest quantity of indicators with each API call.  An API call 
        has to be made to fetch each |Page|.   
        :return: A generator of |Indicator| objects containing values for the "value" and "type" attributes only.
        All other attributes of the |Indicator| object will contain Null values. 
        
        """
        indicators_page_generator = self._get_indicators_page_generator(
            from_time=from_time,
            to_time=to_time,
            enclave_ids=enclave_ids,
            included_tag_ids=included_tag_ids,
            excluded_tag_ids=excluded_tag_ids,
            page_number=start_page,
            page_size=page_size
        )

        indicators_generator = Page.get_generator(page_generator=indicators_page_generator)

        return indicators_generator

    def _get_indicators_page_generator(self, from_time=None, to_time=None, page_number=0, page_size=None,
                                       enclave_ids=None, included_tag_ids=None, excluded_tag_ids=None):
        """
        Creates a generator from the |get_indicators_page| method that returns each successive page.

        :param int from_time: start of time window in milliseconds since epoch (defaults to 7 days ago)
        :param int to_time: end of time window in milliseconds since epoch (defaults to current time)
        :param int page_number: the page number
        :param int page_size: the page size
        :param list(string) enclave_ids: a list of enclave IDs to filter by
        :param list(string) included_tag_ids: only indicators containing ALL of these tags will be returned
        :param list(string) excluded_tag_ids: only indicators containing NONE of these tags will be returned
        :return: a |Page| of |Indicator| objects
        """

        get_page = functools.partial(
            self.get_indicators_page,
            from_time=from_time,
            to_time=to_time,
            page_number=page_number,
            page_size=page_size,
            enclave_ids=enclave_ids,
            included_tag_ids=included_tag_ids,
            excluded_tag_ids=excluded_tag_ids
        )
        return Page.get_page_generator(get_page, page_number, page_size)

    def get_indicators_page(self, from_time=None, to_time=None, page_number=None, page_size=None,
                            enclave_ids=None, included_tag_ids=None, excluded_tag_ids=None):
        """
        Get a page of indicators matching the provided filters.

        :param int from_time: start of time window in milliseconds since epoch (defaults to 7 days ago)
        :param int to_time: end of time window in milliseconds since epoch (defaults to current time)
        :param int page_number: the page number
        :param int page_size: the page size
        :param list(string) enclave_ids: a list of enclave IDs to filter by
        :param list(string) included_tag_ids: only indicators containing ALL of these tags will be returned
        :param list(string) excluded_tag_ids: only indicators containing NONE of these tags will be returned
        :return: a |Page| of indicators
        """

        params = {
            'from': from_time,
            'to': to_time,
            'pageSize': page_size,
            'pageNumber': page_number,
            'enclaveIds': enclave_ids,
            'tagIds': included_tag_ids,
            'excludedTagIds': excluded_tag_ids
        }

        resp = self._client.get("indicators", params=params)

        page_of_indicators = Page.from_dict(resp.json(), content_type=Indicator)

        return page_of_indicators

    def search_indicators(self, search_term, enclave_ids=None):
        """
        Uses the |search_indicators_page| method to create a generator that returns each successive indicator.

        :param str search_term: The term to search for.
        :param list(str) enclave_ids: list of enclave ids used to restrict indicators to specific enclaves (optional - by
            default indicators from all of user's enclaves are returned)
        :return: The generator.
        """

        return Page.get_generator(page_generator=self._search_indicators_page_generator(search_term, enclave_ids))

    def _search_indicators_page_generator(self, search_term, enclave_ids=None, start_page=0, page_size=None):
        """
        Creates a generator from the |search_indicators_page| method that returns each successive page.

        :param str search_term: The term to search for.
        :param list(str) enclave_ids: list of enclave ids used to restrict indicators to specific enclaves (optional - by
            default indicators from all of user's enclaves are returned)
        :param int start_page: The page to start on.
        :param page_size: The size of each page.
        :return: The generator.
        """

        get_page = functools.partial(self.search_indicators_page, search_term, enclave_ids)
        return Page.get_page_generator(get_page, start_page, page_size)

    def search_indicators_page(self, search_term, enclave_ids=None, page_size=None, page_number=None):
        """
        Search for indicators containing a search term.

        :param str search_term: The term to search for.
        :param list(str) enclave_ids: list of enclave ids used to restrict to indicators found in reports in specific
            enclaves (optional - by default reports from all of the user's enclaves are used)
        :param int page_number: the page number to get.
        :param int page_size: the size of the page to be returned.
        :return: a |Page| of |Indicator| objects.
        """

        params = {
            'searchTerm': search_term,
            'enclaveIds': enclave_ids,
            'pageSize': page_size,
            'pageNumber': page_number
        }

        resp = self._client.get("indicators/search", params=params)

        return Page.from_dict(resp.json(), content_type=Indicator)

    def get_related_indicators(self, indicators=None, enclave_ids=None):
        """
        Uses the |get_related_indicators_page| method to create a generator that returns each successive report.

        :param list(string) indicators: list of indicator values to search for
        :param list(string) enclave_ids: list of GUIDs of enclaves to search in
        :return: The generator.
        """

        return Page.get_generator(page_generator=self._get_related_indicators_page_generator(indicators, enclave_ids))

    def get_indicators_for_report(self, report_id):
        """
        Creates a generator that returns each successive indicator for a given report.

        :param str report_id: The ID of the report to get indicators for.
        :return: The generator.
        """

        return Page.get_generator(page_generator=self._get_indicators_for_report_page_generator(report_id))

    def get_indicator_metadata(self, value):
        """
        Provide metadata associated with a single indicators, including value, indicatorType, noteCount,
        sightings, lastSeen, enclaveIds, and tags. The metadata is determined based on the enclaves the user making the
        request has READ access to.

        :param value: an indicator value to query.
        :return: A dict containing three fields: 'indicator' (an |Indicator| object), 'tags' (a list of |Tag|
            objects), and 'enclaveIds' (a list of enclave IDs that the indicator was found in).

        .. warning:: This method is deprecated.  Please use |get_indicators_metadata| instead.
        """

        result = self.get_indicators_metadata([Indicator(value=value)])
        if len(result) > 0:
            indicator = result[0]
            return {
                'indicator': indicator,
                'tags': indicator.tags,
                'enclaveIds': indicator.enclave_ids
            }
        else:
            return None

    def get_indicators_metadata(self, indicators):
        """
        Provide metadata associated with an list of indicators, including value, indicatorType, noteCount, sightings,
        lastSeen, enclaveIds, and tags. The metadata is determined based on the enclaves the user making the request has
        READ access to.

        :param indicators: a list of |Indicator| objects to query.  Values are required, types are optional.  Types
            might be required to distinguish in a case where one indicator value has been associated with multiple types
            based on different contexts.
        :return: A list of |Indicator| objects.  The following attributes of the objects will be returned:  
            correlation_count, last_seen, sightings, notes, tags, enclave_ids.  All other attributes of the Indicator
            objects will have Null values.  
        """

        data = [{
            'value': i.value,
            'indicatorType': i.type
        } for i in indicators]

        resp = self._client.post("indicators/metadata", data=json.dumps(data))

        return [Indicator.from_dict(x) for x in resp.json()]

    def get_indicators_metadata_robust(self, indicators):
        """
        The "get_indicators_metadata(..)" method accepts a list of Indicator objects and then queries Station for the
        metadata for all of those Indicators.  If for whatever reason Station crashes while retrieving the metadata
        for one of the indicators, the endpoint used by the "get_indicators_metadata(..)" method will return an error,
        and the method will throw an exception.  The "get_indicators_metadata_robust(..)" method handles that issue
        by repeatedly dividing the list by 2 and submits the smaller lists to the "get_indicators_metadata(..)" method
        again until metadata has been retrieved for all indicators possible and the indicators causing failure have
        been isolated into a separate list.

        :param indicators: a list of |Indicator| objects for which the user wants to obtain metadata.  Only the Indicator's
        "value" and "type" attributes are used by this method and the endpoint it queries.  All values for all other
        attributes of each |Indicator| instance will be discarded.  The return will contain values for attributes
        returned by the metadata endpoint.
        NOTE:  If one indicator's 'type' attribute contains a valid value, they all must.  This method does not check
        for that; the API call will fail if that rule is violated.

        :return: A tuple of lists of |Indicator| objects.  The first list in the tuple is the list of indicator objects
        for which the method was able to obtain metadata, and the second list is the list of indicator objects for
        which the method was not able to obtain metadata.  Each indicator for which the method was able to obtain
        metadata will have values for the following attributes:
            'value': string
            'type': string
            'sightings': integer
            'last_seen': integer, epoch timestamp
            'enclave_ids': list (str) of GUIDs that the user has access to and the indicator is present in.
            'tags': list (|Tag| objects), each tag containing values for the 'name', 'id', and 'enclave_id'
            attributes.
            'source': string
            'notes': list (str) of notes made on the indicator. 
        """

        MAX_N_INDICS_PER_LIST_SUBMITTED_FOR_METADATA = 1000            


        # DEDUPLICATE THE LIST OF INDICATORS. 
        # discard all attribute values other than value and type so we can dedupe on this later without other attrs messing up the dedup
        indicators = [ Indicator.from_dict( { Indicator.VALUE_API_PARAM : i.value, Indicator.TYPE_API_PARAM : i.type } ) ]

        # isolate singles & multiples.
        values = [i.value for i in idicators]
        singles = [i for i in indicators if values.count(i.value) == 1]
        multiples = [i for i in indicators if values.count(i.value) > 1]
        
        # dedup the multiples, but keep multiple entries for a single indicator value in the list if the entries have different values for their "type" attributes.
        multiples_deduped = [Indicator.from_dict(json.loads(i)) for i in list(set([str(i) for i in indicators]))]
        deduped_list_of_indics = list().extend(singles).extend(multiples)
        print(len(deduped_list_of_indics))
        print(len(singles)+len(multiples_deduped))
        
        # GROUP BY PRESENCE OF TYPES.
        indics_with_types = [i for i in deduped_list_of_indics if i.type]
        indics_no_types = [i for i in deduped_list_of_indics if not i.type]
        

        # BUILD LIST OF METADATA AND FAILURES.
        md_list = []
        n_indics_per_list = MAX_N_INDICS_PER_LIST_SUBMITTED_FOR_METADATA
        master_failures_list = []
        for l in [indics_with_types, indics_with_no_types]:

            big_list_of_indicators = l
            fails_list = []

            # loop until fails list and list of indicator lists are equal or the length of the fails list is zero. 
            while not ((len(fails_list) == len(list_of_indicator_lists)  and n_indics_per_list == 1) or len(fails_list) == 0):

                # a list to keep track of lists that fail when submitted to the metadata method. 
                fails_list = []

                # break big list into list of small lists.   
                list_of_indicator_lists = []
                sublist = []
                for i in big_list_of_indicators :
                    sublist.append(i)
                    if len(sublist) >= n_indics_per_list:
                        list_of_indicator_lists.append(sublist)
                        sublist = []                
                list_of_indicator_lists.append(sublist)  # catch the last sub-list.

                # filter out empty or Nonetype sub-lists.
                list_of_indicator_lists = [x for x in list_of_indicator_lists if x != []]
                list_of_indicator_lists = [x for x in list_of_indicator_lists if x]

                # submit each sub-list to metadata method.
                for indic_list in list_of_indicator_lists:
                    try:
                        md_list.extend(ts.get_indicators_metadata(indic_list))
                    except:
                        fails_list.extend(indic_list)

                # divide n by 2.
                if n_indics_per_list >= 2:
                    n_indics_per_list = int(n_indics_per_list/2)

                # recycle failures.     
                big_list_of_indicators = fails_list

                '''
                # end loop if all indicators fail and n_indics_per_list == 1
                if ( len( fails_list ) == len( list_of_indicator_lists )  and n_indics_per_list == 1 ) or len( fails_list ) == 0:
                    break
                '''
            master_failures_list.extend(fails_list)    
    return md_list, fails_list


    
    def get_indicator_details(self, indicators, enclave_ids=None):
        """
        NOTE: This method uses an API endpoint that is intended for internal use only, and is not officially supported.

        Provide a list of indicator values and obtain details for all of them, including indicator_type, priority_level,
        correlation_count, and whether they have been whitelisted.  Note that the values provided must match indicator
        values in Station exactly.  If the exact value of an indicator is not known, it should be obtained either through
        the search endpoint first.

        :param indicators: A list of indicator values of any type.
        :param enclave_ids: Only find details for indicators in these enclaves.

        :return: a list of |Indicator| objects with all fields (except possibly ``reason``) filled out
        """

        # if the indicators parameter is a string, make it a singleton
        if isinstance(indicators, string_types):
            indicators = [indicators]

        params = {
            'enclaveIds': enclave_ids,
            'indicatorValues': indicators
        }
        resp = self._client.get("indicators/details", params=params)

        return [Indicator.from_dict(indicator) for indicator in resp.json()]

    def get_whitelist(self):
        """
        Uses the |get_whitelist_page| method to create a generator that returns each successive whitelisted indicator.

        :return: The generator.
        """

        return Page.get_generator(page_generator=self._get_whitelist_page_generator())

    def add_terms_to_whitelist(self, terms):
        """
        Add a list of terms to the user's company's whitelist.

        :param terms: The list of terms to whitelist.
        :return: The list of extracted |Indicator| objects that were whitelisted.
        """

        resp = self._client.post("whitelist", json=terms)
        return [Indicator.from_dict(indicator) for indicator in resp.json()]

    def delete_indicator_from_whitelist(self, indicator):
        """
        Delete an indicator from the user's company's whitelist.

        :param indicator: An |Indicator| object, representing the indicator to delete.
        """

        params = indicator.to_dict()
        self._client.delete("whitelist", params=params)

    def get_community_trends(self, indicator_type=None, days_back=None):
        """
        Find indicators that are trending in the community.

        :param indicator_type: A type of indicator to filter by.  If ``None``, will get all types of indicators except
            for MALWARE and CVEs (this convention is for parity with the corresponding view on the Dashboard).
        :param days_back: The number of days back to search.  Any integer between 1 and 30 is allowed.
        :return: A list of |Indicator| objects.
        """

        params = {
            'type': indicator_type,
            'daysBack': days_back
        }

        resp = self._client.get("indicators/community-trending", params=params)
        body = resp.json()

        # parse items in response as indicators
        return [Indicator.from_dict(indicator) for indicator in body]

    def get_whitelist_page(self, page_number=None, page_size=None):
        """
        Gets a paginated list of indicators that the user's company has whitelisted.

        :param int page_number: the page number to get.
        :param int page_size: the size of the page to be returned.
        :return: A |Page| of |Indicator| objects.
        """

        params = {
            'pageNumber': page_number,
            'pageSize': page_size
        }
        resp = self._client.get("whitelist", params=params)
        return Page.from_dict(resp.json(), content_type=Indicator)
    
    def get_indicators_for_report_page(self, report_id, page_number=None, page_size=None):
        """
        Get a page of the indicators that were extracted from a report.

        :param str report_id: the ID of the report to get the indicators for
        :param int page_number: the page number to get.
        :param int page_size: the size of the page to be returned.
        :return: A |Page| of |Indicator| objects.
        """

        params = {
            'pageNumber': page_number,
            'pageSize': page_size
        }
        resp = self._client.get("reports/%s/indicators" % report_id, params=params)
        return Page.from_dict(resp.json(), content_type=Indicator)

    def get_related_indicators_page(self, indicators=None, enclave_ids=None, page_size=None, page_number=None):
        """
        Finds all reports that contain any of the given indicators and returns correlated indicators from those reports.

        :param indicators: list of indicator values to search for
        :param enclave_ids: list of IDs of enclaves to search in
        :param page_size: number of results per page
        :param page_number: page to start returning results on
        :return: A |Page| of |Report| objects.
        """

        params = {
            'indicators': indicators,
            'enclaveIds': enclave_ids,
            'pageNumber': page_number,
            'pageSize': page_size
        }

        resp = self._client.get("indicators/related", params=params)

        return Page.from_dict(resp.json(), content_type=Indicator)

    def _get_indicators_for_report_page_generator(self, report_id, start_page=0, page_size=None):
        """
        Creates a generator from the |get_indicators_for_report_page| method that returns each successive page.

        :param str report_id: The ID of the report to get indicators for.
        :param int start_page: The page to start on.
        :param int page_size: The size of each page.
        :return: The generator.
        """

        get_page = functools.partial(self.get_indicators_for_report_page, report_id=report_id)
        return Page.get_page_generator(get_page, start_page, page_size)

    def _get_related_indicators_page_generator(self, indicators=None, enclave_ids=None, start_page=0, page_size=None):
        """
        Creates a generator from the |get_related_indicators_page| method that returns each
        successive page.

        :param indicators: list of indicator values to search for
        :param enclave_ids: list of IDs of enclaves to search in
        :param start_page: The page to start on.
        :param page_size: The size of each page.
        :return: The generator.
        """

        get_page = functools.partial(self.get_related_indicators_page, indicators, enclave_ids)
        return Page.get_page_generator(get_page, start_page, page_size)

    def _get_whitelist_page_generator(self, start_page=0, page_size=None):
        """
        Creates a generator from the |get_whitelist_page| method that returns each successive page.

        :param int start_page: The page to start on.
        :param int page_size: The size of each page.
        :return: The generator.
        """

        return Page.get_page_generator(self.get_whitelist_page, start_page, page_size)
