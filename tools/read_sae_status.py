#!/usr/bin/env python3
"""Read non-secret SAE and PHY diagnostics from the loaded driver."""
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

for properties in controllers(tree):
    result = {k: v for k, v in properties.items()
              if (k.startswith("RTWSAE") and k != "RTWSAERxHeaders") or
              k in ("RTW89HECapable", "RTW89HEEnabled", "RTW89NegotiatedPHY")}
    raw = properties.get("RTWSAERxHeaders", b"")
    count = properties.get("RTWSAERawData", 0)
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
    result["headers"] = records
    print(json.dumps(result, indent=2))
