/* SPDX-License-Identifier: GPL-2.0 OR BSD-3-Clause */
/* PCI-family selection for AirportRTW; not a second network state machine. */
#include "main.h"
#include "pci.h"
#include "rtw8821c.h"
#include "rtw8822b.h"
#include "rtw8822c.h"

int rtw88_native_probe(struct pci_dev *device)
{
    const struct rtw_chip_info *chip;
    if (!device || device->vendor != PCI_VENDOR_ID_REALTEK)
        return -ENODEV;
    switch (device->device) {
    case 0xb822: chip = &rtw8822b_hw_spec; break;
    case 0xc822: case 0xc82f: chip = &rtw8822c_hw_spec; break;
    case 0xc821: case 0xb821: chip = &rtw8821c_hw_spec; break;
    default: return -ENODEV;
    }
    struct pci_device_id id = {
        .vendor = PCI_VENDOR_ID_REALTEK,
        .device = device->device,
        .driver_data = (kernel_ulong_t)chip,
    };
    return rtw_pci_probe(device, &id);
}
