// Host-side regression checks for untrusted native Wi-Fi request decoding.
#include "../AirportRTW/WCL/WCL.hpp"
#include <assert.h>

int main()
{
    using namespace AirportWCL;
    const uint8_t valid[] = {0, 3, 'a', 'p', '1', 1, 1, 0x82};
    const uint8_t truncated[] = {0, 3, 'a'};
    assert(validIEs(valid, sizeof(valid)));
    assert(!validIEs(truncated, sizeof(truncated)));
    assert(!validIEs(nullptr, 3));

    uint8_t request[0x2cc] = {};
    JoinRequest join;
    // An empty request, an oversized SSID and a multicast AP must all fail.
    assert(!decodeJoin(request, sizeof(request), join));
    request[0x10] = 1;
    request[0x1c] = 3;
    memcpy(request + 0x20, "ap1", 3);
    request[0x214] = 1;
    request[0x21c] = 2;
    assert(decodeJoin(request, sizeof(request), join));
    assert(classifyLegacyAuth(join) == LegacyAuth::Open);
    assert(!decodeJoin(request, 0x218, join));
    request[0x1c] = 33;
    assert(!decodeJoin(request, sizeof(request), join));
    request[0x1c] = 3;
    request[0x21c] = 1;
    assert(!decodeJoin(request, sizeof(request), join));

    uint8_t channels[32] = {};
    channels[36 / 8] |= 1u << (36 % 8);
    assert(scanChannelSelected(channels, true, 36));
    assert(!scanChannelSelected(channels, true, 1));
    assert(!scanChannelSelected(channels, true, 256));
    assert(!probeChannel(true, true, false));
    assert(!probeChannel(true, false, true));

    const uint8_t mac[] = {2, 1, 2, 3, 4, 5};
    const uint8_t multicast[] = {1, 1, 2, 3, 4, 5};
    assert(planMacUpdate(mac, mac, sizeof(mac), false) == MacUpdate::Unchanged);
    assert(planMacUpdate(mac, multicast, sizeof(mac), false) == MacUpdate::Invalid);
    assert(!validCipherKey(6, 31, 0, 0, 0));
    assert(validCipherKey(6, 32, 0, 0, 8));
    return 0;
}
