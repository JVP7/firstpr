-- Allow Java (Maven coordinates), Ruby gems, PHP Composer packages, NuGet packages and C/C++ libraries
-- (vcpkg, Conan, CMake and Meson names share one namespace, since they name the same libraries).
-- Additive: existing rows already satisfy the wider check.

BEGIN;

ALTER TABLE packages
    DROP CONSTRAINT packages_ecosystem_check,
    ADD CONSTRAINT packages_ecosystem_check
        CHECK (ecosystem IN ('pypi', 'npm', 'go', 'cargo', 'maven', 'rubygems', 'packagist', 'nuget', 'c/c++'));

COMMIT;
