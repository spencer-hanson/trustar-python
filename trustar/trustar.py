# python 2 backwards compatibility
from __future__ import print_function
from builtins import object, str
from future import standard_library
from six import string_types

# external imports
import configparser
import os
import yaml
import logging

# package imports
from .api_client import ApiClient
from .report_client import ReportClient
from .indicator_client import IndicatorClient
from .phishing_triage_client import PhishingTriageClient
from .tag_client import TagClient
from .models import EnclavePermissions, RequestQuota
from .utils import normalize_timestamp

from .version import __version__, __api_version__

# python 2 backwards compatibility
standard_library.install_aliases()


class TruStar(ReportClient, IndicatorClient, TagClient, PhishingTriageClient):

    logger = logging.getLogger(__name__)

    # raise exception if any of these config keys are missing
    REQUIRED_KEYS = ['api_key', 'api_secret']

    # allow configs to use different key names for config values
    REMAPPED_KEYS = {
        'auth_endpoint': 'auth',
        'api_endpoint': 'base',
        'user_api_key': 'api_key',
        'user_api_secret': 'api_secret'
    }

    # default config values
    DEFAULTS = {
        'auth': 'https://api.trustar.co/oauth/token',
        'base': 'https://api.trustar.co/api/1.3',
        'client_type': 'PYTHON_SDK',
        'client_version': __version__,
        'client_metatag': None,
        'verify': True,
        'retry': True,
        'max_wait_time': 60,
        'http_proxy': None,
        'https_proxy': None
    }

    def __init__(self, config_file=None, config_role=None, config=None):

        """
        Constructs and configures the instance.  Initially attempts to use ``config``; if it is ``None``,
        then attempts to use ``config_file`` instead.

        The only required config keys are ``user_api_key`` and ``user_api_secret``.  To obtain these values, login to
        TruSTAR Station in your browser and visit the **API** tab under **SETTINGS** to generate an API key and secret.

        All available keys, and their defaults, are listed below:

        +-------------------------+-----------+--------------------------------------------------+--------------------------------------------------------+
        | key                     | required  | default                                          | description                                            |
        +=========================+===========+==================================================+========================================================+
        | ``user_api_key``        | Yes       | ``True``                                         | API key                                                |
        +-------------------------+-----------+--------------------------------------------------+--------------------------------------------------------+
        | ``user_api_secret``     | Yes       | ``True``                                         | API secret                                             |
        +-------------------------+-----------+--------------------------------------------------+--------------------------------------------------------+
        | ``enclave_ids``         | No        | ``[]``                                           | a list (or comma-separated list) of enclave ids        |
        +-------------------------+-----------+--------------------------------------------------+--------------------------------------------------------+
        | ``auth_endpoint``       | No        | ``"https://api.trustar.co/oauth/token"``         | the URL used to obtain OAuth2 tokens                   |
        +-------------------------+-----------+--------------------------------------------------+--------------------------------------------------------+
        | ``api_endpoint``        | No        | ``"https://api.trustar.co/api/1.3"``             | the base URL used for making API calls                 |
        +-------------------------+-----------+--------------------------------------------------+--------------------------------------------------------+
        | ``verify``              | No        | ``True``                                         | whether to use SSL verification                        |
        +-------------------------+-----------+--------------------------------------------------+--------------------------------------------------------+
        | ``retry``               | No        | ``True``                                         | whether to wait and retry requests that fail with 429  |
        +-------------------------+-----------+--------------------------------------------------+--------------------------------------------------------+
        | ``max_wait_time``       | No        | ``60``                                           | fail if 429 wait time is greater than this (seconds)   |
        +-------------------------+-----------+--------------------------------------------------+--------------------------------------------------------+
        | ``client_type``         | No        | ``"Python_SDK"``                                 | the name of the client being used                      |
        +-------------------------+-----------+--------------------------------------------------+--------------------------------------------------------+
        | ``client_version``      | No        | the version of the Python SDK in use             | the version of the client being used                   |
        +-------------------------+-----------+--------------------------------------------------+--------------------------------------------------------+
        | ``client_metatag``      | No        | ``None``                                         | any additional information (ex. email address of user) |
        +-------------------------+-----------+--------------------------------------------------+--------------------------------------------------------+
        | ``http_proxy``          | No        | ``None``                                         | http proxy being used - http(s)://user:pwd@{ip}:{port} |
        +-------------------------+-----------+--------------------------------------------------+--------------------------------------------------------+
        | ``https_proxy``         | No        | ``None``                                         | https proxy being used - http(s)://user:pwd@{ip}:{port}|
        +-------------------------+-----------+--------------------------------------------------+--------------------------------------------------------+

        :param str config_file: Path to configuration file (conf, json, or yaml).  If no value is passed, the environment
            variable TRUSTAR_PYTHON_CONFIG_FILE will be used.  If that is not defined, defaults to "trustar.conf".
        :param str config_role: The section in the configuration file to use.  If no value is passed, the environment
            variable TRUSTAR_PYTHON_CONFIG_ROLE will be used.  If that is not defined, defaults to "trustar".
        :param dict config: A dictionary of configuration options.  This will override the config file path passed in
            the ``config_file`` parameter.
        """

        # attempt to use configuration file if one exists
        if config is None:

            # look for config path in environment variable
            if config_file is None:
                config_file = os.environ.get('TRUSTAR_PYTHON_CONFIG_PATH')

            # fallback to config file in current working directory
            if config_file is None:
                config_file = 'trustar.conf'

            # look for config role in environment variable
            if config_role is None:
                config_role = os.environ.get('TRUSTAR_PYTHON_CONFIG_ROLE')

            # fallback to config role 'trustar'
            if config_role is None:
                config_role = 'trustar'

            config = self.config_from_file(config_file, config_role)

        else:
            # copy so that the dictionary that was passed is not mutated
            config = config.copy()

        # remap config keys names
        for k, v in self.REMAPPED_KEYS.items():
            if k in config and v not in config:
                config[v] = config[k]

        # coerce value to boolean
        verify = config.get('verify')
        config['verify'] = self.parse_boolean(verify)

        # coerce value to boolean
        retry = config.get('retry')
        config['retry'] = self.parse_boolean(retry)

        max_wait_time = config.get('max_wait_time')
        if max_wait_time is not None:
            config['max_wait_time'] = int(max_wait_time)

        # override Nones with default values if they exist
        for key, val in self.DEFAULTS.items():
            if config.get(key) is None:
                config[key] = val

        # ensure required properties are present
        for key in self.REQUIRED_KEYS:
            if config.get(key) is None:
                raise Exception("Missing config value for %s" % key)

        self.enclave_ids = config.get('enclave_ids')

        if isinstance(self.enclave_ids, str):
            self.enclave_ids = [self.enclave_ids]

        # initialize api client
        self._client = ApiClient(config=config)

        # get API version and strip "beta" tag
        # This comes from base url passed in config
        # e.g. https://api.trustar.co/api/1.3-beta will give 1.3
        api_version = self._client.base.strip("/").split("/")[-1]

        # strip beta tag
        BETA_TAG = "-beta"
        api_version = api_version.strip(BETA_TAG)

        # /api resolves to version 1.2
        if api_version.lower() == "api":
            api_version = "1.2"

        # if API version does not match expected version, log a warning
        if api_version.strip(BETA_TAG) != __api_version__.strip(BETA_TAG):
            self.logger.warning("This version (%s) of the TruStar Python SDK is only compatible with version %s of"
                                " the TruStar Rest API, but is attempting to contact version %s of the Rest API."
                                % (__version__, __api_version__, api_version))

        # initialize token property
        self.token = None


    @staticmethod
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

    @staticmethod
    def config_from_file(config_file_path, config_role):
        """
        Create a configuration dictionary from a config file section.  This dictionary is what the TruStar
        class constructor ultimately requires.

        :param config_file_path: The path to the config file.
        :param config_role: The section within the file to use.
        :return: The configuration dictionary.
        """

        # read config file depending on filetype, parse into dictionary
        ext = os.path.splitext(config_file_path)[-1]
        if ext in ['.conf', '.ini']:
            config_parser = configparser.RawConfigParser()
            config_parser.read(config_file_path)
            roles = dict(config_parser)
        elif ext in ['.json', '.yml', '.yaml']:
            with open(config_file_path, 'r') as f:
                roles = yaml.safe_load(f)
        else:
            raise IOError("Unrecognized filetype for config file '%s'" % config_file_path)

        # ensure that config file has indicated role
        if config_role in roles:
            config = dict(roles[config_role])
        else:
            raise KeyError("Could not find role %s" % config_role)

        # parse enclave ids
        if 'enclave_ids' in config:
            # if id has all numeric characters, will be parsed as an int, so convert to string
            if isinstance(config['enclave_ids'], int):
                config['enclave_ids'] = str(config['enclave_ids'])
            # split comma separated list if necessary
            if isinstance(config['enclave_ids'], string_types):
                config['enclave_ids'] = config['enclave_ids'].split(',')
            elif not isinstance(config['enclave_ids'], list):
                raise Exception("'enclave_ids' must be a list or a comma-separated list")
            # strip out whitespace
            config['enclave_ids'] = [str(x).strip() for x in config['enclave_ids'] if x is not None]
        else:
            # default to empty list
            config['enclave_ids'] = []

        return config

    @staticmethod
    def normalize_timestamp(date_time):
        return normalize_timestamp(date_time)

    #####################
    ### API Endpoints ###
    #####################

    def ping(self):
        """
        Ping the API.

        Example:

        >>> ts.ping()
        pong
        """

        result = self._client.get("ping").content

        if isinstance(result, bytes):
            result = result.decode('utf-8')

        return result.strip('\n')

    def get_version(self):
        """
        Get the version number of the API.

        Example:

        >>> ts.get_version()
        1.3
        """

        result = self._client.get("version").content

        if isinstance(result, bytes):
            result = result.decode('utf-8')

        return result.strip('\n')

    def get_user_enclaves(self):
        """
        Gets the list of enclaves that the user has access to.

        :return: A list of |EnclavePermissions| objects, each representing an enclave and whether the requesting user
            has read, create, and update access to it.
        """

        resp = self._client.get("enclaves")
        return [EnclavePermissions.from_dict(enclave) for enclave in resp.json()]

    def get_request_quotas(self):
        """
        Gets the request quotas for the user's company.

        :return: A list of |RequestQuota| objects.
        """

        resp = self._client.get("request-quotas")
        return [RequestQuota.from_dict(quota) for quota in resp.json()]
