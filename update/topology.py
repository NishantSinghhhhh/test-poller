"""Module for updating the database with topology data."""

import time
import socket
import yaml

from switchmap.core import log
from switchmap.core import general
from switchmap.server.db.table import device as _device
from switchmap.server.db.table import l1interface as _l1interface
from switchmap.server.db.table import vlan as _vlan
from switchmap.server.db.table import macip as _macip
from switchmap.server.db.table import macport as _macport
from switchmap.server.db.table import vlanport as _vlanport
from switchmap.server.db.table import mac as _mac
from switchmap.server.db.table import oui as _oui
from switchmap.server.db.table import (
    IDevice,
    IL1Interface,
    IVlan,
    IMacIp,
    IMac,
    IMacPort,
    IVlanPort,
    ProcessMacIP,
    TopologyResult,
    TopologyUpdates,
)


def process(data, idx_event, dns=True):
    """Process data received from a device.

    Args:
        data: Device data (dict)
        idx_event: Event idx_event
        dns: Do DNS lookups if True

    Returns:
        None

    """
    # Dump data to file
    filepath = '/tmp/{}.yaml'.format(data["misc"]["host"])
    with open(filepath, 'w') as outfile:
        yaml.dump(data, outfile, default_flow_style=False)

    # Process the device
    device(data, idx_event)
    l1interface(data)
    vlan(data)
    vlanport(data)
    mac(data, idx_event)
    macip(data, dns=dns)
    macport(data)


def device(data, idx_event):
    """Update the Device DB table.

    Args:
        data: Device data (dict)
        idx_event: Event idx_event

    Returns:
        None

    """
    # Initialize key variables
    exists = False
    hostname = data["misc"]["host"]
    row = IDevice(
        idx_zone=1,
        idx_event=idx_event,
        hostname=hostname,
        name=hostname,
        sys_name=data["system"]["SNMPv2-MIB"]["sysName"][0],
        sys_description=data["system"]["SNMPv2-MIB"]["sysDescr"][0],
        sys_objectid=data["system"]["SNMPv2-MIB"]["sysObjectID"][0],
        sys_uptime=data["system"]["SNMPv2-MIB"]["sysUpTime"][0],
        last_polled=data["misc"]["timestamp"],
        enabled=1,
    )

    # Log
    log_message = "Updating Device table for host {}".format(hostname)
    log.log2debug(1080, log_message)

    # Update the database
    exists = _device.exists(row.hostname)
    if bool(exists) is True:
        _device.update_row(exists.idx_device, row)
    else:
        _device.insert_row(row)

    # Log
    log_message = "Updated Device table for host {}".format(hostname)
    log.log2debug(1137, log_message)


def l1interface(data):
    """Update the L1interface DB table.

    Args:
        data: Device data (dict)

    Returns:
        None

    """
    # Initialize key variables
    exists = False
    hostname = data["misc"]["host"]
    interfaces = data["layer1"]

    # Log
    log_message = "Updating L1Interface table for host {}".format(hostname)
    log.log2debug(1128, log_message)

    # Get device data
    device_ = _device.exists(hostname)

    if bool(device_) is True:

        # Process each interface
        for ifindex, interface in sorted(interfaces.items()):
            exists = _l1interface.exists(device_.idx_device, ifindex)

            # Update the database
            if bool(exists) is True:
                # Calculate the ts_idle time
                ifadminstatus = interface.get("ifAdminStatus")
                ifoperstatus = interface.get("ifOperStatus")
                if ifadminstatus == 1 and ifoperstatus == 1:
                    # Port enabled with link
                    ts_idle = 0
                elif ifadminstatus == 2:
                    # Port disabled
                    ts_idle = 0
                else:
                    # Port enabled no link
                    if bool(exists.ts_idle) is True:
                        # Do nothing if already idle
                        ts_idle = exists.ts_idle
                    else:
                        # Otherwise create an idle time entry
                        ts_idle = int(time.time())

                # Add new row to the database table
                row = IL1Interface(
                    idx_device=device_.idx_device,
                    ifindex=ifindex,
                    duplex=interface.get("l1_duplex"),
                    ethernet=int(bool(interface.get("l1_ethernet"))),
                    nativevlan=interface.get("l1_nativevlan"),
                    trunk=int(bool(interface.get("l1_trunk"))),
                    ifspeed=interface.get("ifSpeed"),
                    ifalias=interface.get("ifAlias"),
                    ifdescr=interface.get("ifDescr"),
                    ifadminstatus=interface.get("ifAdminStatus"),
                    ifoperstatus=interface.get("ifOperStatus"),
                    cdpcachedeviceid=interface.get("cdpCacheDeviceId"),
                    cdpcachedeviceport=interface.get("cdpCacheDevicePort"),
                    cdpcacheplatform=interface.get("cdpCachePlatform"),
                    lldpremportdesc=interface.get("lldpRemPortDesc"),
                    lldpremsyscapenabled=interface.get("lldpRemSysCapEnabled"),
                    lldpremsysdesc=interface.get("lldpRemSysDesc"),
                    lldpremsysname=interface.get("lldpRemSysName"),
                    ts_idle=ts_idle,
                    enabled=int(bool(exists.enabled)),
                )

                _l1interface.update_row(exists.idx_l1interface, row)
            else:
                # Add new row to the database table
                row = IL1Interface(
                    idx_device=device_.idx_device,
                    ifindex=ifindex,
                    duplex=interface.get("l1_duplex"),
                    ethernet=int(bool(interface.get("l1_ethernet"))),
                    nativevlan=interface.get("l1_nativevlan"),
                    trunk=int(bool(interface.get("l1_trunk"))),
                    ifspeed=interface.get("ifSpeed"),
                    ifalias=interface.get("ifAlias"),
                    ifdescr=interface.get("ifDescr"),
                    ifadminstatus=interface.get("ifAdminStatus"),
                    ifoperstatus=interface.get("ifOperStatus"),
                    cdpcachedeviceid=interface.get("cdpCacheDeviceId"),
                    cdpcachedeviceport=interface.get("cdpCacheDevicePort"),
                    cdpcacheplatform=interface.get("cdpCachePlatform"),
                    lldpremportdesc=interface.get("lldpRemPortDesc"),
                    lldpremsyscapenabled=interface.get("lldpRemSysCapEnabled"),
                    lldpremsysdesc=interface.get("lldpRemSysDesc"),
                    lldpremsysname=interface.get("lldpRemSysName"),
                    ts_idle=0,
                    enabled=1,
                )

                _l1interface.insert_row(row)

        # Log
        log_message = "Updated L1Interface table for host {}".format(hostname)
        log.log2debug(1138, log_message)

    else:

        # Log
        log_message = "No interfaces detected for for host {}".format(hostname)
        log.log2debug(1139, log_message)


def vlan(data):
    """Update the Vlan DB table.

    Args:
        data: Device data (dict)

    Returns:
        None

    """
    # Initialize key variables
    exists = False
    hostname = data["misc"]["host"]
    interfaces = data["layer1"]
    rows = []
    unique_vlans = []

    # Log
    log_message = "Updating Vlan table for host {}".format(hostname)
    log.log2debug(1131, log_message)

    # Get device data
    device_ = _device.exists(hostname)

    if bool(device_) is True:

        # Process each interface
        for ifindex, interface in sorted(interfaces.items()):
            exists = _l1interface.exists(device_.idx_device, ifindex)

            # Process each Vlan
            if bool(exists) is True:
                vlans = interface.get("l1_vlans")
                if isinstance(vlans, list) is True:
                    for next_vlan in vlans:
                        rows.append(
                            IVlan(
                                idx_device=device_.idx_device,
                                vlan=next_vlan,
                                name=None,
                                state=0,
                                enabled=1,
                            )
                        )

    # Do Vlan insertions
    unique_vlans = list(set(rows))

    for item in unique_vlans:

        vlan_exists = _vlan.exists(item.idx_device, item.vlan)

        if vlan_exists is False:
            _vlan.insert_row(item)
        else:
            _vlan.update_row(vlan_exists.idx_vlan, item)

    # Log
    log_message = "Updated Vlan table for host {}".format(hostname)
    log.log2debug(1140, log_message)


def vlanport(data):
    """Update the VlanPort DB table.

    Args:
        data: Device data (dict)

    Returns:
        None

    """
    # Initialize key variables
    hostname = data["misc"]["host"]
    interfaces = data["layer1"]

    # Log
    log_message = "Updating VlanPort table for host {}".format(hostname)
    log.log2debug(1194, log_message)

    # Get device data
    device_ = _device.exists(hostname)

    if bool(device_) is True:
        # Process each interface
        for ifindex, interface in sorted(interfaces.items()):
            l1_exists = _l1interface.exists(device_.idx_device, ifindex)

            # Process each Vlan
            if bool(l1_exists) is True:
                _vlans = interface.get("l1_vlans")
                if bool(_vlans) is True:
                    for item in sorted(_vlans):
                        # Ensure the Vlan exists in the database
                        vlan_exists = _vlan.exists(device_.idx_device, item)
                        if bool(vlan_exists) is True:
                            row = IVlanPort(
                                idx_l1interface=l1_exists.idx_l1interface,
                                idx_vlan=vlan_exists.idx_vlan,
                                enabled=1,
                            )
                            # Update the VlanPort database table
                            vlanport_exists = _vlanport.exists(
                                l1_exists.idx_l1interface, vlan_exists.idx_vlan
                            )
                            if bool(vlanport_exists) is True:
                                _vlanport.update_row(
                                    vlanport_exists.idx_vlanport, row
                                )
                            else:
                                _vlanport.insert_row(row)

    # Log
    log_message = "Updated VlanPort table for host {}".format(hostname)
    log.log2debug(1195, log_message)


def mac(data, idx_event):
    """Update the Mac DB table.

    Args:
        data: Device data (dict)
        idx_event: Event idx_event

    Returns:
        None

    """
    # Initialize key variables
    exists = False
    hostname = data["misc"]["host"]
    interfaces = data["layer1"]
    all_macs = []
    unique_macs = []
    unique_ouis = []
    lookup = {}

    # Log
    log_message = "Updating Mac table for host {}".format(hostname)
    log.log2debug(1134, log_message)

    # Get device data
    device_ = _device.exists(hostname)

    if bool(device_) is True:
        # Process each interface
        for ifindex, interface in interfaces.items():
            exists = _l1interface.exists(device_.idx_device, ifindex)

            # Process each Mac
            if bool(exists) is True:
                these_macs = interface.get("l1_macs")
                if bool(these_macs) is True:
                    all_macs.extend(these_macs)

    # Get macs and ouis
    unique_macs = list(set(_.lower() for _ in all_macs))
    unique_ouis = list(set([_[:6].lower() for _ in unique_macs]))

    # Process ouis
    for item in sorted(unique_ouis):
        exists = _oui.exists(item)
        lookup[item] = exists.idx_oui if bool(exists) is True else 1

    # Process macs
    for item in sorted(unique_macs):
        exists = _mac.exists(item)
        row = IMac(
            idx_oui=lookup.get(item[:6], 1),
            idx_zone=1,
            idx_event=idx_event,
            mac=item,
            enabled=1,
        )
        if bool(exists) is False:
            _mac.insert_row(row)
        else:
            _mac.update_row(exists.idx_mac, row)

    # Log
    log_message = "Updated Mac table for host {}".format(hostname)
    log.log2debug(1136, log_message)


def macport(data):
    """Update the MacPort DB table.

    Args:
        data: Device data (dict)

    Returns:
        None

    """
    # Initialize key variables
    hostname = data["misc"]["host"]
    interfaces = data["layer1"]

    # Log
    log_message = "Updating MacPort table for host {}".format(hostname)
    log.log2debug(1135, log_message)

    # Get device data
    device_ = _device.exists(hostname)

    if bool(device_) is True:
        # Process each interface
        for ifindex, interface in sorted(interfaces.items()):
            l1_exists = _l1interface.exists(device_.idx_device, ifindex)

            # Process each Mac
            if bool(l1_exists) is True:
                _macs = interface.get("l1_macs")
                if bool(_macs) is True:
                    for item in sorted(_macs):
                        # Ensure the Mac exists in the database
                        mac_exists = _mac.exists(item)
                        if bool(mac_exists) is True:
                            row = IMacPort(
                                idx_l1interface=l1_exists.idx_l1interface,
                                idx_mac=mac_exists.idx_mac,
                                enabled=1,
                            )
                            # Update the MacPort database table
                            macport_exists = _macport.exists(
                                l1_exists.idx_l1interface, mac_exists.idx_mac
                            )
                            if bool(macport_exists) is True:
                                _macport.update_row(
                                    macport_exists.idx_macport, row
                                )
                            else:
                                _macport.insert_row(row)

    # Log
    log_message = "Updated MacPort table for host {}".format(hostname)
    log.log2debug(1141, log_message)


def macip(data, dns=True):
    """Update the MacIp DB table.

    Args:
        data: MacIp data

    Returns:
        None

    """
    # Initialize key variables
    ipv6 = None
    ipv4 = None
    hostname = data["misc"]["host"]
    adds = []
    updates = []

    # Log
    log_message = "Updating MacIp table for host {}".format(hostname)
    log.log2debug(1148, log_message)

    # Get device data
    device_ = _device.exists(hostname)

    # Get MacIp data
    layer3 = data.get("layer3")
    if bool(layer3) is True and bool(device_) is True:
        ipv4 = layer3.get("ipNetToMediaTable")
        ipv6 = layer3.get("ipNetToPhysicalPhysAddress")

        # Process IPv4 data
        if bool(ipv4) is True:
            result = _process_macip(
                ProcessMacIP(table=ipv4, device=device_, version=4), dns=dns
            )
            adds.extend(result.adds)
            updates.extend(result.updates)

        # Process IPv6 data
        if bool(ipv6) is True:
            result = _process_macip(
                ProcessMacIP(table=ipv6, device=device_, version=6), dns=dns
            )
            adds.extend(result.adds)
            updates.extend(result.updates)

    # Do the Updates
    for item in sorted(updates):
        _macip.update_row(item.idx_macip, item.row)
    for item in sorted(adds):
        _macip.insert_row(item)

    # Log
    log_message = "Updated MacIp table for host {}".format(hostname)
    log.log2debug(1149, log_message)


def _process_macip(info, dns=True):
    """Update the mac DB table.

    Args:
        info: ProcessMacIP object
        dns: Do DNS lookup if True

    Returns:
        result

    """
    # Initialize key variables
    adds = []
    updates = []

    # Process data
    for next_ip_addr, next_mac_addr in info.table.items():
        # Create expanded lower case versions of the IP address
        ipmeta = general.ipaddress(next_ip_addr)
        if bool(ipmeta) is False:
            continue
        ip_address = ipmeta.address

        # Create lowercase version of mac address
        next_mac_addr = general.mac(next_mac_addr)

        # Update the database
        mac_exists = _mac.exists(next_mac_addr)
        if bool(mac_exists) is True:
            # Does the record exist?
            macip_exists = _macip.exists(
                info.device.idx_device, mac_exists.idx_mac, ip_address
            )

            # Get hostname for DB
            if bool(dns) is True:
                try:
                    hostname = socket.gethostbyaddr(ip_address)[0]
                except:
                    hostname = None
            else:
                hostname = None

            # Create a DB record
            row = IMacIp(
                idx_device=info.device.idx_device,
                idx_mac=mac_exists.idx_mac,
                ip_=ip_address,
                hostname=hostname,
                version=info.version,
                enabled=1,
            )
            if bool(macip_exists) is True:
                updates.append(
                    TopologyUpdates(idx_macip=macip_exists.idx_macip, row=row)
                )
            else:
                adds.append(row)

    # Return
    result = TopologyResult(adds=adds, updates=updates)
    return result
