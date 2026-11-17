from ingest.parsers import parse_cargo_toml, parse_go_mod, parse_package_json, parse_requirements


def test_requirements_handles_specifiers_extras_markers_and_options():
    text = """
# comment
Flask_SQLAlchemy>=3.0  # inline comment
requests[socks]==2.31 ; python_version >= "3.8"
numpy
-r dev.txt
-e git+https://github.com/x/y.git#egg=y
--index-url https://pypi.org/simple
git+https://github.com/a/b.git
./local/pkg
Django~=4.2
"""
    assert parse_requirements(text) == {"flask-sqlalchemy", "requests", "numpy", "django"}


def test_package_json_reads_dependencies_and_dev_dependencies():
    text = '{"dependencies": {"React": "^18", "@types/node": "20"}, "devDependencies": {"vite": "5"}, "peerDependencies": {"x": "1"}}'
    assert parse_package_json(text) == {"react", "@types/node", "vite"}


def test_package_json_tolerates_bad_input():
    assert parse_package_json("not json") == set()
    assert parse_package_json("[]") == set()
    assert parse_package_json('{"dependencies": "oops"}') == set()


def test_pyproject_reads_pep621_optional_groups_and_poetry():
    text = """
[project]
dependencies = ["httpx>=0.27", "Pydantic[email]"]
[project.optional-dependencies]
docs = ["mkdocs"]
[dependency-groups]
dev = ["pytest", {include-group = "docs"}]
[tool.poetry.dependencies]
python = "^3.10"
SQLAlchemy = "^2"
[tool.poetry.group.test.dependencies]
coverage = "*"
"""
    from ingest.parsers import parse_pyproject
    assert parse_pyproject(text) == {"httpx", "pydantic", "mkdocs", "pytest", "sqlalchemy", "coverage"}
    assert parse_pyproject("not = [toml") == set()


def test_go_mod_reads_direct_requirements_only():
    text = """module github.com/me/app

go 1.22

require github.com/Sirupsen/logrus v1.9.3

require (
	github.com/spf13/cobra v1.8.0
	// a comment
	golang.org/x/sys v0.20.0 // indirect
	gopkg.in/yaml.v3 v3.0.1
)

replace github.com/x/y => ../y
"""
    assert parse_go_mod(text) == {"github.com/sirupsen/logrus", "github.com/spf13/cobra", "gopkg.in/yaml.v3"}


def test_cargo_toml_reads_every_dependency_table():
    text = """
[package]
name = "app"

[dependencies]
serde = "1"
serde_json = { version = "1" }
tokio_alias = { version = "1", package = "tokio" }
local-crate = { path = "../local" }

[dev-dependencies]
criterion = "0.5"

[target.'cfg(windows)'.dependencies]
winapi = "0.3"

[workspace.dependencies]
anyhow = "1"
"""
    assert parse_cargo_toml(text) == {"serde", "serde-json", "tokio", "criterion", "winapi", "anyhow"}


def test_new_parsers_tolerate_bad_input():
    assert parse_cargo_toml("not = = toml") == set()
    assert parse_go_mod("") == set()
