"""Continuity and publication safety tests, independent of Airflow or a live model."""

from copy import deepcopy

import pytest

from retcon import store, workflow
from retcon.continuity import check_story, index_text, preview, proposed_story
from retcon.seed import seed_story


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "STATE_DIR", tmp_path / "state")


def start_checked_run():
    run = workflow.start_retcon("mara", 2, "Mara dies at the end of chapter two.")
    payloads = workflow.check_run(run["id"])
    return run["id"], payloads


def prepare_review():
    run_id, payloads = start_checked_run()
    for payload in payloads:
        workflow.save_candidate(
            run_id,
            payload["chapter_id"],
            payload["paragraph_id"],
            payload["before"].replace("Mara", "Ivo"),
        )
    workflow.finish_candidates(run_id)
    return run_id


def paragraph_texts(story):
    return {p["id"]: p["text"] for c in story["chapters"] for p in c["paragraphs"]}


def test_seed_impact_checks_three_chapters_but_only_repairs_two():
    original = seed_story()
    impact = preview(original, "mara", 2)

    assert impact["affected"] == [3, 4, 5]
    assert impact["unchanged"] == [1, 2, 5]
    assert impact["metrics"] == {"checked": 3, "rewritten": 2, "untouched": 3}
    assert {(i["chapter_id"], i["paragraph_id"], i["rule"]) for i in impact["issues"]} == {
        (3, "3-2", "dead_character_speaks"),
        (4, "4-2", "dead_character_speaks"),
    }
    assert original == seed_story(), "A preview must never mutate published canon."
    assert check_story(original) == []


def test_a_memory_mentions_the_dead_character_without_becoming_a_violation():
    story = proposed_story(seed_story(), "mara", 2)
    memory = story["chapters"][4]["paragraphs"][0]
    assert "mara" in index_text(memory["text"], story["characters"])["characters"]
    assert "mara" not in index_text(memory["text"], story["characters"])["speakers"]
    assert all(i["chapter_id"] != 5 for i in check_story(story))


@pytest.mark.parametrize("text", ['“Open the door,” Mara whispered.', '“Open the door,” whispered Mara.'])
def test_dead_dialogue_is_detected_from_prose_even_when_metadata_is_stripped(text):
    story = proposed_story(seed_story(), "mara", 2)
    paragraph = story["chapters"][2]["paragraphs"][1]
    paragraph.update(text=text, speakers=[], characters=[])
    issues = [i for i in check_story(story) if i["paragraph_id"] == "3-2"]
    assert len(issues) == 1
    assert issues[0]["rule"] == "dead_character_speaks"
    assert issues[0]["quote"] == text
    assert 3 in preview(story, "mara", 2)["affected"]


def test_character_can_speak_before_or_in_the_chapter_where_they_die():
    story = proposed_story(seed_story(), "mara", 2)
    assert not any(i["chapter_id"] <= 2 for i in check_story(story))


def test_time_reversal_reports_the_offending_paragraph():
    story = seed_story()
    story["chapters"][2]["paragraphs"][0]["time"] = "21:23"
    issues = check_story(story)
    assert [(i["paragraph_id"], i["rule"]) for i in issues] == [("3-1", "time_moves_backwards")]


def test_character_cannot_occupy_two_locations_in_one_scene():
    story = seed_story()
    first, second = story["chapters"][0]["paragraphs"][:2]
    second.update(characters=["sera"], scene=first["scene"], time=first["time"], location="Airlock")
    issues = check_story(story)
    assert [(i["paragraph_id"], i["rule"]) for i in issues] == [("1-2", "two_locations_one_scene")]


def test_identical_scene_names_in_different_chapters_do_not_conflict():
    story = seed_story()
    story["chapters"] = story["chapters"][:2]
    for chapter in story["chapters"]:
        chapter["paragraphs"] = chapter["paragraphs"][:1]
        chapter["paragraphs"][0].update(characters=["sera"], time="21:00", scene="shared")
    assert check_story(story) == []


@pytest.mark.parametrize("character_id, death_chapter", [("missing", 2), ("mara", 99)])
def test_invalid_canon_change_does_not_create_a_run(character_id, death_chapter):
    before = store.load_state()
    with pytest.raises(ValueError):
        workflow.start_retcon(character_id, death_chapter, "")
    assert store.load_state() == before


def test_check_payloads_only_target_the_broken_paragraphs():
    original = store.load_state()["story"]
    run_id, payloads = start_checked_run()
    state = store.load_state()
    assert [(p["chapter_id"], p["paragraph_id"]) for p in payloads] == [(3, "3-2"), (4, "4-2")]
    assert state["run"]["id"] == run_id
    assert state["run"]["status"] == "rewriting"
    assert state["run"]["metrics"]["checked"] == 3
    assert all(p["living_characters"] == ["Sera", "Ivo"] for p in payloads)
    assert state["story"] == original


def test_approval_publishes_canon_and_repairs_atomically_preserving_all_other_text():
    original = store.load_state()["story"]
    run_id = prepare_review()
    staged = store.load_state()
    assert staged["story"] == original
    assert staged["run"]["status"] == "awaiting_approval"

    workflow.publish_run(run_id, True)
    state = store.load_state()
    published = state["story"]
    assert state["run"]["status"] == "published"
    assert published["version"] == original["version"] + 1
    mara = next(c for c in published["characters"] if c["id"] == "mara")
    assert mara["status"] == "dead"
    assert mara["death_chapter"] == 2
    assert check_story(published) == []
    assert state["run"]["metrics"] == {"checked": 3, "rewritten": 2, "untouched": 3}
    before_text, after_text = paragraph_texts(original), paragraph_texts(published)
    assert {pid for pid in before_text if before_text[pid] != after_text[pid]} == {"3-2", "4-2"}
    for pid in before_text.keys() - {"3-2", "4-2"}:
        assert after_text[pid].encode("utf-8") == before_text[pid].encode("utf-8")
    assert [c["version"] for c in published["chapters"]] == [1, 1, 2, 2, 1]


def test_reject_keeps_original_canon_and_manuscript():
    original = store.load_state()["story"]
    run_id = prepare_review()
    workflow.publish_run(run_id, False)
    state = store.load_state()
    assert state["story"] == original
    assert state["run"]["status"] == "rejected"
    assert len(state["run"]["patches"]) == 2


def test_publication_requires_reviewable_complete_repairs():
    run_id, payloads = start_checked_run()
    with pytest.raises(ValueError, match="not ready"):
        workflow.publish_run(run_id, True)
    with pytest.raises(ValueError, match="violations remain"):
        workflow.finish_candidates(run_id)
    first = payloads[0]
    workflow.save_candidate(run_id, first["chapter_id"], first["paragraph_id"], first["before"].replace("Mara", "Ivo"))
    with pytest.raises(ValueError, match="violations remain"):
        workflow.finish_candidates(run_id)
    assert store.load_state()["story"] == seed_story()


@pytest.mark.parametrize(
    "invalid_text",
    ["", "```text\nA replacement\n```", "<think>Let me think.</think>", "word " * 251,
     '“Open it,” Mara whispered.', "Mara silently turned the key."],
)
def test_invalid_model_output_never_changes_the_manuscript_or_staged_patches(invalid_text):
    run_id, payloads = start_checked_run()
    before = store.load_state()
    first = payloads[0]
    with pytest.raises(ValueError):
        workflow.save_candidate(run_id, first["chapter_id"], first["paragraph_id"], invalid_text)
    assert store.load_state() == before


def test_unchanged_broken_paragraph_is_rejected():
    run_id, payloads = start_checked_run()
    first = payloads[0]
    with pytest.raises(ValueError, match="unchanged"):
        workflow.save_candidate(run_id, first["chapter_id"], first["paragraph_id"], first["before"])


def test_a_model_cannot_rewrite_a_paragraph_that_passed_checks():
    run_id, _ = start_checked_run()
    clean_paragraph = seed_story()["chapters"][0]["paragraphs"][0]["text"]
    with pytest.raises(ValueError, match="passed continuity checks"):
        workflow.save_candidate(run_id, 1, "1-1", clean_paragraph.replace("honest", "truthful"))
    assert store.load_state()["run"]["patches"] == []


@pytest.mark.parametrize("failure", ["unclosed_smart_quote", "unclosed_ascii_quote", "mid_sentence", "too_short"])
def test_incomplete_model_replacements_are_rejected_before_staging(failure):
    run_id, payloads = start_checked_run()
    payload = payloads[0]
    valid_replacement = payload["before"].replace("Mara", "Ivo")
    bad_outputs = {
        "unclosed_smart_quote": (valid_replacement.replace("”", "", 1), "unclosed quotation"),
        "unclosed_ascii_quote": (valid_replacement.replace("“", '"', 1).replace("”", "", 1), "unclosed quotation"),
        "mid_sentence": (valid_replacement.removesuffix("."), "mid-sentence"),
        "too_short": ("Ivo found the key.", "too short"),
    }
    text, message = bad_outputs[failure]
    before = store.load_state()
    with pytest.raises(ValueError, match=message):
        workflow.save_candidate(run_id, payload["chapter_id"], payload["paragraph_id"], text)
    assert store.load_state() == before


@pytest.mark.parametrize("operation", ["review", "publish"])
def test_legacy_staged_truncated_text_cannot_reach_review_or_publication(operation):
    run_id = prepare_review()
    # Simulate a candidate created before completeness validation existed.
    with store.transaction() as state:
        patch = state["run"]["patches"][0]
        patch["after"] = patch["after"].removesuffix(".")
        if operation == "review":
            state["run"]["status"] = "rewriting"
    before = store.load_state()
    with pytest.raises(ValueError, match="mid-sentence"):
        if operation == "review":
            workflow.finish_candidates(run_id)
        else:
            workflow.publish_run(run_id, True)
    assert store.load_state() == before
    assert store.load_state()["story"] == seed_story()


def test_check_and_publish_reject_a_stale_manuscript_version():
    run = workflow.start_retcon("mara", 2, "")
    with store.transaction() as state:
        state["story"]["version"] += 1
    with pytest.raises(ValueError, match="changed"):
        workflow.check_run(run["id"])

    workflow.fail_run(run["id"], "Stale test run")
    workflow.reset_demo()
    run_id = prepare_review()
    with store.transaction() as state:
        state["story"]["version"] += 1
    before = store.load_state()
    with pytest.raises(ValueError, match="version has changed"):
        workflow.publish_run(run_id, True)
    assert store.load_state() == before


@pytest.mark.parametrize("stage", ["queued", "rewriting", "awaiting_approval"])
def test_active_revision_blocks_manuscript_edits_import_reset_and_another_revision(stage):
    if stage == "awaiting_approval":
        prepare_review()
    elif stage == "rewriting":
        start_checked_run()
    else:
        workflow.start_retcon("mara", 2, "")
    before = store.load_state()
    operations = [
        lambda: workflow.edit_chapter(1, "Sera said hello."),
        lambda: workflow.import_story("Other story", "Mara said hello."),
        workflow.reset_demo,
        lambda: workflow.start_retcon("mara", 1, ""),
    ]
    for operation in operations:
        with pytest.raises(ValueError, match="Finish or reject"):
            operation()
        assert store.load_state() == before


def test_retrying_candidate_review_and_publication_does_not_duplicate_patches_or_versions():
    run_id, payloads = start_checked_run()
    assert workflow.check_run(run_id) == payloads
    for payload in payloads:
        arguments = (run_id, payload["chapter_id"], payload["paragraph_id"], payload["before"].replace("Mara", "Ivo"))
        workflow.save_candidate(*arguments)
        workflow.save_candidate(*arguments)
    assert len(store.load_state()["run"]["patches"]) == 2
    workflow.finish_candidates(run_id)
    workflow.finish_candidates(run_id)
    workflow.publish_run(run_id, True)
    published = store.load_state()
    workflow.publish_run(run_id, True)
    assert store.load_state() == published


def test_rejection_is_idempotent_and_a_closed_revision_cannot_be_reopened():
    run_id = prepare_review()
    workflow.publish_run(run_id, False)
    rejected = store.load_state()
    workflow.publish_run(run_id, False)
    workflow.fail_run(run_id, "Late task failure")
    assert store.load_state() == rejected
    with pytest.raises(ValueError):
        workflow.publish_run(run_id, True)
    with pytest.raises(ValueError):
        workflow.check_run(run_id)


def test_old_run_ids_cannot_modify_a_new_revision():
    old_id = prepare_review()
    workflow.publish_run(old_id, False)
    new_run = workflow.start_retcon("mara", 2, "Try again")
    before = store.load_state()
    assert before["history"][0]["id"] == old_id
    assert new_run["id"] != old_id
    with pytest.raises(ValueError, match="no longer active"):
        workflow.check_run(old_id)
    with pytest.raises(ValueError, match="no longer active"):
        workflow.publish_run(old_id, True)
    assert store.load_state() == before


@pytest.mark.parametrize("status", ["queued", "rewriting"])
@pytest.mark.parametrize("next_action", ["edit", "reset"])
def test_cancelling_an_interrupted_persisted_revision_unlocks_the_manuscript(status, next_action):
    if status == "rewriting":
        run_id, _ = start_checked_run()
    else:
        run_id = workflow.start_retcon("mara", 2, "")["id"]
    persisted = store.load_state()
    assert persisted["run"]["status"] == status
    assert (store.STATE_DIR / "state.json").exists()

    cancelled = workflow.cancel_run(persisted["run"]["id"])
    assert cancelled["id"] == run_id
    assert cancelled["status"] == "cancelled"
    assert cancelled["completed_at"]
    assert store.load_state()["story"] == persisted["story"]
    if next_action == "edit":
        result = workflow.edit_chapter(1, "Sera said the work could continue.")
        assert result["story"]["chapters"][0]["paragraphs"][0]["text"] == "Sera said the work could continue."
    else:
        result = workflow.reset_demo()
        assert result["story"] == seed_story()
    assert result["run"] is None


def test_late_worker_results_cannot_change_a_cancelled_outcome():
    run_id, payloads = start_checked_run()
    payload = payloads[0]
    workflow.cancel_run(run_id)
    cancelled = store.load_state()
    operations = [
        lambda: workflow.save_candidate(
            run_id, payload["chapter_id"], payload["paragraph_id"], payload["before"].replace("Mara", "Ivo")
        ),
        lambda: workflow.finish_candidates(run_id),
        lambda: workflow.publish_run(run_id, True),
        lambda: workflow.publish_run(run_id, False),
        lambda: workflow.check_run(run_id),
    ]
    for operation in operations:
        with pytest.raises(ValueError):
            operation()
        assert store.load_state() == cancelled
    workflow.fail_run(run_id, "A late model request timed out")
    assert store.load_state() == cancelled


def test_stale_cancellation_cannot_cancel_a_newer_revision():
    old_id = workflow.start_retcon("mara", 2, "")["id"]
    workflow.cancel_run(old_id)
    new_id = workflow.start_retcon("mara", 2, "Try again")["id"]
    before = store.load_state()
    with pytest.raises(ValueError, match="no longer active"):
        workflow.cancel_run(old_id)
    assert store.load_state() == before
    assert store.load_state()["run"]["id"] == new_id
    assert store.load_state()["run"]["status"] == "queued"


def test_cancellation_cannot_undo_a_published_revision():
    run_id = prepare_review()
    workflow.publish_run(run_id, True)
    published = store.load_state()
    with pytest.raises(ValueError, match="already finished"):
        workflow.cancel_run(run_id)
    assert store.load_state() == published


def test_import_indexes_explicit_characters_and_export_preserves_their_prose():
    manuscript = '# Arrival\n\nNora said, “Welcome.”\n\nEli replied, “Thank you.”\n\n## Departure\n\nNora whispered, “Goodbye.”'
    state = workflow.import_story("A small story", manuscript)
    story = state["story"]
    assert story["title"] == "A small story"
    assert [c["title"] for c in story["chapters"]] == ["Arrival", "Departure"]
    assert {c["name"] for c in story["characters"]} == {"Nora", "Eli"}
    assert all(c["status"] == "unresolved" for c in story["characters"])
    assert story["chapters"][0]["paragraphs"][0]["speakers"] == ["nora"]
    assert all(p["time"] is None and p["location"] is None for c in story["chapters"] for p in c["paragraphs"])
    exported = workflow.export_markdown()
    assert exported.startswith("# A small story\n\n## 1. Arrival\n\n")
    assert all(text in exported for text in paragraph_texts(story).values())
    assert state["run"] is None
    assert state["history"] == []


def test_plain_text_import_and_edit_are_indexed_without_inventing_scene_metadata():
    workflow.import_story("", "Nora said hello.\n\nA door closed.")
    original = store.load_state()["story"]
    assert original["title"] == "Untitled manuscript"
    assert original["chapters"][0]["title"] == "Opening"
    updated = workflow.edit_chapter(1, 'Nora whispered, “Stay.”\n\nThe door remained open.', title="A change")
    story = updated["story"]
    chapter = story["chapters"][0]
    assert story["version"] == 2
    assert chapter["version"] == 2
    assert chapter["title"] == "A change"
    assert chapter["status"] == "edited"
    assert [p["id"] for p in chapter["paragraphs"]] == ["1-1", "1-2"]
    assert chapter["paragraphs"][0]["speakers"] == ["nora"]
    assert chapter["paragraphs"][1]["characters"] == []
    assert all(p["time"] is None and p["scene"] is None for p in chapter["paragraphs"])


def test_plain_chapter_number_headings_split_a_pasted_manuscript_without_markdown():
    first = 'Nora said, “Welcome.”'
    second = 'Nora whispered, “Goodbye.”'
    manuscript = f"Chapter 1: Arrival\n\n{first}\n\nCHAPTER 2 — Departure\n\n{second}"
    story = workflow.import_story("A pasted draft", manuscript)["story"]
    assert [c["title"] for c in story["chapters"]] == ["Chapter 1: Arrival", "CHAPTER 2 — Departure"]
    assert [p["text"] for c in story["chapters"] for p in c["paragraphs"]] == [first, second]
    assert all(p["speakers"] == ["nora"] for c in story["chapters"] for p in c["paragraphs"])


@pytest.mark.parametrize("text", ["", "  \n  ", "A door closed without a sound."])
def test_invalid_import_preserves_existing_story(text):
    original = store.load_state()
    with pytest.raises(ValueError):
        workflow.import_story("Invalid story", text)
    assert store.load_state() == original


def test_invalid_chapter_edit_preserves_existing_story():
    original = store.load_state()
    for chapter_id, text in [(99, "Sera said hello."), (1, " \n ")]:
        with pytest.raises(ValueError):
            workflow.edit_chapter(chapter_id, text)
        assert store.load_state() == original


def test_failed_transaction_rolls_back_all_changes():
    before = store.load_state()
    with pytest.raises(RuntimeError):
        with store.transaction() as state:
            state["story"]["title"] = "Must not be saved"
            raise RuntimeError("Aborted operation")
    assert store.load_state() == before


def test_returned_snapshot_cannot_mutate_saved_state():
    snapshot = store.load_state()
    expected = deepcopy(snapshot)
    snapshot["story"]["characters"].clear()
    assert store.load_state() == expected
