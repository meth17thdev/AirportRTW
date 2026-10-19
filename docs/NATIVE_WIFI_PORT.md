# Native Sequoia/Tahoe frontend port

## Scope and provenance

The frontend and Apple ABI declarations originate from jzrodriguez98/itlwm
commit `7e50738b80e65630040e2da22d464d0d13c847d3`, incorporating laobamac's
implementation. Copyright notices are retained. The donor repository is not
required to build AirportRTW after this port.

Catalina, Big Sur, Monterey, Ventura and the two Sonoma targets retain their
controller/interface sources. The Sequoia and Tahoe targets use separate
controller/interface sources under `AirportRTW/WCL/`, with unique header names
to prevent Xcode header-map collisions with older targets. Apple headers dispatch
to macOS15/macOS26 only when `AIRPORT_WCL` is defined. Shared net80211 changes
are conditional on that flag.

## Realtek integration

- `RTWCore` owns the existing Realtek hardware/net80211 backend. The former
  standalone controller is `RTWEthernetController`, still in `RTWCore.kext`.
- Realtek power-up success/failure and power-down generate native driver
  availability notifications. No Intel firmware initialization task is assumed.
- Native scan requests feed the software scanner. Requested SSIDs, active/
  passive policy and channel restrictions are honored. Beacon/probe events
  publish scan metadata and IEs; explicit discovery does not auto-associate.
- While connected, scans return cached results because `ic_bgscan_start` is not
  implemented by this Realtek backend. Discovering new APs off-channel while
  retaining the current link requires additional hardware integration.
- WCL joins configure the existing net80211 SSID, BSSID and WPA parameters.
  Existing Realtek association and key callbacks remain the hardware path.
  WPA2-Personal uses net80211's handshake. Enterprise PMK delivery is inherited
  but unverified and must not be advertised as tested.
- Association failures, deauthentication, link authorization and fresh associated
  beacons feed WCL completion/link events.
- Private MAC changes update BSD and net80211, then restart the interface so
  Realtek add_interface programs the new vif address into its MAC table. The
  efuse/permanent address stays unchanged. Failed restarts restore the old
  software address and attempt recovery. This path still requires hardware
  validation. HE is not advertised until Realtek HE/rate support is tested.

## AppleVTD/DMA review — separate from root patching

The DMA transport has intentionally not been replaced as part of the frontend
port. Neither compiling WCL nor avoiding userspace root patches establishes
AppleVTD compatibility.

Findings in `Rtw89PciTransport.cpp` and `compat/linux/dma-mapping.h`:

1. `allocateDMA` prepares an `IOBufferMemoryDescriptor`, then returns
   `getPhysicalAddress()` to the hardware. There is no device-specific `IOMapper`
   or `IODMACommand` IOVA translation.
2. Streaming mappings allocate bounce buffers and copy at ownership boundaries.
   Bounce buffers alone do not provide IOMMU mappings.
3. `dma_set_mask`, `dma_set_coherent_mask` and their combined variant return
   success without recording/enforcing a device mask. The allocator currently
   constrains physical backing to a 32-bit mask.
4. Linux-derived PCI TX/RX paths can allocate/map buffers during operation and
   under synchronization. `IODMACommand::prepare` can block; replacing
   `getPhysicalAddress()` with a mapping call in those contexts is not sufficient.
   The bundled SDK explicitly documents the context restriction.
5. Deferred freeing already avoids releasing descriptors with preemption
   disabled, but mapping lifetime, reset quiescence and buffer reuse still need
   validation against the hardware queues.

Required implementation for verified VT-d operation:

- Obtain the PCI device's mapper and establish mapped `IODMACommand` resources
  in a context where mapping can sleep.
- Preallocate mapped packet/ring resources, return device-visible IOVAs, and
  enforce DMA masks and segment/alignment restrictions.
- Keep mappings alive until hardware has completed or stopped DMA. Quiesce
  interrupt/TX/RX/reset activity before reclaiming resources.
- Implement direction-aware synchronization and preserve streaming copy-back
  semantics, including failure and reset paths.
- Validate with AppleVTD active: firmware load, scan, sustained bidirectional
  traffic, pool exhaustion, power cycling, sleep/wake, and detach/reset recovery.

There is no claim of working AppleVTD support from this change. A follow-up DMA
implementation should be reviewed and tested separately from the Wi-Fi frontend.

## Validation

`python3 tools/validate_rtw89_backend.py` parses the OpenStep project, verifies
eight OS target configurations and frontend isolation, resolves schemes, checks
Realtek personalities and C archive inputs, and verifies embedded firmware
against the six source binaries. `tools/wire_rtw89_xcode.py` is idempotent and
maintains only Realtek C++ backend source-phase coverage; C driver files remain
in the dedicated C archive.

CI builds Debug/Release for each OS target on an Intel macOS runner. It also
compiles host-side WCL request/layout regression checks for both ABIs. These
checks do not prove that private Apple class layouts match every OS update.

The development host is Windows: Xcode compilation, linking and loading have
not been executed locally. The CI workflow is prepared, not a reported successful
CI run. Initial hardware validation must include cold boot, scans on both bands,
open/WPA2 association, DHCP, traffic, disconnect/reconnect, Wi-Fi power toggling
and sleep/wake. Repeat existing smoke tests on older OS builds to detect shared
net80211 regressions.
