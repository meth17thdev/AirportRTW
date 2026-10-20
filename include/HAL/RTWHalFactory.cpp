/* SPDX-License-Identifier: GPL-2.0 OR BSD-3-Clause */
#include "RTWHalFactory.hpp"
#include "RTW88Hal.hpp"
#include "RTW89Hal.hpp"

namespace {
RTWFamily family(IOPCIDevice *device)
{
    return device ? rtwFamilyForPCI(device->configRead16(kIOPCIConfigVendorID),
                                    device->configRead16(kIOPCIConfigDeviceID))
                  : RTWFamily::Unsupported;
}
}

bool RTWHalFactory::supports(IOPCIDevice *device)
{
    return family(device) != RTWFamily::Unsupported;
}

RTWCore *RTWHalFactory::create(IOPCIDevice *device)
{
    switch (family(device)) {
    case RTWFamily::RTW88: return new RTW88Hal;
    case RTWFamily::RTW89: return new RTW89Hal;
    default: return nullptr;
    }
}
