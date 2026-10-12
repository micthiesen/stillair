# Rollback-enabled bootloader

`esp32c6-bootloader.bin` belongs here. It is not committed yet: esp-lan-ota's CI builds it,
and `scripts/flash-app.sh` refuses to flash until it is present.

Provenance: copy `bootloaders/esp32c6-bootloader.bin` (and its `esp32c6-idf-version.txt`)
from [esp-lan-ota](https://github.com/micthiesen/esp-lan-ota) at the revision pinned in
`app/Cargo.toml`. It is the ESP-IDF `release/v5.5` second-stage bootloader with espflash's
bundled defaults plus `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y`, built with the 64 MB
flash-size setting the C6's 64 KiB MMU page needs (espflash patches the real size at flash
time).

Without rollback, an OTA image that never confirms itself is not rolled back, and
`esp-ota status` reports `rollback unsupported`.
