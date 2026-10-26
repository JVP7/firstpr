from ingest.parsers import parse_package_json, parse_requirements


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
