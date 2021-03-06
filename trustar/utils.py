# python 2 backwards compatibility
from __future__ import print_function
from six import string_types

# external imports
import logging
import time
from datetime import datetime
import dateutil.parser
import pytz
from tzlocal import get_localzone


DAY = 24 * 60 * 60 * 1000


def normalize_timestamp(date_time):
    """
    TODO: get rid of this function and all references to it / uses of it.
    Attempt to convert a string timestamp in to a TruSTAR compatible format for submission.
    Will return current time with UTC time zone if None
    :param date_time: int that is seconds or milliseconds since epoch, or string/datetime object containing date, time,
    and (ideally) timezone.
    Examples of supported timestamp formats: 1487890914, 1487890914000, "2017-02-23T23:01:54", "2017-02-23T23:01:54+0000"
    :return If input is an int, will return milliseconds since epoch.  Otherwise, will return a normalized isoformat
    timestamp.
    """

    # if timestamp is null, just return the same null. 
    if not date_time:
        return date_time

    datetime_dt = datetime.now()

    # get current time in seconds-since-epoch
    current_time = int(time.time()) * 1000

    try:
        # identify type of timestamp and convert to datetime object
        if isinstance(date_time, int):

            # if timestamp has less than 10 digits, it is in seconds
            if date_time < 10000000000:
                date_time *= 1000

            # if timestamp is incorrectly forward dated, set to current time
            if date_time > current_time:
                raise ValueError("The given time %s is in the future." % date_time)

            return date_time

        if isinstance(date_time, str):
            datetime_dt = dateutil.parser.parse(date_time)
        elif isinstance(date_time, datetime):
            datetime_dt = date_time

    # if timestamp is none of the formats above, error message is printed and timestamp is set to current time by
    # default
    except Exception as e:
        logger.warning(e)
        logger.warning("Using current time as replacement.")
        datetime_dt = datetime.now()

    # if timestamp is timezone naive, add timezone
    if not datetime_dt.tzinfo:
        # add system timezone and convert to UTC
        datetime_dt = get_localzone().localize(datetime_dt).astimezone(pytz.utc)

    # converts datetime to iso8601
    return datetime_dt.isoformat()


def get_current_time_millis():
    """
    :return: the current time in milliseconds since epoch.
    """
    return int(time.time()) * 1000


def datetime_to_millis(dt):
    """
    Convert a ``datetime`` object to milliseconds since epoch.
    """
    return int(time.mktime(dt.timetuple())) * 1000


def get_logger(name=None):
    """
    Get a logger.  (Deprecated)
    :param name: The name of the logger.
    :return: The logger.
    """

    return logging.getLogger(name)


def get_time_based_page_generator(get_page, get_next_to_time, from_time=None, to_time=None):
    """
    A page generator that uses time-based pagination.

    :param get_page: a function to get the next page, given values for from_time and to_time
    :param get_next_to_time: get the to_time for the next query, given the result set and to_time for the previous query
    :param from_time: the initial from_time
    :param to_time: the initial to_time
    :return: a generator that yields each successive page
    """

    # default to_time to current time
    if to_time is None:
        to_time = get_current_time_millis()

    # default from_time to 1 day before to_time
    if from_time is None:
        from_time = to_time - DAY

    # stop iteration if get_next_to_time returns either None, or a to_time before from_time
    while to_time is not None and from_time <= to_time:
        # query the API for the next page
        result = get_page(from_time, to_time)
        # return the page
        yield result
        # use the given function to calculate the to_time of the next query
        new_to_time = get_next_to_time(result, to_time)
        # to_time should never increase between pages
        if new_to_time is not None:
            if new_to_time > to_time:
                raise Exception("to_time should not increase between page iterations.  "
                                "This can result in an endless loop.")
        # set the to_time for the next query
        to_time = new_to_time


def parse_boolean(value):
    """
    Coerce a value to boolean.

    :param value: the value, could be a string, boolean, or None
    :return: the value as coerced to a boolean
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, string_types):
        value = value.lower()
        if value == 'false':
            return False
        if value == 'true':
            return True

    raise ValueError("Could not convert value to boolean: {}".format(value))


logger = logging.getLogger(__name__)
