/* SPDX-License-Identifier: GPL-2.0 OR BSD-3-Clause */
#pragma once
#include <stdint.h>

enum class RTWFamily { Unsupported, RTW88, RTW89 };

constexpr RTWFamily rtwFamilyForPCI(uint16_t vendor, uint16_t device)
{
    if (vendor != 0x10ec)
        return RTWFamily::Unsupported;
    switch (device) {
    case 0xb822: case 0xc822: case 0xc82f: case 0xc821: case 0xb821:
        return RTWFamily::RTW88;
    case 0x8852: case 0xa85a: case 0xb852: case 0xb85b: case 0xb851:
    case 0xb520: case 0xc852: case 0x8922: case 0x892b:
        return RTWFamily::RTW89;
    default:
        return RTWFamily::Unsupported;
    }
}
