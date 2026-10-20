#!/bin/bash
set -euo pipefail

ROOT="${PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
OUT_DIR="${DERIVED_FILE_DIR:?DERIVED_FILE_DIR is required}/rtw88-c"
OUT_LIB="${DERIVED_FILE_DIR}/librtw88_c.a"
SDK_PATH="${SDKROOT:?SDKROOT is required}"
BACKEND="$ROOT/rtw/hal_rtw88"
DRIVER="$BACKEND/driver"
COMPAT="$BACKEND/compat"
mkdir -p "$OUT_DIR"

COMMON=(
  -arch x86_64 "-mmacosx-version-min=${MACOSX_DEPLOYMENT_TARGET:-10.15}"
  -isysroot "$SDK_PATH" -fno-exceptions -fno-rtti -fno-stack-protector -mkernel
  # Tentative globals must be section definitions, not common symbols, so
  # nmedit can localize them in the private relocatable object.
  -fno-common
  -I"$ROOT/MacKernelSDK/Headers"
  -I"$SDK_PATH/System/Library/Frameworks/Kernel.framework/Headers"
)
CFLAGS=(
  "${COMMON[@]}" -I"$COMPAT" -I"$COMPAT/linux" -I"$DRIVER"
  -include "$COMPAT/rtw88_compat.h" -DRTW88_MACOS=1 -D__KERNEL__
  -DCONFIG_RTW88_PCI=1 -DCONFIG_RTW88_8822B=1 -DCONFIG_RTW88_8822BE=1
  -DCONFIG_RTW88_8822C=1 -DCONFIG_RTW88_8822CE=1
  -DCONFIG_RTW88_8821C=1 -DCONFIG_RTW88_8821CE=1
  -Werror=implicit-function-declaration -Wno-int-conversion
  -Wno-incompatible-pointer-types -Wno-unused-function -Wno-unused-variable
)
if [[ "${CONFIGURATION:-Release}" == Debug ]]; then OPT=(-O0 -g); else OPT=(-O2); fi
objects=()
compile_c() {
  local source="$1"
  shift
  local relative="${source#$ROOT/}"
  local object="$OUT_DIR/${relative//\//_}.o"
  echo "CC $relative"
  xcrun clang "$@" "${OPT[@]}" -c "$source" -o "$object"
  objects+=("$object")
}
for file in \
  main.c mac.c phy.c fw.c tx.c rx.c sec.c efuse.c coex.c ps.c regd.c \
  bf.c sar.c util.c pci.c mac80211.c \
  rtw8822b.c rtw8822b_table.c rtw8822be.c \
  rtw8822c.c rtw8822c_table.c rtw8822ce.c \
  rtw8821c.c rtw8821c_table.c rtw8821ce.c rtw88_native.c
do
  compile_c "$DRIVER/$file" "${CFLAGS[@]}"
done
compile_c "$COMPAT/rtw88_compat.c" "${CFLAGS[@]}"
compile_c "$COMPAT/rtw88_thread_call.c" "${CFLAGS[@]}"
compile_c "$COMPAT/rtw88_firmware.c" "${COMMON[@]}" -I"$COMPAT"
compile_c "$COMPAT/fw_blobs.c" "${COMMON[@]}" -I"$COMPAT"

# The bridge and transport use RTW88's own Linux compatibility ABI. They must
# be linked into the same private object before hiding duplicate Linux symbols.
for file in Rtw88LinuxBridge.cpp Rtw88PciTransport.cpp; do
  object="$OUT_DIR/$file.o"
  xcrun clang++ "${COMMON[@]}" "${OPT[@]}" -std=c++14 -fapple-kext -DKERNEL \
    -I"$COMPAT" -I"$COMPAT/linux" -I"$BACKEND" -I"$DRIVER" \
    -Wno-deprecated-declarations -Wno-nullability-completeness \
    -c "$BACKEND/$file" -o "$object"
  objects+=("$object")
done

# Localize RTW88 Linux/compat definitions so the existing RTW89 implementation
# cannot accidentally satisfy them (or cause duplicate-symbol link failures).
combined="$OUT_DIR/rtw88-private.o"
exports="$OUT_DIR/exports.txt"
xcrun ld -r -arch x86_64 -o "$combined" "${objects[@]}"
xcrun nm -gUj "$combined" | awk '/rtw88Linux|Rtw88PciTransport/' > "$exports"
test -s "$exports"
xcrun nmedit -s "$exports" "$combined"
unexpected=$(xcrun nm -gUj "$combined" | awk '!/rtw88Linux|Rtw88PciTransport/')
if [[ -n "$unexpected" ]]; then
  echo "Unexpected public RTW88 symbols: $unexpected" >&2
  exit 1
fi
xcrun libtool -static -o "$OUT_LIB" "$combined"
