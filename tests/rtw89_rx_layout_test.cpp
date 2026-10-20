#include "../rtw/hal_rtw89/Rtw89RxLayout.hpp"
#include <assert.h>
int main()
{
    uint8_t frame[80] = {};
    frame[0] = 0x08; frame[1] = 0x42; frame[27] = 0x20;
    Rtw89Rx::CCMPLayout layout;
    assert(Rtw89Rx::ccmpLayout(frame, 40, layout));
    assert(layout.headerLength == 24 && layout.keyIndex == 0 && !layout.multicast);
    assert(!Rtw89Rx::ccmpLayout(frame, 39, layout));
    frame[4] = 1; frame[27] = 0xa0;
    assert(Rtw89Rx::ccmpLayout(frame, 40, layout));
    assert(layout.keyIndex == 2 && layout.multicast);
    frame[0] = 0x88; frame[1] = 0xc3; frame[39] = 0xe0;
    assert(Rtw89Rx::ccmpLayout(frame, 52, layout));
    assert(layout.headerLength == 36 && layout.keyIndex == 3);
    assert(!Rtw89Rx::ccmpLayout(frame, 51, layout));
    frame[39] = 0;
    assert(!Rtw89Rx::ccmpLayout(frame, 80, layout));
    frame[0] = 0x80;
    assert(!Rtw89Rx::ccmpLayout(frame, 80, layout));
    assert(!Rtw89Rx::ccmpLayout(nullptr, 80, layout));
}
