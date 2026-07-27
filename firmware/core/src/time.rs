//! Monotonic time, injected rather than read.
//!
//! The supervisor never calls a clock itself. Every entry point takes the current
//! [`Millis`] from its caller, so tests advance time by arithmetic instead of by
//! sleeping, and a 10-second safe-boot hold costs a test nothing.

/// Milliseconds since boot, monotonic. Wrapping is not modelled: at one millisecond
/// per tick a `u64` covers roughly 584 million years.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Default)]
pub struct Millis(pub u64);

impl Millis {
    pub const ZERO: Self = Self(0);

    pub const fn from_secs(secs: u64) -> Self {
        Self(secs * 1_000)
    }

    /// Milliseconds elapsed since `earlier`, saturating at zero if time went backwards.
    pub const fn since(self, earlier: Self) -> u64 {
        self.0.saturating_sub(earlier.0)
    }

    pub const fn plus_ms(self, ms: u64) -> Self {
        Self(self.0.saturating_add(ms))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn since_saturates_instead_of_underflowing() {
        assert_eq!(Millis(500).since(Millis(200)), 300);
        assert_eq!(Millis(200).since(Millis(500)), 0);
    }

    #[test]
    fn from_secs_matches_plus_ms() {
        assert_eq!(Millis::from_secs(10), Millis::ZERO.plus_ms(10_000));
    }
}
