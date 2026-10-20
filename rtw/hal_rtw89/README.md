# RTW89 net80211 backend

`RTW89Hal` implements the shared `RTWCore` interface. The frontend uses
`RTWHalFactory` to select it from the PCI vendor/device ID. Its embedded
`rtw89_softc.sc_ic` remains the authoritative OpenBSD net80211 controller.

The class was previously named `RTWCore`; the standalone Ethernet product is
still called `RTWCore.kext`. That product name is independent of the shared
interface class.

Linux-derived driver code operates the hardware and firmware. It does not own
a parallel scan cache, association state machine, station database or key store.
Its C sources are compiled by `scripts/build_rtw89_c_archive.sh`.

See [the shared architecture](../../docs/REALTEK_HAL.md) and
[the native frontend notes](../../docs/NATIVE_WIFI_PORT.md).
