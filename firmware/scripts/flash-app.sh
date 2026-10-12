#!/bin/sh
# Flash the C6 app over USB with the OTA layout. Also the cargo runner for `firmware/app`.
#
# Usage: firmware/scripts/flash-app.sh [espflash flash options] <ELF>
#
# Every USB flash writes the rollback bootloader and `app/partitions.csv`, puts the image in
# ota_0 and erases otadata, so the bootloader starts that image and the firmware opens its
# one-time `esp-ota enroll` window. nvs (Matter fabrics) is never touched.
set -eu

firmware=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
bootloader="$firmware/bootloader/esp32c6-bootloader.bin"
partitions="$firmware/app/partitions.csv"

if [ ! -f "$bootloader" ]; then
    echo "flash-app: missing $bootloader" >&2
    echo "flash-app: copy the rollback-enabled bootloader per firmware/bootloader/README.md" >&2
    exit 1
fi

exec espflash flash --chip esp32c6 \
    --bootloader "$bootloader" \
    --partition-table "$partitions" \
    --target-app-partition ota_0 \
    --erase-parts otadata \
    "$@"
