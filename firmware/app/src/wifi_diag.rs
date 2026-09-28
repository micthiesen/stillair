//! Low-rate, read-only Wi-Fi health sampling for the USB commissioning console.
//!
//! This deliberately does not create a LAN listener. Matter remains the only network-facing
//! service, while a technician with physical USB access can still verify RF margin after the
//! controller is installed in its metal-adjacent enclosure.

use core::sync::atomic::{AtomicBool, AtomicI32, AtomicU32, Ordering};

use embassy_time::{Duration, Instant, Timer};
use portable_atomic::AtomicU64;
use stillair_core::console::{wifi_quality, WifiDiagnostics};

const UNAVAILABLE_RSSI: i32 = i32::MAX;
const SAMPLE_INTERVAL: Duration = Duration::from_secs(10);
const FIRST_SAMPLE_DELAY: Duration = Duration::from_secs(5);
// `wifi_mode_t` values from the pinned esp-wifi-sys C6 bindings.
const WIFI_MODE_STA: u32 = 1;
const WIFI_MODE_APSTA: u32 = 3;

static CONNECTED: AtomicBool = AtomicBool::new(false);
static EVER_CONNECTED: AtomicBool = AtomicBool::new(false);
static RSSI_DBM: AtomicI32 = AtomicI32::new(UNAVAILABLE_RSSI);
static WEAKEST_RSSI_DBM: AtomicI32 = AtomicI32::new(UNAVAILABLE_RSSI);
static SAMPLES: AtomicU32 = AtomicU32::new(0);
static SAMPLE_FAILURES: AtomicU32 = AtomicU32::new(0);
static DISCONNECTS: AtomicU32 = AtomicU32::new(0);
static LAST_OK_MS: AtomicU64 = AtomicU64::new(0);

// Mirror `esp-radio::WifiController::rssi()`'s mode check and vendor ABI. Matter owns that
// controller and does not expose it. `wifi_mode_t` is C unsigned int (u32 on this target).
// These functions only read driver state; `get_mode` reports NOT_INIT before Wi-Fi starts.
extern "C" {
    fn esp_wifi_get_mode(mode: *mut u32) -> i32;
    fn esp_wifi_sta_get_rssi(rssi: *mut i32) -> i32;
    #[cfg(feature = "matter-diagnostics")]
    fn esp_wifi_get_mac(interface: u32, mac: *mut u8) -> i32;
}

#[embassy_executor::task]
pub async fn sample_task() {
    Timer::after(FIRST_SAMPLE_DELAY).await;
    let mut reported_quality: Option<&'static str> = None;
    #[cfg(feature = "matter-diagnostics")]
    let mut reported_driver = false;

    loop {
        let mut mode = 0u32;
        let mut rssi = 0i32;
        // SAFETY: both outputs are valid and aligned. Unlike get_mode, the RSSI function
        // can fault before initialization (sequential commissioning starts with BLE only).
        // Match the driver's safe wrapper: require initialized station mode first. There
        // is no await here, so Matter on this executor cannot drop the driver between calls.
        let result = unsafe {
            if esp_wifi_get_mode(&mut mode) == 0 && matches!(mode, WIFI_MODE_STA | WIFI_MODE_APSTA)
            {
                #[cfg(feature = "matter-diagnostics")]
                if !reported_driver {
                    // WIFI_IF_STA is 0; the vendor writes exactly six bytes. Read the actual
                    // radio MAC separately from the eFuse value Embassy uses. Do not create
                    // another Interface::station(): Matter already owns that singleton.
                    let mut mac = [0u8; 6];
                    let status = esp_wifi_get_mac(0, mac.as_mut_ptr());
                    let expected = esp_hal::efuse::interface_mac_address(
                        esp_hal::efuse::InterfaceMacAddress::Station,
                    );
                    log::info!(
                        "Wi-Fi driver MAC status={status} actual={mac:02x?} expected={:02x?}; PHY calibration {:?}",
                        expected.as_bytes(),
                        esp_radio::last_calibration_result()
                    );
                    reported_driver = true;
                }
                esp_wifi_sta_get_rssi(&mut rssi)
            } else {
                -1
            }
        };
        SAMPLES.fetch_add(1, Ordering::Relaxed);

        if result == 0 && i32::from(i8::MIN) <= rssi && rssi <= 0 {
            let rssi = rssi as i8;
            let was_connected = CONNECTED.swap(true, Ordering::AcqRel);
            RSSI_DBM.store(i32::from(rssi), Ordering::Relaxed);
            WEAKEST_RSSI_DBM.fetch_min(i32::from(rssi), Ordering::Relaxed);
            LAST_OK_MS.store(Instant::now().as_millis(), Ordering::Relaxed);

            if !was_connected {
                let reconnect = EVER_CONNECTED.swap(true, Ordering::AcqRel);
                log::info!(
                    "Wi-Fi {} at {rssi} dBm ({})",
                    if reconnect {
                        "reconnected"
                    } else {
                        "connected"
                    },
                    wifi_quality(rssi)
                );
            }

            let quality = wifi_quality(rssi);
            if reported_quality != Some(quality) {
                log::info!("Wi-Fi signal {quality}: {rssi} dBm");
                reported_quality = Some(quality);
            }
        } else {
            SAMPLE_FAILURES.fetch_add(1, Ordering::Relaxed);
            RSSI_DBM.store(UNAVAILABLE_RSSI, Ordering::Relaxed);
            reported_quality = None;
            if CONNECTED.swap(false, Ordering::AcqRel) {
                DISCONNECTS.fetch_add(1, Ordering::Relaxed);
                log::warn!("Wi-Fi RSSI became unavailable; association may be down");
            }
        }

        Timer::after(SAMPLE_INTERVAL).await;
    }
}

pub fn snapshot() -> WifiDiagnostics {
    WifiDiagnostics {
        connected: CONNECTED.load(Ordering::Acquire),
        rssi_dbm: load_rssi(&RSSI_DBM),
        weakest_rssi_dbm: load_rssi(&WEAKEST_RSSI_DBM),
        samples: SAMPLES.load(Ordering::Relaxed),
        sample_failures: SAMPLE_FAILURES.load(Ordering::Relaxed),
        disconnects: DISCONNECTS.load(Ordering::Relaxed),
        last_ok_ms: match LAST_OK_MS.load(Ordering::Relaxed) {
            0 => None,
            value => Some(value),
        },
    }
}

fn load_rssi(value: &AtomicI32) -> Option<i8> {
    match value.load(Ordering::Relaxed) {
        UNAVAILABLE_RSSI => None,
        value => i8::try_from(value).ok(),
    }
}
