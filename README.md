# AirportRTW

macOS Wi-Fi driver for supported Realtek RTW89 PCIe cards.

## Compatibility

Build targets cover macOS High Sierra (10.13) through Sonoma (14), plus an
experimental native Wi-Fi frontend for Sequoia 15.2+ and Tahoe 26.x on x86_64.
The new targets require macOS/Xcode builds and hardware validation before
their compatibility can be considered established.

Supported cards:

- RTL8851BE
- RTL8852AE
- RTL8852BE
- RTL8852BTE
- RTL8852CE
- RTL8922AE

## Build Catalina through Tahoe

Install Xcode command-line tools and check out MacKernelSDK commit
`3f750085caa17ec3a7880f11c11bf4f48cd6a164` in `MacKernelSDK/`.

```sh
python3 tools/validate_rtw89_backend.py
bash scripts/build_release_kexts.sh
# Or select one target:
bash scripts/build_release_kexts.sh AirportRTW-Sequoia
bash scripts/build_release_kexts.sh AirportRTW-Tahoe
# Debug builds:
CONFIGURATION=Debug bash scripts/build_release_kexts.sh AirportRTW-Tahoe
```

Outputs are in `build/releases/Release/<OS>/AirportRTW.kext` (or `Debug`).
Sequoia and Tahoe also have shared schemes with the same names as their targets.
The older targets keep their existing frontend implementations; only the new
targets define `AIRPORT_WCL` and compile `AirportRTW/WCL/`.

The new frontend is intended to use the installed OS Wi-Fi stack without OCLP's
userspace Wi-Fi root patches. This has not yet been verified on hardware. Do not
mix native and legacy-stack instructions. Restrict Sequoia to Darwin
24.2.0–24.99.99 and Tahoe to 25.0.0–25.99.99 when sharing an OpenCore configuration.
The Sequoia ABI starts at 15.2; 15.0/15.1 are not covered by the new target.

Initial limitations: associated scans use cached results because the Realtek HAL
does not implement off-channel background scans; private MAC changes are wired through interface reinitialization but unverified;
HE/Wi-Fi 6 is not advertised by the new frontend. WPA3-only,
mandatory PMF and AWDL/AirDrop are not established features of this port.

The backend class is `RTWCore`; the standalone Ethernet controller class is
`RTWEthernetController`, retaining the `RTWCore.kext` product name.

See [port status and AppleVTD review](docs/NATIVE_WIFI_PORT.md) for validation
requirements and the separate DMA work still needed for verified VT-d support.

## Older Ventura-build workaround for Tahoe

The older implementation uses the Ventura 13 kext with a restored legacy Wi-Fi
stack. These instructions apply to that build, not the new `AirportRTW-Tahoe`
target. Keep a working recovery USB and back up your EFI first.

1. Copy `AirportRTW.kext` from the Ventura 13 build to `EFI/OC/Kexts`.
2. Add current, mutually compatible builds of `Lilu.kext`, `AMFIPass.kext`, `IOSkywalkFamily.kext`, and `IO80211FamilyLegacy.kext`. Obtain the restored Apple networking components through [OpenCore Legacy Patcher](https://dortania.github.io/OpenCore-Legacy-Patcher/), not from unofficial kext archives.
3. In OpenCore `Kernel -> Add`, load the kexts in this order: Lilu, AMFIPass, IOSkywalkFamily, IO80211FamilyLegacy, then AirportRTW. For AirportRTW use `Contents/MacOS/AirportRTW` as `ExecutablePath` and restrict the entry to Darwin `25.0.0`–`25.99.99`.
4. In `Kernel -> Block`, block `com.apple.iokit.IOSkywalkFamily` with strategy `Exclude` for Darwin `25.0.0`–`25.99.99`, allowing the restored version to load.
5. Set `Misc -> Security -> SecureBootModel` to `Disabled`, boot through OpenCore, and apply OCLP's **Post-Install Root Patch**. OCLP determines the required SIP/AMFI changes; do not copy security values from an unrelated machine.
6. Reboot and verify the stack with `kmutil showloaded | grep -Ei 'AirportRTW|IO80211|Skywalk'`.

Root patches are normally removed by macOS updates and must be reapplied. OCLP's Tahoe wireless work remains in development; check its [Tahoe support tracker](https://github.com/dortania/OpenCore-Legacy-Patcher/issues/1167) before updating.

## Credits

Special thanks to the [OpenIntelWireless/itlwm](https://github.com/OpenIntelWireless/itlwm) project. Its modular architecture provided the foundation we adapted to connect the Realtek backend to AirportRTW, making support for Realtek Wi-Fi cards possible.
