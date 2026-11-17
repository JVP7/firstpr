"""Parse dependency manifests into normalized package names."""

import json
import re
import tomllib
from xml.etree import ElementTree

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


def cargo_workspace_members(text):
    """The `[workspace] members` of a Cargo.toml: paths like "crates/core" or globs like "crates/*"."""
    try:
        members = tomllib.loads(text).get("workspace", {}).get("members", [])
    except tomllib.TOMLDecodeError:
        return []
    return [m for m in members if isinstance(m, str)]


def _local(tag):
    return tag.rsplit("}", 1)[-1]  # drop the XML namespace


def parse_pom(text):
    """Return "groupid:artifactid" for the dependencies and managed dependencies of a Maven pom.xml.
    Coordinates built from ${properties} are usually the project's own modules, so they're skipped."""
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return set()
    sections = [root] + [child for child in root if _local(child.tag) == "dependencyManagement"]
    names = set()
    for section in sections:
        for deps in (child for child in section if _local(child.tag) == "dependencies"):
            for dep in deps:
                fields = {_local(f.tag): (f.text or "").strip() for f in dep}
                group, artifact = fields.get("groupId", ""), fields.get("artifactId", "")
                if group and artifact and "${" not in group + artifact:
                    names.add(f"{group}:{artifact}".lower())
    return names


# A Gradle configuration (implementation, testImplementation, api, kapt, classpath...) followed by "group:artifact".
_GRADLE_DEP = re.compile(
    r"\b\w*(?:[Ii]mplementation|[Aa]pi|[Cc]ompileOnly|[Rr]untimeOnly|[Pp]rocessor|kapt|ksp|classpath)"
    r"""\s*\(?\s*(?:platform\s*\(\s*)?["']([\w.-]+):([\w.-]+)""")


def parse_gradle(text):
    """Return "group:artifact" for string-notation dependencies in a build.gradle or build.gradle.kts."""
    return {f"{group}:{artifact}".lower() for group, artifact in _GRADLE_DEP.findall(text)}


def parse_gradle_catalog(text):
    """Return "group:artifact" for the [libraries] of a Gradle version catalog (gradle/libs.versions.toml)."""
    try:
        libraries = tomllib.loads(text).get("libraries", {})
    except tomllib.TOMLDecodeError:
        return set()
    names = set()
    for spec in libraries.values():
        if isinstance(spec, dict):
            spec = spec.get("module") or f"{spec.get('group', '')}:{spec.get('name', '')}"
        if isinstance(spec, str) and spec.count(":") >= 1 and not spec.startswith(":") and not spec.endswith(":"):
            names.add(":".join(spec.split(":")[:2]).lower())
    return names


_GEM = re.compile(r"""^\s*gem\s*\(?\s*["']([^"']+)["']""", re.M)
_GEMSPEC_DEP = re.compile(r"""\badd_(?:runtime_|development_)?dependency\s*\(?\s*["']([^"']+)["']""")


def parse_gemfile(text):
    """Return the gem names in a Gemfile."""
    return {name.lower() for name in _GEM.findall(text)}


def parse_gemspec(text):
    """Return the gem names a .gemspec depends on (runtime and development)."""
    return {name.lower() for name in _GEMSPEC_DEP.findall(text)}


def parse_composer_json(text):
    """Return the Packagist "vendor/package" names in a composer.json (require + require-dev). Platform
    requirements like php and ext-json have no vendor, so the slash check drops them."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return set()
    if not isinstance(data, dict):
        return set()
    names = set()
    for key in ("require", "require-dev"):
        deps = data.get(key)
        if isinstance(deps, dict):
            names.update(name.strip().lower() for name in deps if "/" in name)
    return names
