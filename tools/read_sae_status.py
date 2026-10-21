#!/usr/bin/env python3
"""Read non-secret WPA2/WPA3 join and PHY diagnostics from the loaded driver."""
import json
import plistlib
import struct
import subprocess

tree = plistlib.loads(subprocess.check_output(
    ["ioreg", "-a", "-r", "-c", "AirportRTW", "-l"]))

def controllers(value):
    if isinstance(value, dict):
        if "RTWSAEStage" in value:
            yield value
        for child in value.get("IORegistryEntryChildren", []):
            yield from controllers(child)
    elif isinstance(value, list):
        for child in value:
            yield from controllers(child)

def decode_headers(raw, count):
    records = []
    if isinstance(raw, bytes) and len(raw) == 128:
        for number in range(max(0, count - 8), count):
            control, length, flags, ether_type = struct.unpack_from("<IIII", raw, (number % 8) * 16)
            records.append({"number": number + 1, "control": hex(control), "length": length,
                "state": flags >> 8, "null_data": bool(control & 0x40),
                "protected": bool(control & 0x4000), "decrypted": bool(flags & 1),
                "iv_stripped": bool(flags & 2), "addressed_to_station": bool(flags & 4),
                "multicast": bool(flags & 8),
                "ether_type": None if ether_type == 0xffffffff else hex(ether_type)})
    return records

for properties in controllers(tree):
    result = {k: v for k, v in properties.items()
              if ((k.startswith("RTWSAE") or k.startswith("RTWLastIncompleteJoin"))
                  and not k.endswith("Headers")) or
              k in ("RTW89HECapable", "RTW89HEEnabled", "RTW89NegotiatedPHY")}
    result["headers"] = decode_headers(properties.get("RTWSAERxHeaders", b""),
                                        properties.get("RTWSAERawData", 0))
    result["last_incomplete_headers"] = decode_headers(
        properties.get("RTWLastIncompleteJoinHeaders", b""),
        properties.get("RTWLastIncompleteJoinData", 0))
    print(json.dumps(result, indent=2))
