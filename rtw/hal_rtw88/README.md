# Experimental RTW88 net80211 backend

`RTW88Hal` implements `RTWCore`, alongside `RTW89Hal`. It connects the existing
OpenBSD net80211 callbacks to the imported RTW88 PCI driver through an opaque
C++ bridge. The donor's `RTW88IEEE80211` state machine is not linked.

Initial PCI scope: RTL8821CE (`10ec:c821`, `10ec:b821`), RTL8822BE
(`10ec:b822`) and RTL8822CE (`10ec:c822`, `10ec:c82f`). Firmware for all three
chips is embedded; source/binary integrity is checked by the repository validator.
This does not establish successful firmware startup on hardware.

`scripts/build_rtw88_c_archive.sh` compiles the RTW88 C code, bridge and PCI
transport into one relocatable object. It localizes Linux compatibility symbols
before creating the archive, exposing the bridge and transport to the frontend.
This keeps RTW88's compatibility ABI separate from RTW89's.

Imported file notices, project notices and firmware attribution are retained.
See `LICENSE.linux`, `LICENSE.project`, `THIRD_PARTY_NOTICES.md`,
`ORIGINAL_WORK_NOTICE.md` and `firmware/README.md`.

This integration requires a macOS compile/link check and hardware testing.
See [validation and limitations](../../docs/REALTEK_HAL.md).
