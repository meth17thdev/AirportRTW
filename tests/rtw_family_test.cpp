/* SPDX-License-Identifier: GPL-2.0 OR BSD-3-Clause */
#include "../include/HAL/RTWDeviceMatch.hpp"
#include <assert.h>

static_assert(rtwFamilyForPCI(0x10ec, 0xc822) == RTWFamily::RTW88, "8822CE");
static_assert(rtwFamilyForPCI(0x10ec, 0xc852) == RTWFamily::RTW89, "8852CE");
static_assert(rtwFamilyForPCI(0x8086, 0xc822) == RTWFamily::Unsupported, "vendor");

int main()
{
    const uint16_t ids88[] = {0xb822, 0xc822, 0xc82f, 0xc821, 0xb821};
    const uint16_t ids89[] = {0x8852, 0xa85a, 0xb852, 0xb85b, 0xb851, 0xb520, 0xc852, 0x8922, 0x892b};
    for (auto id : ids88) assert(rtwFamilyForPCI(0x10ec, id) == RTWFamily::RTW88);
    for (auto id : ids89) assert(rtwFamilyForPCI(0x10ec, id) == RTWFamily::RTW89);
    assert(rtwFamilyForPCI(0x10ec, 0xffff) == RTWFamily::Unsupported);
    assert(rtwFamilyForPCI(0, 0) == RTWFamily::Unsupported);
}
