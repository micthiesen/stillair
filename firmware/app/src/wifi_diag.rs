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

static CONNECTED: AtomicBool = AtomicBool::new(false);
static EVER_CONNECTED: AtomicBool = AtomicBool::new(false);
static RSSI_DBM: AtomicI32 = AtomicI32::new(UNAVAILABLE_RSSI);
static WEAKEST_RSSI_DBM: AtomicI32 = AtomicI32::new(UNAVAILABLE_RSSI);
static SAMPLES: AtomicU32 = AtomicU32::new(0);
static SAMPLE_FAILURES: AtomicU32 = AtomicU32::new(0);
static DISCONNECTS: AtomicU32 = AtomicU32::new(0);
static LAST_OK_MS: AtomicU64 = AtomicU64::new(0);

// `esp-radio::WifiController::rssi()` is a thin safe wrapper over this vendor ABI, but the
// Matter integration owns that controller for its entire lifetime and does not expose it.
// The function itself reads the station's last beacon and does not mutate configuration.
extern "C" {
    fn esp_wifi_sta_get_rssi(rssi: *mut i32) -> i32;
}

#[embassy_executor::task]
pub async fn sample_task() {
    Timer::after(FIRST_SAMPLE_DELAY).await;
    let mut reported_quality: Option<&'static str> = None;

    loop {
        let mut rssi = 0i32;
        // SAFETY: `rssi` is a valid, aligned out-pointer for the duration of the call. The
        // vendor API is designed to be queried while the station driver is running; a
        // disconnected or not-yet-started station returns an error, handled below.
        let result = unsafe { esp_wifi_sta_get_rssi(&mut rssi) };
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
