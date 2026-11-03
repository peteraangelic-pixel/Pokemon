//! Offline comparison of synthetic metadata. No network access or FFI.

/// A changed status or fingerprint is a triage hint, never a finding.
pub fn metadata_differs(status_a: u16, fingerprint_a: &str, status_b: u16, fingerprint_b: &str) -> bool {
    status_a != status_b || fingerprint_a != fingerprint_b
}

#[cfg(test)]
mod tests {
    use super::metadata_differs;

    #[test]
    fn identical_is_not_a_difference() {
        assert!(!metadata_differs(200, "same", 200, "same"));
    }

    #[test]
    fn changed_status_is_a_hint() {
        assert!(metadata_differs(200, "same", 403, "same"));
    }

    #[test]
    fn changed_fingerprint_is_a_hint() {
        assert!(metadata_differs(200, "a", 200, "b"));
    }
}
