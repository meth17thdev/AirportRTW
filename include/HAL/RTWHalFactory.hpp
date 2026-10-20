/* SPDX-License-Identifier: GPL-2.0 OR BSD-3-Clause */
#pragma once
#include "RTWCore.hpp"
#include "RTWDeviceMatch.hpp"

namespace RTWHalFactory {
    bool supports(IOPCIDevice *device);
    RTWCore *create(IOPCIDevice *device);
}
