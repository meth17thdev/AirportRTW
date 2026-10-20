#!/usr/bin/env python3
"""Validate RTW88 hardware isolation, matching, firmware and optional bundles."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
HAL = ROOT/'rtw/hal_rtw88'
EXPECTED = {0xc822, 0xc82f, 0xb822, 0xc821, 0xb821}

def require(ok, message):
    if not ok: raise RuntimeError(message)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundles', action='store_true')
    parser.add_argument('--platforms', nargs='+', choices=['Tahoe', 'Sequoia'], default=['Tahoe', 'Sequoia'])
    opts = parser.parse_args()
    hardware = (HAL/'Rtw88Hardware.c').read_text()
    ids = {int(s,16) for s in re.findall(r'case (0x[0-9a-f]+):', hardware)}
    require(ids == EXPECTED, 'Probe IDs differ from supported PCIe cards')
    upstream = set()
    for chip in ['rtw8822ce', 'rtw8822be', 'rtw8821ce']:
        upstream.update(int(s,16) for s in re.findall(r'PCI_DEVICE\(PCI_VENDOR_ID_REALTEK,\s*(0x[0-9A-Fa-f]+)\)', (HAL/'driver'/f'{chip}.c').read_text()))
    require(ids == upstream, 'Probe must match actual upstream PCI ID tables')
    require('id.driver_data' in hardware and 'rtw_pci_probe(pdev, &id)' in hardware,
            'RTW88 requires actual chip specification at probe')
    for fw in ['rtw8821c_fw.bin','rtw8822b_fw.bin','rtw8822c_fw.bin']:
        require((HAL/'firmware'/fw).stat().st_size > 100000, 'Missing/truncated firmware: '+fw)
    require((HAL/'firmware/LICENCE.rtlwifi_firmware.txt').is_file(), 'Missing firmware notice')
    require(not list(HAL.rglob('*IEEE80211.cpp')), 'Donor MLME must not replace net80211')
    bridge = (HAL/'Rtw88LinuxBridge.cpp').read_text()
    require('stationAdded' in bridge and 'hw->txq_data_size' in bridge, 'Missing queue allocation/unwind')
    require('rtw88LinuxSetMacAddress' in bridge, 'Missing private MAC programming')
    require('IODelay(500)' not in (HAL/'compat/rtw88_compat.c').read_text(),
            'Timer teardown must wait for callbacks rather than guessing a delay')
    manifest = json.loads((HAL/'UPSTREAM.json').read_text())
    for path, expected in manifest['files'].items():
        require(hashlib.sha256((HAL/path).read_bytes()).hexdigest() == expected,
                'Imported donor file changed without provenance update: '+path)
    if opts.bundles:
        for platform in opts.platforms:
            bundle=ROOT/f'build/rtw88/Release/{platform}/AirportRTW.kext'
            plist=plistlib.loads((bundle/'Contents/Info.plist').read_bytes())
            matches={int(x,16)>>16 for p in plist['IOKitPersonalities'].values() for x in p.get('IOPCIMatch','').split()}
            require(matches==EXPECTED, platform+': incorrect PCI matches')
            require('com.apple.iokit.IO80211FamilyLegacy' not in plist['OSBundleLibraries'], 'Unexpected legacy stack')
            binary=bundle/'Contents/MacOS/AirportRTW'
            symbols=subprocess.check_output(['nm',str(binary)],text=True)
            require('_rtw8822c_hw_spec' in symbols and 'RTW88Core' in symbols, 'Missing RTW88 implementation')
            require('_rtw89_pci_probe' not in symbols, 'RTW89 hardware linked into RTW88 variant')
            unresolved=subprocess.check_output(['nm','-u',str(binary)],text=True)
            require(not any(line.strip().startswith(('_rtw','_airportrtw88')) for line in unresolved.splitlines()), 'Unresolved backend symbols')
            require((bundle/'Contents/Resources/LICENCE.rtlwifi_firmware.txt').is_file(), 'Packaged firmware notice missing')
    print('OK: RTW88 PCI matching, source provenance, firmware, isolation'+(' and both native bundles' if opts.bundles else ''))

if __name__=='__main__': main()
