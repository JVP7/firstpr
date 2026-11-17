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


def parse_go_mod(text):
    """Return the module paths a go.mod requires directly; `// indirect` ones are transitive, so skipped."""
    names, in_block = set(), False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("require ("):
            in_block = True
            continue
        if in_block and line.startswith(")"):
            in_block = False
            continue
        if line.startswith("require "):
            line = line[len("require "):].strip()
        elif not in_block:
            continue
        if not line or line.startswith("//") or "// indirect" in line:
            continue
        names.add(line.split()[0].lower())  # GitHub paths are case-insensitive
    return names


def _cargo_tables(data):
    """Every dependency table in a Cargo.toml, including workspace and target-specific ones."""
    keys = ("dependencies", "dev-dependencies", "build-dependencies")
    tables = [data.get(k, {}) for k in keys]
    tables.append(data.get("workspace", {}).get("dependencies", {}))
    for target in data.get("target", {}).values():
        tables += [target.get(k, {}) for k in keys if isinstance(target, dict)]
    return [t for t in tables if isinstance(t, dict)]


def parse_cargo_toml(text):
    """Return the crates.io crate names in a Cargo.toml. Local `path` crates are skipped; renamed
    dependencies (`alias = { package = "real" }`) count under their real name."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return set()
    names = set()
    for table in _cargo_tables(data):
        for name, spec in table.items():
            if isinstance(spec, dict):
                if "path" in spec:
                    continue
                name = spec.get("package", name)
            names.add(name.lower().replace("_", "-"))  # crates.io treats - and _ as the same name
    return names
