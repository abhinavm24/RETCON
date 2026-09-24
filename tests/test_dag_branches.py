"""Regression checks for Airflow's zero-length mapped task output contract."""

from importlib import import_module
from unittest.mock import Mock

import pytest

pytest.importorskip("airflow")


@pytest.fixture
def cascade():
    module = import_module("retcon.dags.retcon")
    return module, module.cascade_retcon()


def test_zero_mapped_repairs_produces_no_retry_payloads(cascade):
    _, dag = cascade
    select_rejected = dag.get_task("select_rejected_paragraphs").python_callable
    assert select_rejected(None) == []
    assert select_rejected([]) == []
    assert select_rejected([{"patch": {"after": "fixed"}, "retry": None}]) == []


def test_only_rejected_repairs_enter_second_attempt(cascade):
    _, dag = cascade
    select_rejected = dag.get_task("select_rejected_paragraphs").python_callable
    retry = {"paragraph_id": "chapter-3-p2", "validation_feedback": "Still mentions Mara"}
    assert select_rejected([{"patch": {}, "retry": None}, {"patch": None, "retry": retry}]) == [retry]


@pytest.mark.parametrize("staged,retried", [(None, None), ([{"patch": {}, "retry": None}], None)])
def test_approval_preparation_allows_empty_repair_or_retry_maps(cascade, monkeypatch, staged, retried):
    module, dag = cascade
    backend = Mock()
    monkeypatch.setattr(module, "_workflow", lambda: backend)
    prepare = dag.get_task("prepare_editor_review").python_callable
    message = prepare("revision-no-repairs", staged, retried)
    backend.finish_candidates.assert_called_once_with("revision-no-repairs")
    assert "revision-no-repairs" in message
    assert "Review the exact paragraph changes" in message
