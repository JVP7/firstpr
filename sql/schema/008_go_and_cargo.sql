-- Allow Go modules (go.mod) and Rust crates (Cargo.toml) alongside PyPI and npm packages.
-- Additive: existing rows already satisfy the wider check, and code that only writes pypi/npm keeps working.

BEGIN;

ALTER TABLE packages
    DROP CONSTRAINT packages_ecosystem_check,
    ADD CONSTRAINT packages_ecosystem_check CHECK (ecosystem IN ('pypi', 'npm', 'go', 'cargo'));

COMMIT;
