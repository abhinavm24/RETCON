"""Register RETCON's packaged DAGs without copying files into a DAG directory."""

from __future__ import annotations

import argparse
import configparser
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

BUNDLE_CLASS = "retcon.bundle.RetconDagBundle"
BUNDLE_CONFIG = {"name": "retcon", "classpath": BUNDLE_CLASS, "kwargs": {}}
DEFAULT_BUNDLE = {
    "name": "dags-folder",
    "classpath": "airflow.dag_processing.bundles.local.LocalDagBundle",
    "kwargs": {},
}
SECTION = "dag_processor"
OPTION = "dag_bundle_config_list"
ENV_OPTION = "AIRFLOW__DAG_PROCESSOR__DAG_BUNDLE_CONFIG_LIST"


class ConfigurationError(ValueError):
    """The existing configuration cannot be safely changed."""


def airflow_config_path() -> Path:
    """Resolve the normal Airflow config location without initializing Airflow."""
    config = os.environ.get("AIRFLOW_CONFIG")
    if config:
        return Path(config).expanduser()
    return Path(os.environ.get("AIRFLOW_HOME", "~/airflow")).expanduser() / "airflow.cfg"


def _read_configuration(path: Path) -> tuple[str, configparser.ConfigParser]:
    if path.exists():
        with path.open(encoding="utf-8", newline="") as source:
            text = source.read()
    else:
        text = ""
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read_string(text)
    except configparser.Error as exc:
        raise ConfigurationError(f"Cannot parse {path}; correct the existing INI configuration first.") from exc
    return text, parser


def _bundle_configuration(parser: configparser.ConfigParser) -> tuple[list[dict], bool]:
    for suffix in ("_CMD", "_SECRET"):
        if ENV_OPTION + suffix in os.environ or parser.has_option(SECTION, OPTION + suffix.lower()):
            raise ConfigurationError(
                f"{OPTION} is managed through {suffix[1:]}; add the RETCON bundle in that configuration source."
            )
    env_managed = ENV_OPTION in os.environ
    value = os.environ[ENV_OPTION] if env_managed else parser.get(SECTION, OPTION, fallback=None)
    if value is None:
        return [DEFAULT_BUNDLE.copy()], env_managed
    try:
        bundles = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"Existing {OPTION} is not valid JSON; no changes made.") from exc
    if not isinstance(bundles, list) or any(
        not isinstance(bundle, dict)
        or not isinstance(bundle.get("name"), str)
        or not isinstance(bundle.get("classpath"), str)
        or not isinstance(bundle.get("kwargs", {}), dict)
        for bundle in bundles
    ):
        raise ConfigurationError(f"Existing {OPTION} must be a list of named bundle objects; no changes made.")
    return bundles, env_managed


def _add_retcon_bundle(bundles: list[dict]) -> tuple[list[dict], bool]:
    if any(bundle["name"] == "retcon" and bundle["classpath"] != BUNDLE_CLASS for bundle in bundles):
        raise ConfigurationError("A different DAG bundle already uses the name 'retcon'; no changes made.")
    if any(bundle["classpath"] == BUNDLE_CLASS for bundle in bundles):
        return bundles, False
    return [*bundles, BUNDLE_CONFIG.copy()], True


def _replace_bundle_option(text: str, bundles: list[dict]) -> str:
    """Change one INI option, keeping unrelated values, comments and spacing."""
    lines = text.splitlines(keepends=True)
    newline = "\r\n" if "\r\n" in text else "\n"
    setting = f"{OPTION} = {json.dumps(bundles, separators=(',', ':'))}{newline}"
    section_start = None
    section_end = len(lines)
    for index, line in enumerate(lines):
        match = re.match(r"\s*\[([^\]]+)\]", line)
        if match:
            if section_start is not None:
                section_end = index
                break
            if match[1] == SECTION:
                section_start = index
    if section_start is None:
        prefix = text + (newline if text and not text.endswith(("\n", "\r")) else "")
        return prefix + f"{newline}[{SECTION}]{newline}" + setting

    for index in range(section_start + 1, section_end):
        match = re.match(rf"^(\s*){OPTION}\s*[:=]", lines[index], flags=re.IGNORECASE)
        if not match:
            continue
        indent = len(match[1])
        end = index + 1
        preserved = []
        while end < section_end:
            line = lines[end]
            if not line.strip() or line.lstrip().startswith(("#", ";")):
                preserved.append(line)
            elif len(line) - len(line.lstrip()) <= indent:
                break
            end += 1
        return "".join([*lines[:index], match[1] + setting, *preserved, *lines[end:]])

    prefix = "".join(lines[:section_end])
    if prefix and not prefix.endswith(("\n", "\r")):
        prefix += newline
    return prefix + setting + "".join(lines[section_end:])


def _write_configuration(path: Path, text: str) -> None:
    """Atomically replace the config while retaining existing file permissions."""
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as output:
            output.write(text)
        temporary.chmod(mode)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def configure(path: Path, *, print_only: bool = False) -> bool:
    """Register the bundle, returning whether the configuration file changed."""
    original, parser = _read_configuration(path)
    bundles, env_managed = _bundle_configuration(parser)
    bundles, changed = _add_retcon_bundle(bundles)
    if print_only:
        print(json.dumps(bundles, indent=2))
        return False
    if env_managed:
        if changed:
            raise ConfigurationError(
                f"{ENV_OPTION} overrides airflow.cfg. Run `retcon configure --print` and update that "
                "environment setting with the merged JSON; no file changes made."
            )
        print("RETCON's DAG bundle is already configured by the environment; no file changes made.")
        return False
    if changed:
        _write_configuration(path, _replace_bundle_option(original, bundles))
        print(f"Registered RETCON's packaged DAGs in {path}.")
    else:
        print(f"RETCON's DAG bundle is already configured in {path}.")
    print("Install the same RETCON package and bundle configuration on every Airflow component, then restart them.")
    return changed


def _initialize_airflow_configuration(path: Path) -> None:
    """Let Airflow generate its normal first-run config, including signing keys.

    Creating a minimal INI file ourselves would prevent Airflow from persisting
    its Fernet and JWT keys. Use the supported CLI in a fresh process so the
    requested config path is honored even if Airflow was previously imported.
    ``airflow version`` cannot do this: it deliberately skips initialization.
    """
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    environment = {**os.environ, "AIRFLOW_CONFIG": str(path)}
    try:
        result = subprocess.run(
            [sys.executable, "-m", "airflow", "config", "list"],
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=60,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ConfigurationError("Airflow configuration initialization timed out; no RETCON changes made.") from exc
    if result.returncode or not path.is_file():
        raise ConfigurationError(
            f"Airflow could not initialize {path}. Run `airflow config list` with AIRFLOW_CONFIG set to that "
            "path for diagnostics; no RETCON changes made."
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Configure the RETCON Airflow plugin.")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("configure", help="Register the packaged RETCON DAG bundle in Airflow.")
    command.add_argument("--airflow-config", type=Path, default=None, help="Path to airflow.cfg.")
    command.add_argument("--print", dest="print_only", action="store_true", help="Print merged bundle JSON only.")
    arguments = parser.parse_args(argv)
    try:
        path = (arguments.airflow_config or airflow_config_path()).expanduser()
        env_managed = any(ENV_OPTION + suffix in os.environ for suffix in ("", "_CMD", "_SECRET"))
        if not arguments.print_only and not path.exists() and not env_managed:
            _initialize_airflow_configuration(path)
        configure(path, print_only=arguments.print_only)
    except (ConfigurationError, OSError) as exc:
        print(f"retcon: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
