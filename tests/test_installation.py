"""Installation must preserve an existing Airflow deployment's configuration."""

import configparser
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from retcon.cli import BUNDLE_CLASS, ConfigurationError, ENV_OPTION, airflow_config_path, configure, main


@pytest.fixture(autouse=True)
def isolated_configuration(monkeypatch):
    for variable in (ENV_OPTION, ENV_OPTION + "_CMD", ENV_OPTION + "_SECRET", "AIRFLOW_CONFIG", "AIRFLOW_HOME"):
        monkeypatch.delenv(variable, raising=False)


def configured_bundles(path):
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(path)
    return json.loads(parser.get("dag_processor", "dag_bundle_config_list"))


def test_initial_configuration_preserves_default_dags_and_is_idempotent(tmp_path):
    config = tmp_path / "airflow.cfg"
    assert configure(config)
    assert [bundle["name"] for bundle in configured_bundles(config)] == ["dags-folder", "retcon"]
    first = config.read_bytes()
    assert not configure(config)
    assert config.read_bytes() == first


def test_register_keeps_custom_bundles_settings_comments_and_permissions(tmp_path):
    config = tmp_path / "airflow.cfg"
    original = (
        "# deployment configuration\n[core]\nexecutor = LocalExecutor\n\n"
        "[dag_processor]\n# existing Git bundle\n"
        "dag_bundle_config_list = [\n"
        '    {"name": "team-dags", "classpath": "provider.GitBundle", "kwargs": {"git_conn_id": "git"}}\n'
        "    ]\n\n# keep this interval\nrefresh_interval = 43\n\n"
        "[api]\nbase_url = https://airflow.example.invalid\n"
    )
    config.write_text(original)
    config.chmod(0o640)
    assert configure(config)
    bundles = configured_bundles(config)
    assert bundles[0] == {
        "name": "team-dags", "classpath": "provider.GitBundle", "kwargs": {"git_conn_id": "git"}
    }
    assert bundles[1]["classpath"] == BUNDLE_CLASS
    assert config.stat().st_mode & 0o777 == 0o640
    changed = config.read_text()
    assert changed.startswith("# deployment configuration\n[core]\nexecutor = LocalExecutor\n\n")
    assert "# existing Git bundle\n" in changed
    assert changed.endswith(
        "\n# keep this interval\nrefresh_interval = 43\n\n[api]\nbase_url = https://airflow.example.invalid\n"
    )


def test_configured_empty_bundle_list_stays_empty_except_retcon(tmp_path):
    config = tmp_path / "airflow.cfg"
    config.write_text("[dag_processor]\ndag_bundle_config_list = []\n")
    configure(config)
    assert [bundle["name"] for bundle in configured_bundles(config)] == ["retcon"]


def test_configure_retains_windows_line_endings(tmp_path):
    config = tmp_path / "airflow.cfg"
    config.write_bytes(b"[core]\r\nexecutor = LocalExecutor\r\n[dag_processor]\r\nrefresh_interval = 43\r\n")
    configure(config)
    content = config.read_bytes()
    assert content.startswith(b"[core]\r\nexecutor = LocalExecutor\r\n")
    assert content.count(b"\n") == content.count(b"\r\n")


def test_existing_bundle_name_is_preserved(tmp_path):
    config = tmp_path / "airflow.cfg"
    original = '[dag_processor]\ndag_bundle_config_list = [{"name":"writing-room", "classpath":"' + BUNDLE_CLASS
    original += '", "kwargs":{"refresh_interval":61}}]\n'
    config.write_text(original)
    assert not configure(config)
    assert config.read_text() == original


@pytest.mark.parametrize("existing", ["not JSON", "{}", '[{"name": "broken"}]'])
def test_invalid_config_is_never_overwritten(tmp_path, existing):
    config = tmp_path / "airflow.cfg"
    config.write_text(f"[dag_processor]\ndag_bundle_config_list = {existing}\n")
    original = config.read_bytes()
    with pytest.raises(ConfigurationError):
        configure(config)
    assert config.read_bytes() == original


def test_bundle_name_collision_is_never_overwritten(tmp_path):
    config = tmp_path / "airflow.cfg"
    config.write_text('[dag_processor]\ndag_bundle_config_list = [{"name":"retcon", "classpath":"other.Bundle"}]\n')
    original = config.read_bytes()
    with pytest.raises(ConfigurationError, match="already uses"):
        configure(config)
    assert config.read_bytes() == original


def test_env_managed_config_requires_source_update_and_prints_merged_list(tmp_path, monkeypatch, capsys):
    config = tmp_path / "airflow.cfg"
    monkeypatch.setenv(ENV_OPTION, '[{"name":"production", "classpath":"other.Bundle", "kwargs":{}}]')
    with pytest.raises(ConfigurationError, match="overrides airflow.cfg"):
        configure(config)
    assert not config.exists()
    assert not configure(config, print_only=True)
    bundles = json.loads(capsys.readouterr().out)
    assert [bundle["name"] for bundle in bundles] == ["production", "retcon"]
    assert not config.exists()


def test_already_configured_environment_does_not_write_a_file(tmp_path, monkeypatch):
    monkeypatch.setenv(ENV_OPTION, json.dumps([{"name": "retcon", "classpath": BUNDLE_CLASS}]))
    config = tmp_path / "airflow.cfg"
    assert not configure(config)
    assert not config.exists()


@pytest.mark.parametrize("suffix", ["CMD", "SECRET"])
def test_external_config_sources_are_not_overwritten(tmp_path, monkeypatch, suffix):
    monkeypatch.setenv(ENV_OPTION + "_" + suffix, "managed-elsewhere")
    config = tmp_path / "airflow.cfg"
    with pytest.raises(ConfigurationError, match="managed through"):
        configure(config)
    assert not config.exists()


def test_cli_uses_airflow_config_and_returns_clear_errors(tmp_path, monkeypatch, capsys):
    config = tmp_path / "chosen.cfg"
    config.write_text("[core]\nexecutor = LocalExecutor\n")
    monkeypatch.setenv("AIRFLOW_CONFIG", str(config))
    assert airflow_config_path() == config
    assert main(["configure"]) == 0
    monkeypatch.setenv(ENV_OPTION, "invalid")
    assert main(["configure"]) == 1
    assert "not valid JSON" in capsys.readouterr().err


def test_cli_uses_airflow_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AIRFLOW_HOME", str(tmp_path))
    assert airflow_config_path() == tmp_path / "airflow.cfg"


def test_cli_bootstraps_missing_config_with_airflow_before_bundle_edit(tmp_path, monkeypatch):
    config = tmp_path / "first-run" / "airflow.cfg"
    calls = []

    def initialize(command, **kwargs):
        calls.append((command, kwargs))
        assert kwargs["env"]["AIRFLOW_CONFIG"] == str(config)
        config.write_text("[core]\nfernet_key = retained-fernet\n[api_auth]\njwt_secret = retained-jwt\n")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("retcon.cli.subprocess.run", initialize)
    assert main(["configure", "--airflow-config", str(config)]) == 0
    assert len(calls) == 1
    command, arguments = calls[0]
    assert command == [sys.executable, "-m", "airflow", "config", "list"]
    assert arguments["stdout"] == arguments["stderr"] == subprocess.DEVNULL
    assert "fernet_key = retained-fernet" in config.read_text()
    assert "jwt_secret = retained-jwt" in config.read_text()
    assert configured_bundles(config)[-1]["classpath"] == BUNDLE_CLASS
    assert main(["configure", "--airflow-config", str(config)]) == 0
    assert len(calls) == 1


def test_cli_print_does_not_bootstrap_or_create_any_config(tmp_path, monkeypatch, capsys):
    config = tmp_path / "unused" / "airflow.cfg"
    monkeypatch.setattr("retcon.cli.subprocess.run", lambda *a, **kw: pytest.fail("Must not initialize Airflow"))
    assert main(["configure", "--airflow-config", str(config), "--print"]) == 0
    assert json.loads(capsys.readouterr().out)[-1]["classpath"] == BUNDLE_CLASS
    assert not config.parent.exists()


def test_cli_existing_config_never_bootstraps_or_changes_keys(tmp_path, monkeypatch):
    config = tmp_path / "airflow.cfg"
    config.write_text("[core]\nfernet_key = original-fernet\n[api_auth]\njwt_secret = original-jwt\n")
    monkeypatch.setattr("retcon.cli.subprocess.run", lambda *a, **kw: pytest.fail("Must not initialize Airflow"))
    assert main(["configure", "--airflow-config", str(config)]) == 0
    assert config.read_text().startswith(
        "[core]\nfernet_key = original-fernet\n[api_auth]\njwt_secret = original-jwt\n"
    )


def test_cli_env_override_does_not_bootstrap_missing_file(tmp_path, monkeypatch):
    config = tmp_path / "airflow.cfg"
    monkeypatch.setenv(ENV_OPTION, "[]")
    monkeypatch.setattr("retcon.cli.subprocess.run", lambda *a, **kw: pytest.fail("Must not initialize Airflow"))
    assert main(["configure", "--airflow-config", str(config)]) == 1
    assert not config.exists()


def test_cli_bootstrap_failure_never_writes_minimal_config(tmp_path, monkeypatch, capsys):
    config = tmp_path / "airflow.cfg"
    monkeypatch.setattr("retcon.cli.subprocess.run", lambda *a, **kw: SimpleNamespace(returncode=1))
    assert main(["configure", "--airflow-config", str(config)]) == 1
    assert "could not initialize" in capsys.readouterr().err
    assert not config.exists()


def test_packaged_bundle_supplies_real_dags():
    pytest.importorskip("airflow")
    from retcon.bundle import RetconDagBundle

    bundle = RetconDagBundle(name="retcon")
    bundle.initialize()
    bundle.refresh()
    assert bundle.is_initialized
    assert not bundle.supports_versioning
    assert bundle.get_current_version() is None
    assert isinstance(bundle.path, Path)
    assert (bundle.path / "retcon.py").is_file()


def test_api_client_uses_airflow_server_configuration(monkeypatch):
    import sys
    from types import SimpleNamespace
    from retcon.airflow_client import AirflowClient

    config = SimpleNamespace(get=lambda *args, **kwargs: "https://airflow.example/platform/",
                             getint=lambda *args, **kwargs: 8081)
    monkeypatch.setitem(sys.modules, "airflow.configuration", SimpleNamespace(conf=config))
    assert AirflowClient().url == "https://airflow.example/platform"
    config.get = lambda *args, **kwargs: None
    assert AirflowClient().url == "http://127.0.0.1:8081"
