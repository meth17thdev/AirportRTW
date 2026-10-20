#!/bin/bash
set -euo pipefail
ROOT="${PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
HAL="$ROOT/rtw/hal_rtw88"
COMPAT="$HAL/compat"
DRIVER="$HAL/driver"
OUT="${DERIVED_FILE_DIR:?DERIVED_FILE_DIR is required}"
SDK_PATH="${SDKROOT:?SDKROOT is required}"
mkdir -p "$OUT/rtw88-c"
flags=(-arch x86_64 -mmacosx-version-min=13.0 -isysroot "$SDK_PATH"
 -mkernel -fno-exceptions -fno-rtti -fno-stack-protector -O2
 -I"$ROOT/MacKernelSDK/Headers" -I"$COMPAT" -I"$COMPAT/linux" -I"$HAL"
 -I"$DRIVER" -include "$COMPAT/rtw88_compat.h"
 -DRTW88_MACOS=1 -D__KERNEL__ -DCONFIG_RTW88_PCI=1
 -DCONFIG_RTW88_8822C=1 -DCONFIG_RTW88_8822CE=1
 -DCONFIG_RTW88_8822B=1 -DCONFIG_RTW88_8822BE=1
 -DCONFIG_RTW88_8821C=1 -DCONFIG_RTW88_8821CE=1
 -Werror=implicit-function-declaration -Wno-unused-function -Wno-unused-variable)
objects=()
for file in main mac phy fw tx rx sec efuse coex ps regd bf sar util pci mac80211 rtw8822c rtw8822c_table rtw8822ce rtw8822b rtw8822b_table rtw8822be rtw8821c rtw8821c_table rtw8821ce; do
 echo "CC RTW88 $file.c"
 xcrun clang "${flags[@]}" -c "$DRIVER/$file.c" -o "$OUT/rtw88-c/$file.o"
 objects+=("$OUT/rtw88-c/$file.o")
done
for file in "$COMPAT/rtw88_compat.c" "$COMPAT/rtw88_thread_call.c" "$HAL/Rtw88Hardware.c"; do
 name="$(basename "$file" .c)"
 xcrun clang "${flags[@]}" -c "$file" -o "$OUT/rtw88-c/$name.o"
 objects+=("$OUT/rtw88-c/$name.o")
done
python3 "$ROOT/scripts/gen_fw_blobs.py" "$HAL/firmware" "$OUT/rtw88-c/fw_blobs.c"
for file in "$COMPAT/rtw88_firmware.c" "$OUT/rtw88-c/fw_blobs.c"; do
 name="$(basename "$file" .c)"
 xcrun clang -arch x86_64 -mkernel -O2 -isysroot "$SDK_PATH" -I"$ROOT/MacKernelSDK/Headers" -I"$COMPAT" -c "$file" -o "$OUT/rtw88-c/$name.o"
 objects+=("$OUT/rtw88-c/$name.o")
done
xcrun libtool -static -o "$OUT/librtw88_c.a" "${objects[@]}"
