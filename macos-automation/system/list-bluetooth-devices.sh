#!/bin/bash
# ==============================================================================
# list-bluetooth-devices.sh - List paired Bluetooth devices
# ==============================================================================
# Description:
#   Lists paired Bluetooth devices showing name, connection status, and address.
#   Can filter to show only connected devices.
#
# Usage:
#   ./list-bluetooth-devices.sh
#   ./list-bluetooth-devices.sh --connected-only
#   ./list-bluetooth-devices.sh --limit 10
#
# Options:
#   --connected-only  Only show currently connected devices
#   --limit <n>       Maximum number of devices to show (default: 20)
#   -h, --help        Show this help message
#
# Example:
#   ./list-bluetooth-devices.sh
#   ./list-bluetooth-devices.sh --connected-only
#   ./list-bluetooth-devices.sh --limit 5
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Default values
CONNECTED_ONLY=false
LIMIT=20

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --connected-only)
            CONNECTED_ONLY=true
            shift
            ;;
        --limit)
            LIMIT="$2"
            shift 2
            ;;
        -h|--help)
            head -25 "$0" | tail -20
            exit 0
            ;;
        *)
            error_exit "Unknown option: $1"
            ;;
    esac
done

osascript -l JavaScript -e "
ObjC.import('IOBluetooth');

var devices = $.IOBluetoothDevice.pairedDevices();
var count = devices.count;
var connectedOnly = $CONNECTED_ONLY;
var limit = $LIMIT;
var results = [];

for (var i = 0; i < count; i++) {
    var device = devices.objectAtIndex(i);
    var name = '';
    try { name = ObjC.unwrap(device.name); } catch(e) { name = '(unknown)'; }
    var address = '';
    try { address = ObjC.unwrap(device.addressString); } catch(e) { address = ''; }
    var connected = device.isConnected();

    if (connectedOnly && !connected) continue;

    results.push({
        name: name || '(unknown)',
        address: address || '(unknown)',
        connected: connected ? 'Yes' : 'No'
    });

    if (results.length >= limit) break;
}

if (results.length === 0) {
    if (connectedOnly) {
        'No connected Bluetooth devices found.';
    } else {
        'No paired Bluetooth devices found.';
    }
} else {
    var output = '=== BLUETOOTH DEVICES ===\n\n';
    for (var j = 0; j < results.length; j++) {
        var d = results[j];
        output += 'Name: ' + d.name + '\n';
        output += 'Address: ' + d.address + '\n';
        output += 'Connected: ' + d.connected + '\n';
        output += '---\n';
    }
    output += '\nTotal: ' + results.length + ' device(s)';
    output;
}
" 2>/dev/null

if [[ $? -ne 0 ]]; then
    error_exit "Failed to list Bluetooth devices. IOBluetooth framework may not be available."
fi
