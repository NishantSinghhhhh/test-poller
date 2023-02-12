"""SNMP Poller module."""

# Switchmap imports
from switchmap.poller.configuration import ConfigPoller
from . import snmp_info
from . import snmp_manager
from switchmap.core import log


class Poll:
    """Switchmap-NG agent that gathers data.

    Args:
        None

    Returns:
        None

    Functions:
        __init__:
        populate:
        post:
    """

    def __init__(self, hostname):
        """Initialize the class.

        Args:
            hostname: Hostname to poll

        Returns:
            None

        """
        # Initialize key variables
        self._server_config = ConfigPoller()()
        self._hostname = hostname
        self._snmp_object = None

        # Get snmp configuration information from Switchmap-NG
        validate = snmp_manager.Validate(hostname, _server_config.snmp_auth())
        snmp_params = validate.credentials()

        # Create an SNMP object for querying
        if _do_poll(snmp_params) is True:
            self._snmp_object = snmp_manager.Interact(snmp_params)
        else:
            log_message = (
                "Uncontactable or disabled host {}, or no valid SNMP "
                "credentials found for it.".format(self._hostname)
            )
            log.log2info(1081, log_message)

    def query(self):
        """Query all remote hosts for data.

        Args:
            None

        Returns:
            None

        """
        # Initialize key variables
        _data = None

        # Only query if wise
        if bool(self._snmp_object) is False:
            return _data

        # Get data
        log_message = """\
Querying topology data from host {}.""".format(
            self._hostname
        )
        log.log2info(1078, log_message)

        # Return the data polled from the device
        status = snmp_info.Query(self._snmp_object)
        _data = status.everything()
        return _data


def _do_poll(snmp_params):
    """Determine whether doing a poll is valid.

    Args:
        snmp_params: Dict of SMNP parameters

    Returns:
        poll: True if a poll should be done

    """
    # Initialize key variables
    poll = False

    if bool(snmp_params) is True:
        if isinstance(snmp_params, dict) is True:
            if "enabled" in snmp_params:
                if bool(snmp_params["enabled"]) is True:
                    poll = True
            else:
                # Default to poll unless otherwise stated
                poll = True

    # Return
    return poll
