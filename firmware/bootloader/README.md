# Rollback-enabled bootloader

`esp32c6-bootloader.bin` is the ESP-IDF second-stage bootloader that `scripts/flash-app.sh`
writes on every USB flash.

| Field | Value |
| --- | --- |
| Source | [esp-lan-ota](https://github.com/micthiesen/esp-lan-ota) `bootloaders/esp32c6-bootloader.bin` at `9b6df67` (`9b6df6712f2727ecdc7cce8045e39b347085340c`) |
| ESP-IDF | `release/v5.5`, `v5.5.5-832-g2553c5ad432` (esp-lan-ota `bootloaders` workflow, run 38320654751) |
| SHA-256 | `97f6c5bf41da12eb1e656e7f27150965e60da72e83b09e496c14f90e456e04fd` (matches upstream `bootloaders/SHA256SUMS`) |

It is espflash's bundled bootloader configuration (ESP-IDF v5.5 defaults) plus
`CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y`, built with the 64 MB flash-size setting the C6's
64 KiB MMU page needs; espflash patches the real flash mode, speed and size at flash time.
An image activated as `New` becomes `PendingVerify` on its first boot; one still
`PendingVerify` at the next boot is marked `Aborted` and the previous slot starts.

Verify after replacing: `shasum -a 256 firmware/bootloader/esp32c6-bootloader.bin`. Update it
together with the esp-lan-ota rev in `app/Cargo.toml`.
