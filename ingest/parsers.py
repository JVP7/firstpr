"""Parse dependency manifests into normalized package names."""

import json
import re
import tomllib

# Name at the start of a requirement line, per PEP 508.
_REQ_NAME = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)")


def normalize_pypi(name):
    """PEP 503 normalization: 'Flask_SQLAlchemy' -> 'flask-sqlalchemy'."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_requirements(text):
    """Return the set of PyPI package names in a requirements.txt."""
    names = set()
    for line in text.splitlines():
        line = line.split(" #", 1)[0].strip()
        # Skip comments, options (-r, -e, --index-url) and direct URLs / paths.
        if not line or line.startswith(("#", "-")) or "://" in line or line.startswith((".", "/")):
            continue
        match = _REQ_NAME.match(line)
        if match:
            names.add(normalize_pypi(match.group(1)))
    return names


def parse_pyproject(text):
    """Return the set of PyPI package names in a pyproject.toml (PEP 621, Poetry, PEP 735 groups)."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return set()
    project = data.get("project", {})
    specs = list(project.get("dependencies", []))
    for group in project.get("optional-dependencies", {}).values():
        specs += group
    for group in data.get("dependency-groups", {}).values():
        specs += [item for item in group if isinstance(item, str)]  # skip {include-group = ...}
    names = parse_requirements("\n".join(s for s in specs if isinstance(s, str)))

    poetry = data.get("tool", {}).get("poetry", {})
    tables = [poetry.get("dependencies", {}), poetry.get("dev-dependencies", {})]
    tables += [group.get("dependencies", {}) for group in poetry.get("group", {}).values()]
    for table in tables:
        names.update(normalize_pypi(name) for name in table if name.lower() != "python")
    return names


def parse_package_json(text):
    """Return the set of npm package names in a package.json (dependencies + devDependencies)."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return set()
    if not isinstance(data, dict):
        return set()
    names = set()
    for key in ("dependencies", "devDependencies"):
        deps = data.get(key)
        if isinstance(deps, dict):
            names.update(name.strip().lower() for name in deps if name.strip())
    return names
