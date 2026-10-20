#include "../rtw/hal_rtw88/Rtw88RxLayout.hpp"
#include "../rtw/hal_rtw88/Rtw88LinkPolicy.hpp"
#include <assert.h>
int main()
{
    uint8_t frame[64] = {};
    Rtw88Rx::CCMPLayout layout;
    frame[0] = 0x88; // QoS data
    frame[1] = 0x42; // downlink, protected
    frame[29] = 0x20; // extended CCMP IV, pairwise key zero
    assert(Rtw88Rx::ccmpLayout(frame, 42, layout));
    assert(layout.headerLength == 26 && layout.keyIndex == 0 && !layout.multicast);
    assert(!Rtw88Rx::ccmpLayout(frame, 41, layout));
    frame[4] = 1; frame[29] = 0xa0;
    assert(Rtw88Rx::ccmpLayout(frame, 42, layout));
    assert(layout.multicast && layout.keyIndex == 2);
    frame[29] = 0x80;
    assert(!Rtw88Rx::ccmpLayout(frame, 42, layout));
    assert(!Rtw88Rx::ccmpLayout(nullptr, 42, layout));
    assert(Rtw88Link::validChannel(5180, 5210, 80));
    assert(!Rtw88Link::validChannel(2412, 2442, 80));
    assert(!Rtw88Link::validChannel(5180, 5180, 40));
    // A one-stream card must not acquire the AP's second stream.
    assert(Rtw88Link::intersectMCS(0xfffe, 0xfffa) == 0xfffe);
}
