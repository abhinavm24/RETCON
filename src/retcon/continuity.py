"""Narrow deterministic rules, separate from model suggestions.

Dialogue recognition is deliberately conservative and covers explicit attribution.
Imported manuscripts require author-reviewed character and scene metadata; these
checks are not a proof of every implicit fact in arbitrary prose.
"""
import re
from copy import deepcopy

SPEECH = r"(?:said|says|whispered|whispers|asked|asks|replied|replies|shouted|shouts|murmured|murmurs|called|calls|answered|answers|told|tells)"


def index_text(text, characters):
    present, speakers = [], []
    for character in characters:
        name, cid = character["name"], character["id"]
        escaped = re.escape(name)
        if re.search(rf"\b{escaped}\b", text, re.I):
            present.append(cid)
        if re.search(rf"\b{escaped}\s+{SPEECH}\b|\b{SPEECH}\s+{escaped}\b", text, re.I):
            speakers.append(cid)
    return {"characters": present, "speakers": speakers}


def proposed_story(story, character_id, death_chapter):
    proposed = deepcopy(story)
    character = next((c for c in proposed["characters"] if c["id"] == character_id), None)
    if not character:
        raise ValueError("Choose a character from this story.")
    if death_chapter not in [c["id"] for c in story["chapters"]]:
        raise ValueError("Choose an existing chapter for the canon change.")
    character.update(status="dead", death_chapter=death_chapter)
    return proposed


def check_story(story):
    issues = []
    locations = {}
    previous_time = None
    for chapter in story["chapters"]:
        for paragraph in chapter["paragraphs"]:
            def add(rule, message, chapter_id=chapter["id"], paragraph_id=paragraph["id"], quote=paragraph["text"]):
                issues.append(dict(chapter_id=chapter_id, paragraph_id=paragraph_id,
                                   rule=rule, message=message, quote=quote))
            indexed = index_text(paragraph["text"], story["characters"])
            # Do not let model-supplied metadata hide explicit dialogue in the prose.
            speakers = set(paragraph.get("speakers", [])) | set(indexed["speakers"])
            for character in story["characters"]:
                death = character.get("death_chapter")
                if death is not None and chapter["id"] > death and character["id"] in speakers:
                    add("dead_character_speaks", f'{character["name"]} speaks after dying at the end of chapter {death}.')
            stamp = paragraph.get("time")
            if stamp:
                if previous_time is not None and stamp < previous_time:
                    add("time_moves_backwards", f"Scene time {stamp} precedes {previous_time} in the linear timeline.")
                previous_time = stamp
            scene = paragraph.get("scene")
            location = paragraph.get("location")
            if scene and location:
                for cid in paragraph.get("characters", []):
                    key = (chapter["id"], scene, stamp, cid)
                    prior = locations.get(key)
                    if prior and prior != location:
                        add("two_locations_one_scene", f"{cid.title()} is recorded in both {prior} and {location} in one scene.")
                    locations[key] = location
    return issues


def preview(story, character_id, death_chapter, instruction=""):
    candidate = proposed_story(story, character_id, death_chapter)
    affected = [c["id"] for c in story["chapters"] if c["id"] > death_chapter and
                any(character_id in set(p.get("characters", [])) | set(index_text(p["text"], story["characters"])["characters"])
                    for p in c["paragraphs"])]
    issues = check_story(candidate)
    # Non-local scene violations are surfaced for human correction rather than blindly rewritten.
    broken = sorted({i["chapter_id"] for i in issues})
    return {"affected": affected, "unchanged": [c["id"] for c in story["chapters"] if c["id"] not in broken],
            "issues": issues, "metrics": {"checked": len(affected), "rewritten": len(broken),
                                            "untouched": len(story["chapters"]) - len(broken)}}
