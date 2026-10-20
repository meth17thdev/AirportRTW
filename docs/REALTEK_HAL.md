# Shared Realtek HAL

The frontend requests a backend from `RTWHalFactory` using the PCI vendor and
device ID. `RTWCore` is the shared interface; `RTW88Hal` and `RTW89Hal` are sibling
implementations. Each owns an OpenBSD net80211 controller and translates its
scan, association, key, aggregation and packet callbacks into hardware operations.
The Linux-derived code below each bridge operates that family's hardware.

```text
macOS Wi-Fi / Ethernet frontend
           |
       RTWCore interface
           |
    RTWHalFactory (PCI ID)
       /             \
  RTW88Hal         RTW89Hal
  net80211         net80211
     |                |
RTW88 bridge     RTW89 bridge
     |                |
RTW88 driver     RTW89 driver
```

All existing macOS target source lists now include both HALs and the factory,
including Catalina through Tahoe. The target's existing frontend remains in use.
This is source integration; it is not a claim of runtime compatibility on every OS.
The standalone Ethernet bundle remains `RTWCore.kext`.

## Validation

Run `python tools/validate_rtw89_backend.py`. Despite its historical name, it
checks both families: OS source coverage, frontend isolation, project structure,
PCI personalities, archive inputs and all nine embedded firmware images.
`tests/rtw_family_test.cpp` checks family selection; CI compiles and runs it.

Build a selected scheme/configuration on macOS or in GitHub Actions. The first
macOS pass must verify both archives compile and link, including RTW88 private
symbol localization. Then test an actual supported card:

1. PCI matching, firmware loading and interrupt initialization.
2. Active/passive scanning on 2.4 and 5 GHz.
3. Open and WPA2-CCMP association, DHCP and bidirectional traffic.
4. Disconnect/reconnect, aggregation and sleep/wake.
5. Repeat with an RTW89 card to check the shared-interface refactor.

The current architecture supports selecting either family for one active
adapter. Global workqueue and backend singleton state have not been redesigned
for simultaneous adapters. DMA still uses the existing physical-address model;
device-specific AppleVTD mapping is a separate unresolved task.

The Windows development environment cannot compile a macOS kernel extension or
validate a hardware boot. Keep this work experimental until those checks pass.
