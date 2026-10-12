"""Human review policy; AI scores remain immutable."""

from datetime import datetime, timezone

from judge import CRITERIA_ORDER, refresh_confidence_flags


class ReviewConflict(ValueError):
    pass


def summarize_result(result):
    refresh_confidence_flags([result])
    pending = []
    required = []
    complete = all(k in result.get("criteria", {}) for k in CRITERIA_ORDER)
    for key in CRITERIA_ORDER:
        c = result.get("criteria", {}).get(key)
        if c is None:
            continue
        human = c.get("human_review")
        c["effective_score"] = human["score"] if human else c["score"]
        c["review_status"] = human["status"] if human else "pending"
        if not human:
            complete = False
            if c["confidence_band"] in ("medium", "low", "unavailable"):
                pending.append(key)
            if c["confidence_band"] in ("low", "unavailable"):
                required.append(key)
    result["effective_raw_total"] = sum(c["effective_score"] for c in result.get("criteria", {}).values())
    result["effective_weighted_score"] = result["effective_raw_total"] * 2
    result["pending_review"] = pending
    result["required_review"] = required
    result["review_revision"] = result.get("review_revision", 0)
    result["submission_status"] = "finalized" if result.get("finalization") else "reviewed" if complete else "provisional"
    return result


def check_version(result, data):
    if data.get("judged_at") != result.get("judged_at") or type(data.get("revision")) is not int or data["revision"] != result.get("review_revision", 0):
        raise ReviewConflict("This submission changed. Refresh it before saving your review.")


def reviewer_name(data):
    name = data.get("reviewer")
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100:
        raise ValueError("Enter a reviewer name (up to 100 characters).")
    return name.strip()


def review_criterion(result, data):
    check_version(result, data)
    reviewer = reviewer_name(data)
    key = data.get("criterion")
    action = data.get("action")
    if key not in CRITERIA_ORDER or key not in result["criteria"]:
        raise ValueError("Unknown criterion")
    if action not in ("confirm", "override", "reset"):
        raise ValueError("Choose confirm, override, or reset")
    c = result["criteria"][key]
    score = c["score"] if action != "override" else data.get("score")
    if type(score) is not int or not 1 <= score <= 5:
        raise ValueError("Score must be an integer from 1 to 5")
    rationale = data.get("rationale", "")
    evidence = data.get("evidence_refs", "")
    if not isinstance(rationale, str) or not isinstance(evidence, str) or len(rationale) > 5000 or len(evidence) > 2000:
        raise ValueError("Review text is invalid or too long")
    if action == "override" and (not rationale.strip() or not evidence.strip()):
        raise ValueError("Overrides require a rationale and slide/page references")
    at = datetime.now(timezone.utc).isoformat()
    previous = c.get("human_review")
    human = {"score": score, "status": "overridden" if action == "override" else "confirmed",
             "reviewer": reviewer, "rationale": rationale.strip(), "evidence_refs": evidence.strip(), "reviewed_at": at}
    if action == "reset":
        c.pop("human_review", None)
        human = None
    else:
        c["human_review"] = human
    result.setdefault("review_history", []).append({"action": action, "criterion": key,
        "reviewer": reviewer, "at": at, "judged_at": result["judged_at"],
        "previous_review": previous, "review": human, "previous_finalization": result.get("finalization")})
    result.pop("finalization", None)
    result["review_revision"] = result.get("review_revision", 0) + 1
    return summarize_result(result)


def finalize_result(result, data):
    check_version(result, data)
    reviewer = reviewer_name(data)
    if any(key not in result.get("criteria", {}) for key in CRITERIA_ORDER):
        raise ValueError("This assessment is incomplete. Rejudge it before finalizing.")
    summarize_result(result)
    if result["required_review"]:
        raise ValueError("Review all Low or Unavailable confidence criteria before finalizing.")
    at = datetime.now(timezone.utc).isoformat()
    result["finalization"] = {"reviewer": reviewer, "at": at}
    result.setdefault("review_history", []).append({"action": "finalized", "reviewer": reviewer,
        "at": at, "judged_at": result["judged_at"], "score": result["effective_weighted_score"]})
    result["review_revision"] = result.get("review_revision", 0) + 1
    return summarize_result(result)
