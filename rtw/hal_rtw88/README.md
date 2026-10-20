# RTW88 PCIe HAL

This backend implements `ItlHalService` for RTL8822CE (10ec:c822/c82f),
RTL8822BE (10ec:b822), and RTL8821CE (10ec:c821/b821). RTL8822CE is the initial
hardware-validation target. Builds are available for native Tahoe and Sequoia.
They have not yet been validated on physical RTW88 hardware.

`RTW88Core` owns the net80211 controller and forwards hardware operations through
`Rtw88LinuxBridge` and `Rtw88PciTransport`. The existing net80211 scan, MLME,
security and replay logic and the existing native frontend are retained. The
donor's independent `RTW88IEEE80211` state machine is not imported.

Implemented paths include probe/unwind, enable/disable, firmware and private
MAC programming, software-driven scans, peer/channel setup, key installation
and removal, hardware CCMP with RX normalization, software crypto for other
net80211-supported ciphers, TX backpressure, RX delivery, per-TID queues,
Block Ack callbacks, multicast filters, EDCA and lifecycle cleanup. HT/VHT data
channel widths are negotiated up to 80 MHz. Hardware-level behavior, reconnect,
sleep/wake and sustained throughput require testing; compilation does not prove
them working. USB, SDIO, WoWLAN and HE/802.11ax are not implemented here.

## Build

First generate the shared frontend's native Xcode build recipes:

```sh
bash scripts/build_release_kexts.sh AirportRTW-Tahoe AirportRTW-Sequoia
python3 scripts/build_rtw88_kexts.py Tahoe Sequoia
python3 tools/validate_rtw88_backend.py --bundles
```

The RTW88 build compiles its own C archive and recompiles the shared native
sources against the RTW88 HAL headers, then links isolated bundles under
`build/rtw88/Release/{Tahoe,Sequoia}/AirportRTW.kext`. It never replaces the
ordinary RTW89 release output. Normal builds recompile all native sources;
`--incremental` can reuse native objects after source-only edits. Use a full
build after changing compiler flags or build recipes.

The RTW88 and RTW89 variants share the native frontend's bundle identifier and
classes. Install **one matching variant**, replacing the existing kext. They
are not a combined universal binary and must not be loaded together. The RTW88
variant's plist and HAL match only RTW88 IDs; it will not attach to an RTW89 card.
Do not install it on the existing RTL8852 machine as a replacement for its driver.

## Provenance

The hardware source comes from the supplied local
`Realtek88LegacyAirport/rtw88-stable` archive. `UPSTREAM.json` records hashes of
the imported driver files and firmware and the fetched comparison revision.
Original file notices and `driver/COPYING` are retained. The compatibility and
net80211-to-hardware adapter derive from AirportRTW's existing RTW89 port, with
RTW88-specific hardware setup and queue handling. The synchronous thread-call
cancellation shim comes from the supplied `Airport_RTW88/src/compat` reference.
Firmware is embedded unmodified in compressed form and its Realtek notice is
included both here and in each generated bundle's Resources directory.
