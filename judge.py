"""PC8 Product Thinking AI Judge — CLI scoring script."""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from typesafe_sdk import Score, TypeSafeClient

CRITERIA = {
    "problem_and_user": {
        "key": "problem_and_user",
        "label": "PROBLEM & USER",
        "abbrev": "P&U",
        "instructions": (
            "How clearly and meaningfully does the submission establish who has the problem, "
            "what the problem is, and why it matters?\n\n"
            "Score only what the submission demonstrates. Do not infer undocumented work. "
            "Use only the submitted slide deck — no external knowledge. "
            "Accept factual claims at face value. "
            "Credit product thinking that is clearly demonstrated even if teams do not use "
            "explicit product-management vocabulary. "
            "Aggregate evidence from anywhere in the deck. "
            "Use holistic best-fit scoring — select the single anchor that best describes "
            "what is demonstrated. "
            "Do not penalise for slide aesthetics, writing polish, or presentation style. "
            "Direct user evidence is NOT required for a 5 — a submission that exceptionally "
            "clearly establishes the user, problem and consequences can score 5 even without "
            "direct user evidence."
        ),
        "criteria": [
            "1 — Weak: User and/or problem is absent, vague or difficult to understand. "
            "The submission may jump directly to an AI idea without establishing who needs it or why.",
            "2 — Limited: A user and problem can be identified, but the framing is superficial, "
            "generic or underspecified. Why the problem matters is weakly demonstrated.",
            "3 — Good: Clearly identifies the affected user(s), a plausible problem they face, "
            "and why the problem matters. The situation is sufficiently specific to understand "
            "what needs improvement.",
            "4 — Strong: Provides a specific and meaningful account of the user's situation, "
            "problem and consequences. The framing demonstrates strong appreciation of the user's "
            "context and makes the importance of solving the problem convincing.",
            "5 — Excellent: Presents a compelling, specific and meaningful problem. The user, "
            "their situation, what impedes them and the consequences are exceptionally clear, "
            "creating a convincing case that this is a problem worth solving.",
        ],
    },
    "problem_understanding": {
        "key": "problem_understanding",
        "label": "PROBLEM UNDERSTANDING",
        "abbrev": "PU",
        "instructions": (
            "How well does the submission demonstrate that the team investigated and understood "
            "the problem rather than simply assuming its initial idea was correct?\n\n"
            "Score only what the submission demonstrates. Do not infer undocumented work. "
            "Use only the submitted slide deck — no external knowledge. "
            "Accept factual claims at face value. "
            "Credit product thinking that is clearly demonstrated even if teams do not use "
            "explicit product-management vocabulary such as 'root cause', 'hypothesis', or 'discovery'. "
            "Do not mechanically require techniques such as Five Whys, personas, journey maps, "
            "or formal interviews. "
            "Excellent user evidence alone can support a 5 — do not require both excellent user "
            "evidence AND explicit root-cause analysis."
        ),
        "criteria": [
            "1 — Weak: Understanding is mostly assumed. Little or no evidence or reasoning "
            "demonstrates that the team investigated the problem before pursuing its solution.",
            "2 — Limited: Shows some attempt to understand the problem — for example users, "
            "observations, assumptions or possible causes — but the resulting insight remains "
            "superficial or weakly supported.",
            "3 — Good: Demonstrates meaningful investigation through relevant evidence and/or "
            "cause-and-effect reasoning. The resulting understanding provides a reasonable basis "
            "for the proposed solution.",
            "4 — Strong: Demonstrates strong understanding through relevant evidence, thoughtful "
            "exploration of the problem, assumptions and/or underlying causes. Conclusions are "
            "well supported by what the team presents.",
            "5 — Excellent: Demonstrates strong, specific evidence that produces convincing insight "
            "into the problem. A single strong and highly relevant piece of evidence can be sufficient. "
            "Explicit root-cause analysis is not mandatory if the user/problem evidence itself "
            "demonstrates excellent understanding.",
        ],
    },
    "outcomes": {
        "key": "outcomes",
        "label": "OUTCOMES",
        "abbrev": "O",
        "instructions": (
            "Does the team define success as a meaningful change for users or operations rather "
            "than merely producing an AI solution?\n\n"
            "Score only what the submission demonstrates. Do not infer undocumented work. "
            "Use only the submitted slide deck — no external knowledge. "
            "Accept factual claims at face value. "
            "A compelling outcome that is not explicitly measurable can score 4, but NOT 5. "
            "A score of 5 requires an explicit measurable outcome or success measure showing "
            "how the team would know whether the intended change occurred."
        ),
        "criteria": [
            "1 — Weak: Success is essentially the production of an output — for example building "
            "an AI application, agent, chatbot or feature. Little indication is given of what "
            "becomes better for the user or operation.",
            "2 — Limited: Implies some benefit or improvement, but it remains vague, "
            "solution-centric or insufficiently connected to a meaningful user/operational change.",
            "3 — Good: Clearly describes the improvement the solution is intended to create for "
            "users or operations. Success goes beyond simply having built the solution.",
            "4 — Strong: Defines a specific and meaningful change in user or operational performance "
            "and gives a strong indication of how success could be recognised or assessed.",
            "5 — Excellent: Defines a meaningful user or operational outcome AND an explicit "
            "measurable outcome or success measure showing how the team would know whether the "
            "intended change occurred.",
        ],
    },
    "test_and_learn": {
        "key": "test_and_learn",
        "label": "TEST & LEARN",
        "abbrev": "T&L",
        "instructions": (
            "Does the submission demonstrate genuine experimentation and learning rather than "
            "assuming the proposed idea will work?\n\n"
            "Score only what the submission demonstrates. Do not infer undocumented work. "
            "Use only the submitted slide deck — no external knowledge. "
            "Accept factual claims at face value. "
            "Merely performing tests is insufficient for a 5. "
            "A score of 5 requires evidence that learning actually influenced the solution, "
            "a decision, or the next test."
        ),
        "criteria": [
            "1 — Weak: Assumes the idea or solution will work. No meaningful testing, learning, "
            "uncertainty or next-step reasoning is demonstrated.",
            "2 — Limited: Identifies assumptions, risks, limitations or possible tests, but "
            "demonstrates little actual learning or connection between these and subsequent decisions.",
            "3 — Good: Shows meaningful testing and/or examination of important assumptions and "
            "describes what was learned. There is some indication of remaining uncertainty or what "
            "should happen next.",
            "4 — Strong: Tests important assumptions or aspects of the solution, extracts meaningful "
            "learning, and clearly connects that learning to changes, decisions, remaining uncertainty "
            "or appropriate next steps.",
            "5 — Excellent: Demonstrates a clear test → learning → consequence loop. Evidence from "
            "testing produced meaningful learning that actually informed the solution, a decision, "
            "or what the team would test next.",
        ],
    },
}

CRITERIA_ORDER = ["problem_and_user", "problem_understanding", "outcomes", "test_and_learn"]

SCORE_LABELS = {1: "Weak", 2: "Limited", 3: "Good", 4: "Strong", 5: "Excellent"}


def extract_deck_content(pptx_path: Path) -> str:
    result = subprocess.run(
        ["markitdown", str(pptx_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"markitdown failed: {result.stderr}")
    return result.stdout.strip()


def score_deck(content: str) -> dict:
    api_key = os.environ.get("TYPESAFE_API_KEY")
    if not api_key:
        raise RuntimeError("TYPESAFE_API_KEY environment variable not set")

    questions = {
        key: Score(
            instructions=CRITERIA[key]["instructions"],
            criteria=CRITERIA[key]["criteria"],
        )
        for key in CRITERIA_ORDER
    }

    with TypeSafeClient(api_key=api_key, base_url="https://jev-ai.pro/api", model="jev-latest") as client:
        response = client.system_one(state=content, questions=questions)

    result_criteria = {}
    for key in CRITERIA_ORDER:
        answer = response.answers[key]
        raw = answer.score
        integer_score = max(1, min(5, round(raw)))
        borderline = abs(raw - round(raw)) > 0.35
        probs = answer.probabilities
        distribution = [probs.get(k, probs.get(str(k), 0.0)) for k in sorted(probs.keys(), key=int)]
        confidence = answer.confidence

        result_criteria[key] = {
            "score": integer_score,
            "raw": raw,
            "distribution": distribution,
            "confidence": confidence,
            "borderline": borderline,
        }

    return result_criteria


def build_result(team: str, file: str, criteria: dict) -> dict:
    raw_total = sum(criteria[k]["score"] for k in CRITERIA_ORDER)
    weighted_score = (raw_total / 20) * 40
    return {
        "team": team,
        "file": file,
        "judged_at": datetime.now(timezone.utc).isoformat(),
        "raw_total": raw_total,
        "weighted_score": weighted_score,
        "criteria": criteria,
    }


def load_results() -> list:
    results_path = Path("results.json")
    if not results_path.exists():
        return []
    with open(results_path) as f:
        return json.load(f)


def save_results(results: list) -> None:
    with open("results.json", "w") as f:
        json.dump(results, f, indent=2)


def upsert_result(results: list, new_result: dict) -> list:
    updated = [r for r in results if r.get("file") != new_result["file"]]
    updated.append(new_result)
    return updated


def print_result(result: dict) -> None:
    print()
    print("=" * 64)
    print(f"PRODUCT THINKING ASSESSMENT — {result['team']}")
    print("=" * 64)
    print()
    for key in CRITERIA_ORDER:
        c = result["criteria"][key]
        label = CRITERIA[key]["label"]
        score = c["score"]
        score_label = SCORE_LABELS.get(score, "")
        borderline_flag = "  ⚠ borderline" if c.get("borderline") else ""
        print(f"{label}")
        print(f"  Score: {score}  ({score} - {score_label}){borderline_flag}")
        dist = c.get("distribution", [])
        if dist:
            dist_parts = "  ".join(f"L{i+1}:{round(p*100)}%" for i, p in enumerate(dist))
            print(f"  Distribution: {dist_parts}")
        if c.get("confidence") is not None:
            print(f"  Confidence: {round(c['confidence'] * 100)}%")
        print()
    print(f"Raw rubric score:           {result['raw_total']}/20")
    print(f"Weighted competition score: {result['weighted_score']:.0f}/40")
    print("=" * 64)


def judge_file(pptx_path: Path, team: str) -> dict:
    print(f"[JUDGING] {team} / {pptx_path.name}")
    print("  Extracting text...")
    content = extract_deck_content(pptx_path)
    print("  Sending to jev.ai...")
    criteria = score_deck(content)
    # TODO: LLM rationale step
    result = build_result(team, pptx_path.name, criteria)
    return result


def discover_pairs(root: Path) -> list[tuple[str, Path]]:
    pairs = []
    subdirs = [p for p in root.iterdir() if p.is_dir()]
    if subdirs:
        for subdir in subdirs:
            pptx_files = list(subdir.glob("*.pptx"))
            for pptx in pptx_files:
                pairs.append((subdir.name, pptx))
    else:
        for pptx in root.glob("*.pptx"):
            pairs.append((pptx.stem, pptx))
    return pairs


def main():
    if len(sys.argv) != 2:
        print("Usage: python judge.py <path-to-file.pptx>  or  python judge.py <path-to-folder>")
        sys.exit(1)

    target = Path(sys.argv[1])

    if target.is_file():
        if target.suffix.lower() != ".pptx":
            print(f"Error: {target} is not a .pptx file")
            sys.exit(1)
        results = load_results()
        result = judge_file(target, target.stem)
        print_result(result)
        results = upsert_result(results, result)
        save_results(results)
        print("  ✓ Saved to results.json")

    elif target.is_dir():
        pairs = discover_pairs(target)
        if not pairs:
            print(f"No .pptx files found in {target}")
            sys.exit(1)

        results = load_results()
        judged_files = {r.get("file") for r in results}

        count = 0
        for team, pptx_path in pairs:
            if pptx_path.name in judged_files:
                print(f"[SKIP] {team} / {pptx_path.name} (already judged)")
                continue
            try:
                result = judge_file(pptx_path, team)
                print_result(result)
                results = upsert_result(results, result)
                save_results(results)
                print("  ✓ Saved to results.json")
                count += 1
            except Exception as e:
                print(f"[ERROR] {team} / {pptx_path.name}: {e}")

        print(f"\n{len(results)} result(s) in results.json")

    else:
        print(f"Error: {target} is not a file or directory")
        sys.exit(1)


if __name__ == "__main__":
    main()
