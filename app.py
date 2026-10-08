"""PC8 Product Thinking AI Judge — Flask web app."""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request

from judge import CRITERIA_ORDER, extract_deck_content, score_deck

app = Flask(__name__)

RESULTS_PATH = Path("results.json")

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PC8 Product Thinking Judge</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --ink:#12162C;
  --ink-2:#5A5F7A;
  --ink-3:#9499B5;
  --surface:#F7F8FA;
  --white:#FFFFFF;
  --border:#E2E5EF;
  --accent:#4055D4;
}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;font-size:14px;line-height:1.5;background:var(--surface);color:var(--ink);display:flex;min-height:100vh}

/* Sidebar */
#sidebar{width:220px;min-width:220px;background:var(--ink);display:flex;flex-direction:column;position:fixed;top:0;left:0;height:100vh;z-index:100}
.sb-brand{padding:1.1rem 1.4rem;border-bottom:1px solid rgba(255,255,255,.08)}
.sb-eyebrow{font-size:.65rem;font-weight:700;color:rgba(255,255,255,.35);letter-spacing:.12em;text-transform:uppercase;margin-bottom:.25rem}
.sb-title{font-size:.95rem;font-weight:700;color:#fff}
.sb-nav{flex:1;padding:.6rem 0}
.sb-nav a{display:flex;align-items:center;gap:.6rem;padding:.6rem 1.4rem;font-size:.85rem;font-weight:500;color:rgba(255,255,255,.5);text-decoration:none;cursor:pointer;border-left:2px solid transparent}
.sb-nav a:hover{color:rgba(255,255,255,.85);background:rgba(255,255,255,.04)}
.sb-nav a.active{color:#fff;background:rgba(255,255,255,.07);border-left:2px solid #7B93FF}
.sb-footer{padding:.9rem 1.4rem;border-top:1px solid rgba(255,255,255,.08);font-size:.72rem;color:rgba(255,255,255,.25);line-height:1.6}

/* Main */
#main{margin-left:220px;flex:1;display:flex;flex-direction:column;min-height:100vh}
.topbar{height:52px;background:var(--white);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:0 2rem;position:sticky;top:0;z-index:50}
.topbar-title{font-size:.9rem;font-weight:600;color:var(--ink)}
.topbar-meta{font-size:.78rem;color:var(--ink-3)}
.content{padding:1.8rem 2rem;flex:1}

/* Pages */
.page{display:none}
.page.active{display:block}

/* Score badge */
.badge{display:inline-flex;align-items:center;justify-content:center;width:2rem;height:2rem;border-radius:6px;font-size:.85rem;font-weight:800;font-variant-numeric:tabular-nums;flex-shrink:0}
.badge-sm{width:1.6rem;height:1.6rem;font-size:.75rem}
.badge-1{background:#D93025;color:#fff}
.badge-2{background:#E8750A;color:#fff}
.badge-3{background:#C8A000;color:#fff}
.badge-4{background:#2E7D32;color:#fff}
.badge-5{background:#00695C;color:#fff}

/* Criteria page */
.intro{max-width:720px;margin-bottom:1.8rem;color:var(--ink-2);font-size:.9rem}
.criterion-block{margin-bottom:1.8rem}
.criterion-header{display:flex;align-items:baseline;gap:.5rem;margin-bottom:.35rem}
.criterion-abbrev{font-weight:700;font-size:1rem;color:var(--accent)}
.criterion-name{font-weight:700;font-size:1rem}
.criterion-pts{margin-left:auto;font-size:.78rem;color:var(--ink-3)}
.criterion-question{font-style:italic;font-size:.82rem;color:var(--ink-2);margin-bottom:.7rem}
.anchor-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:.4rem;margin-bottom:.7rem}
.anchor-cell{border-radius:7px;padding:.6rem .7rem}
.anchor-cell-1{background:#fef2f2}
.anchor-cell-2{background:#fff7ed}
.anchor-cell-3{background:#fefce8}
.anchor-cell-4{background:#f0fdf4}
.anchor-cell-5{background:#f0fdfa}
.anchor-level{font-size:.7rem;font-weight:700;color:var(--ink-2);margin-top:.4rem}
.anchor-desc{font-size:.7rem;color:var(--ink-3);line-height:1.4;margin-top:.2rem}

/* Score conversion table */
.conv-table{border:1px solid var(--border);border-radius:8px;overflow:hidden;display:flex;margin-bottom:.5rem}
.conv-cell{flex:1;padding:.6rem .75rem;text-align:center;border-right:1px solid var(--border)}
.conv-cell:last-child{border-right:none}
.conv-header{font-size:.78rem;color:var(--ink-2);font-weight:600;background:var(--surface)}
.conv-pts{font-size:.75rem;color:var(--ink-3);margin-top:.2rem}
.conv-note{font-size:.75rem;color:var(--ink-3)}

/* Results page */
.summary-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:1.8rem}
.summary-card{background:var(--white);border:1px solid var(--border);border-radius:10px;padding:1.1rem 1.2rem}
.summary-value{font-size:1.7rem;font-weight:800;font-variant-numeric:tabular-nums}
.summary-label{font-size:.72rem;color:var(--ink-3);margin-top:.35rem}

/* Leaderboard */
.leaderboard{background:var(--white);border:1px solid var(--border);border-radius:10px;overflow:hidden;margin-bottom:1.8rem}
.lb-table{width:100%;table-layout:fixed;border-collapse:collapse}
.lb-table th{background:var(--surface);border-bottom:1px solid var(--border);padding:.6rem .75rem;font-size:.65rem;font-weight:700;color:var(--ink-3);text-transform:uppercase;letter-spacing:.05em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.lb-table td{padding:.75rem .75rem;border-bottom:1px solid var(--border);vertical-align:middle}
.lb-table tr:last-child td{border-bottom:none}
.lb-table tr:hover td{background:#fafbff}
.col-rank{width:2.5rem;text-align:center}
.col-team{width:11rem}
.col-criterion{width:7.5rem;text-align:center}
.col-raw{width:4.5rem;text-align:center}
.col-score{width:8rem}
.rank-num{font-weight:700;color:var(--ink-3);font-variant-numeric:tabular-nums}
.rank-top{color:var(--accent)}
.team-name{font-weight:600;font-size:.88rem}
.team-file{font-size:.72rem;color:var(--ink-3)}
.criterion-cell{display:flex;align-items:center;justify-content:center;gap:3px}
.borderline-dot{width:5px;height:5px;border-radius:50%;background:#E8750A;flex-shrink:0}
.raw-score{font-weight:700;color:var(--ink-2);font-variant-numeric:tabular-nums}
.score-cell{display:flex;align-items:center;gap:.5rem}
.score-num{font-size:1rem;font-weight:800;font-variant-numeric:tabular-nums}
.score-bar-wrap{flex:1;height:4px;background:var(--border);border-radius:99px;overflow:hidden}
.score-bar{height:100%;background:var(--accent);border-radius:99px}

/* Criterion breakdown */
.breakdown-label{font-size:.78rem;font-weight:700;color:var(--ink-3);text-transform:uppercase;letter-spacing:.05em;margin-bottom:.75rem}
.breakdown-grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.8rem}
.breakdown-card{background:var(--white);border:1px solid var(--border);border-radius:10px;padding:1.1rem 1.2rem}
.breakdown-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:.8rem}
.breakdown-team{font-weight:700;font-size:.9rem}
.breakdown-wscore{font-size:1.1rem;font-weight:800;font-variant-numeric:tabular-nums}
.mini-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:.4rem}
.mini-cell{background:var(--surface);border-radius:6px;padding:.5rem .6rem;text-align:center}
.mini-label{font-size:.65rem;color:var(--ink-3);margin-bottom:.3rem}
.mini-borderline{font-size:.62rem;color:#E8750A;margin-top:.2rem}
.mini-conf{font-size:.72rem;color:var(--ink-3);margin-top:.1rem}
.dist-bars{margin-top:.5rem}
.dist-row{display:flex;align-items:center;gap:.3rem;margin-top:.2rem}
.dist-level{font-size:.65rem;color:var(--ink-3);width:4.2rem;flex-shrink:0}
.dist-bar-wrap{flex:1;height:4px;background:var(--border);border-radius:99px;overflow:hidden}
.dist-bar{height:100%;background:var(--accent);border-radius:99px}
.dist-pct{font-size:.65rem;color:var(--ink-3);width:2.2rem;text-align:right;flex-shrink:0}

/* Judge page */
.judge-layout{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;align-items:start}
.upload-card{background:var(--white);border:1px solid var(--border);border-radius:10px;padding:1.5rem}
.team-input-wrap{margin-bottom:.8rem}
.team-input-label{font-size:.75rem;font-weight:600;color:var(--ink-3);text-transform:uppercase;letter-spacing:.05em;display:block;margin-bottom:.35rem}
.team-input{width:100%;padding:.55rem .75rem;border:1px solid var(--border);border-radius:7px;font-size:.88rem;color:var(--ink);background:var(--white);outline:none}
.team-input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(64,85,212,.1)}
.team-input::placeholder{color:var(--ink-3)}
.upload-zone{border:2px dashed var(--border);border-radius:8px;padding:2.5rem 1.5rem;text-align:center;cursor:pointer;transition:border-color .15s,background .15s}
.upload-zone:hover,.upload-zone.dragover{border-color:var(--accent);background:#f6f7ff}
.upload-icon{font-size:2rem;margin-bottom:.6rem}
.upload-label{font-size:.88rem;color:var(--ink-2)}
.upload-hint{font-size:.75rem;color:var(--ink-3);margin-top:.3rem}
.upload-filename{font-size:.88rem;color:var(--accent);font-weight:600}
#file-input{display:none}
.judge-btn{display:block;width:100%;margin-top:1rem;padding:.6rem 1.2rem;background:var(--ink);color:#fff;border:none;border-radius:7px;font-size:.85rem;font-weight:600;cursor:pointer;text-align:center}
.judge-btn:disabled{opacity:.4;cursor:not-allowed}
.what-scores{border-top:1px solid var(--border);margin-top:1.2rem;padding-top:1rem}
.what-label{font-size:.72rem;font-weight:700;color:var(--ink-3);text-transform:uppercase;letter-spacing:.05em;margin-bottom:.6rem}
.what-row{display:flex;gap:.5rem;align-items:baseline;margin-bottom:.35rem;font-size:.82rem;color:var(--ink-2)}
.what-abbrev{font-weight:700;color:var(--accent);flex-shrink:0}

/* Result panel */
.result-card{background:var(--white);border:1px solid var(--border);border-radius:10px;padding:1.5rem}
.result-empty{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:200px;color:var(--ink-3);gap:.5rem;text-align:center}
.result-empty-icon{font-size:1.5rem}
.result-header{display:flex;align-items:flex-start;justify-content:space-between;border-bottom:1px solid var(--border);padding-bottom:1rem;margin-bottom:1.2rem}
.result-filename{font-weight:700;font-size:.9rem}
.result-team{font-size:.78rem;color:var(--ink-3);margin-top:.15rem}
.result-wscore{text-align:right}
.result-wscore-num{font-size:1.6rem;font-weight:800;font-variant-numeric:tabular-nums}
.result-wscore-denom{font-size:.85rem;color:var(--ink-3)}
.criteria-list{display:flex;flex-direction:column;gap:.7rem}
.crit-item{margin-bottom:.7rem}
.crit-row{display:flex;align-items:center;gap:.8rem}
.crit-text{flex:1}
.crit-name{font-size:.85rem;font-weight:600}
.crit-anchor{font-size:.72rem;color:var(--ink-3);margin-top:.1rem}
.crit-dist-full{padding-left:2.8rem;margin-top:.35rem}
.result-footer{border-top:1px solid var(--border);margin-top:1rem;padding-top:.75rem;display:flex;justify-content:space-between;align-items:center;font-size:.75rem;color:var(--ink-3)}
.result-flags{color:#E8750A;font-weight:600}
.see-results-btn{display:inline-block;margin-top:1rem;padding:.45rem .9rem;background:var(--accent);color:#fff;border:none;border-radius:6px;font-size:.82rem;font-weight:600;cursor:pointer}

/* Mobile leaderboard cards */
.mobile-lb{display:none}
.mlb-card{background:var(--white);border:1px solid var(--border);border-radius:10px;padding:.9rem 1rem;margin-bottom:.6rem;cursor:pointer}
.mlb-card.selected{border-color:var(--accent);background:#f4f6ff}
.mlb-header{display:flex;align-items:center;gap:.7rem;margin-bottom:.6rem}
.mlb-rank{font-size:.8rem;font-weight:700;color:var(--ink-3);width:1.6rem;flex-shrink:0}
.mlb-rank-top{color:var(--accent)}
.mlb-team{flex:1;min-width:0}
.mlb-name{font-weight:600;font-size:.9rem;display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mlb-file{font-size:.7rem;color:var(--ink-3);display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mlb-score{font-size:1.1rem;font-weight:800;font-variant-numeric:tabular-nums;flex-shrink:0}
.mlb-score-denom{font-size:.75rem;font-weight:400;color:var(--ink-3)}
.mlb-criteria{display:grid;grid-template-columns:repeat(4,1fr);gap:.4rem}
.mlb-crit{background:var(--surface);border-radius:6px;padding:.4rem .3rem;text-align:center}
.mlb-crit-label{display:block;font-size:.6rem;color:var(--ink-3);margin-bottom:.25rem}
.mlb-dot{width:5px;height:5px;border-radius:50%;background:#E8750A;display:inline-block;vertical-align:middle;margin-left:2px}

/* Mobile breakdown */
.mobile-breakdown{background:var(--white);border:1px solid var(--accent);border-radius:10px;padding:1rem;margin-bottom:1rem}
.mbd-header{font-weight:700;font-size:.88rem;margin-bottom:.7rem;color:var(--ink)}
.mbd-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:.5rem}
.mbd-cell .dist-level{width:auto;white-space:nowrap;padding-right:.4rem}
@media(max-width:768px){.mbd-grid{grid-template-columns:1fr}}
.mbd-cell{background:var(--surface);border-radius:6px;padding:.5rem .6rem;text-align:center}
.mbd-label{font-size:.65rem;color:var(--ink-3);margin-bottom:.25rem}
.mbd-conf{font-size:.65rem;color:var(--ink-3);margin-top:.2rem}
.mbd-bl{font-size:.62rem;color:#E8750A;margin-top:.15rem}

/* Mobile bottom nav */
.mobile-nav{display:none;position:fixed;bottom:0;left:0;right:0;height:56px;background:var(--ink);border-top:1px solid rgba(255,255,255,.1);z-index:200}
.mobile-nav a{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;color:rgba(255,255,255,.45);font-size:.62rem;font-weight:500;gap:.18rem;text-decoration:none;padding:.4rem 0}
.mobile-nav a.active{color:#fff}
.mobile-nav-icon{font-size:1.15rem;line-height:1}

@media(max-width:768px){
  #sidebar{display:none}
  #main{margin-left:0}
  .topbar{padding:0 1rem}
  .topbar-meta{display:none}
  .content{padding:1rem 1rem 5rem}
  .mobile-nav{display:flex}

  /* Grids */
  .summary-grid{grid-template-columns:1fr 1fr}
  .anchor-grid{grid-template-columns:1fr;gap:.5rem}
  .anchor-cell{display:flex;align-items:flex-start;gap:.6rem;padding:.5rem .7rem}
  .anchor-cell .anchor-level{margin-top:0;white-space:nowrap}
  .anchor-cell .anchor-desc{font-size:.72rem}
  .judge-layout{grid-template-columns:1fr}
  .breakdown-grid{grid-template-columns:1fr}
  .mini-grid{grid-template-columns:repeat(2,1fr)}

  /* Leaderboard: card list replaces table */
  .leaderboard{display:none}
  .mobile-lb{display:block}
  #breakdown-section{display:none}

  /* Conv table: allow wrapping */
  .conv-table{flex-wrap:wrap}
  .conv-cell{min-width:3rem}

  /* Criterion block spacing */
  .criterion-block{margin-bottom:1.2rem}
}
</style>
</head>
<body>

<nav id="sidebar">
  <div class="sb-brand">
    <div class="sb-eyebrow">PC8 · AI Builder Day</div>
    <div class="sb-title">Product Thinking Judge</div>
  </div>
  <div class="sb-nav">
    <a href="#" class="active" data-page="criteria">◎ Criteria</a>
    <a href="#" data-page="results">◈ Results</a>
    <a href="#" data-page="judge">⊕ Judge a deck</a>
  </div>
  <div class="sb-footer">
    Scoring via jev.ai<br>
    Rubric: Product Thinking v1
  </div>
</nav>

<div id="main">
  <div class="topbar">
    <span class="topbar-title" id="topbar-title">Criteria</span>
    <span class="topbar-meta" id="topbar-meta">PC8 Product Thinking rubric · 40 points total</span>
  </div>

  <!-- ========================== PAGE: CRITERIA ========================== -->
  <div class="content page active" id="page-criteria">
    <p class="intro">
      The AI judge assesses <strong>product thinking</strong> demonstrated in a team's slide deck —
      not technical sophistication, implementation quality, or slide design.
      Each of the four criteria is scored <strong>1–5</strong> using a holistic best-fit rubric,
      contributing up to <strong>10 points</strong> each toward the competition's 40-point product thinking total.
    </p>

    <!-- P&U -->
    <div class="criterion-block">
      <div class="criterion-header">
        <span class="criterion-abbrev">P&amp;U</span>
        <span class="criterion-name">Problem &amp; User</span>
        <span class="criterion-pts">up to 10 pts</span>
      </div>
      <p class="criterion-question">How clearly and meaningfully does the submission establish who has the problem, what the problem is, and why it matters?</p>
      <div class="anchor-grid">
        <div class="anchor-cell anchor-cell-1"><span class="badge badge-sm badge-1">1</span><div class="anchor-level">Weak</div><div class="anchor-desc">User and/or problem is absent or vague. May jump straight to a solution.</div></div>
        <div class="anchor-cell anchor-cell-2"><span class="badge badge-sm badge-2">2</span><div class="anchor-level">Limited</div><div class="anchor-desc">User and problem identifiable but framing is superficial or generic.</div></div>
        <div class="anchor-cell anchor-cell-3"><span class="badge badge-sm badge-3">3</span><div class="anchor-level">Good</div><div class="anchor-desc">Clearly identifies user, problem, and why it matters. Sufficiently specific.</div></div>
        <div class="anchor-cell anchor-cell-4"><span class="badge badge-sm badge-4">4</span><div class="anchor-level">Strong</div><div class="anchor-desc">Specific, meaningful account of user's situation and consequences. Convincing context.</div></div>
        <div class="anchor-cell anchor-cell-5"><span class="badge badge-sm badge-5">5</span><div class="anchor-level">Excellent</div><div class="anchor-desc">Compelling, specific problem. User, situation, impediment and consequences are exceptionally clear.</div></div>
      </div>
    </div>

    <!-- PU -->
    <div class="criterion-block">
      <div class="criterion-header">
        <span class="criterion-abbrev">PU</span>
        <span class="criterion-name">Problem Understanding</span>
        <span class="criterion-pts">up to 10 pts</span>
      </div>
      <p class="criterion-question">How well does the submission demonstrate that the team investigated and understood the problem rather than simply assuming its initial idea was correct?</p>
      <div class="anchor-grid">
        <div class="anchor-cell anchor-cell-1"><span class="badge badge-sm badge-1">1</span><div class="anchor-level">Weak</div><div class="anchor-desc">Understanding mostly assumed. Little evidence of investigation before building.</div></div>
        <div class="anchor-cell anchor-cell-2"><span class="badge badge-sm badge-2">2</span><div class="anchor-level">Limited</div><div class="anchor-desc">Some attempt to understand the problem but insight remains superficial.</div></div>
        <div class="anchor-cell anchor-cell-3"><span class="badge badge-sm badge-3">3</span><div class="anchor-level">Good</div><div class="anchor-desc">Meaningful investigation through relevant evidence or cause-and-effect reasoning.</div></div>
        <div class="anchor-cell anchor-cell-4"><span class="badge badge-sm badge-4">4</span><div class="anchor-level">Strong</div><div class="anchor-desc">Strong understanding through relevant evidence and exploration of underlying causes.</div></div>
        <div class="anchor-cell anchor-cell-5"><span class="badge badge-sm badge-5">5</span><div class="anchor-level">Excellent</div><div class="anchor-desc">Strong, specific evidence producing convincing insight. One strong piece can be sufficient.</div></div>
      </div>
    </div>

    <!-- O -->
    <div class="criterion-block">
      <div class="criterion-header">
        <span class="criterion-abbrev">O</span>
        <span class="criterion-name">Outcomes</span>
        <span class="criterion-pts">up to 10 pts</span>
      </div>
      <p class="criterion-question">Does the team define success as a meaningful change for users or operations rather than merely producing an AI solution?</p>
      <div class="anchor-grid">
        <div class="anchor-cell anchor-cell-1"><span class="badge badge-sm badge-1">1</span><div class="anchor-level">Weak</div><div class="anchor-desc">Success is producing an output. No indication of what improves for users.</div></div>
        <div class="anchor-cell anchor-cell-2"><span class="badge badge-sm badge-2">2</span><div class="anchor-level">Limited</div><div class="anchor-desc">Benefit implied but vague or too solution-centric to be meaningful.</div></div>
        <div class="anchor-cell anchor-cell-3"><span class="badge badge-sm badge-3">3</span><div class="anchor-level">Good</div><div class="anchor-desc">Clearly describes improvement intended for users or operations beyond just shipping.</div></div>
        <div class="anchor-cell anchor-cell-4"><span class="badge badge-sm badge-4">4</span><div class="anchor-level">Strong</div><div class="anchor-desc">Specific, meaningful change defined with indication of how success could be recognised.</div></div>
        <div class="anchor-cell anchor-cell-5"><span class="badge badge-sm badge-5">5</span><div class="anchor-level">Excellent</div><div class="anchor-desc">Meaningful outcome with an explicit measurable success measure. Team knows how to verify change.</div></div>
      </div>
    </div>

    <!-- T&L -->
    <div class="criterion-block">
      <div class="criterion-header">
        <span class="criterion-abbrev">T&amp;L</span>
        <span class="criterion-name">Test &amp; Learn</span>
        <span class="criterion-pts">up to 10 pts</span>
      </div>
      <p class="criterion-question">Does the submission demonstrate genuine experimentation and learning rather than assuming the proposed idea will work?</p>
      <div class="anchor-grid">
        <div class="anchor-cell anchor-cell-1"><span class="badge badge-sm badge-1">1</span><div class="anchor-level">Weak</div><div class="anchor-desc">Idea assumed to work. No testing, learning, or uncertainty demonstrated.</div></div>
        <div class="anchor-cell anchor-cell-2"><span class="badge badge-sm badge-2">2</span><div class="anchor-level">Limited</div><div class="anchor-desc">Assumptions or risks identified but little actual learning or connection to decisions.</div></div>
        <div class="anchor-cell anchor-cell-3"><span class="badge badge-sm badge-3">3</span><div class="anchor-level">Good</div><div class="anchor-desc">Meaningful testing and what was learned is described. Some uncertainty acknowledged.</div></div>
        <div class="anchor-cell anchor-cell-4"><span class="badge badge-sm badge-4">4</span><div class="anchor-level">Strong</div><div class="anchor-desc">Tests important assumptions, extracts learning, clearly connects to decisions or next steps.</div></div>
        <div class="anchor-cell anchor-cell-5"><span class="badge badge-sm badge-5">5</span><div class="anchor-level">Excellent</div><div class="anchor-desc">Clear test → learning → consequence loop. Learning actually changed the solution or next test.</div></div>
      </div>
    </div>

    <div class="conv-table">
      <div class="conv-cell conv-header" style="text-align:left">Rubric score</div>
      <div class="conv-cell anchor-cell-1"><span class="badge badge-sm badge-1">1</span><div class="conv-pts">2 pts</div></div>
      <div class="conv-cell anchor-cell-2"><span class="badge badge-sm badge-2">2</span><div class="conv-pts">4 pts</div></div>
      <div class="conv-cell anchor-cell-3"><span class="badge badge-sm badge-3">3</span><div class="conv-pts">6 pts</div></div>
      <div class="conv-cell anchor-cell-4"><span class="badge badge-sm badge-4">4</span><div class="conv-pts">8 pts</div></div>
      <div class="conv-cell anchor-cell-5"><span class="badge badge-sm badge-5">5</span><div class="conv-pts">10 pts</div></div>
    </div>
    <p class="conv-note">Each criterion contributes up to 10 points. Product Thinking total = (sum of four scores ÷ 20) × 40.</p>
  </div>

  <!-- ========================== PAGE: RESULTS ========================== -->
  <div class="content page" id="page-results">
    <div id="results-content"><div style="color:var(--ink-3);padding:2rem 0">Loading…</div></div>
  </div>

  <!-- ========================== PAGE: JUDGE ========================== -->
  <div class="content page" id="page-judge">
    <div class="judge-layout">
      <!-- Left: Upload -->
      <div class="upload-card">
        <div class="team-input-wrap">
          <label class="team-input-label" for="team-input">Team name</label>
          <input type="text" id="team-input" class="team-input" placeholder="e.g. Team Alpha">
        </div>
        <div class="upload-zone" id="upload-zone">
          <input type="file" id="file-input" accept=".pptx">
          <div class="upload-icon">📂</div>
          <div class="upload-label" id="upload-label">Drop a .pptx file here, or click to browse</div>
          <div class="upload-hint">.pptx files only — slide text is extracted automatically</div>
        </div>
        <button class="judge-btn" id="judge-btn" disabled>Judge deck</button>
        <div class="what-scores">
          <div class="what-label">What this scores</div>
          <div class="what-row"><span class="what-abbrev">P&amp;U</span> How clearly the submission establishes who has the problem, what it is, and why it matters.</div>
          <div class="what-row"><span class="what-abbrev">PU</span> How well the team demonstrates investigation and understanding of the problem.</div>
          <div class="what-row"><span class="what-abbrev">O</span> Whether success is defined as a meaningful change, not just shipping a solution.</div>
          <div class="what-row"><span class="what-abbrev">T&amp;L</span> Whether genuine experimentation and learning is demonstrated.</div>
        </div>
      </div>

      <!-- Right: Result -->
      <div class="result-card" id="result-panel">
        <div class="result-empty">
          <div class="result-empty-icon">◈</div>
          <div>Results will appear here once a deck is judged</div>
        </div>
      </div>
    </div>
  </div>
</div>

<nav class="mobile-nav" id="mobile-nav">
  <a href="#" data-page="criteria" class="active"><span class="mobile-nav-icon">◎</span>Criteria</a>
  <a href="#" data-page="results"><span class="mobile-nav-icon">◈</span>Results</a>
  <a href="#" data-page="judge"><span class="mobile-nav-icon">⊕</span>Judge</a>
</nav>

<script>
const CRITERIA_ORDER = ["problem_and_user","problem_understanding","outcomes","test_and_learn"];
const CRITERIA_LABELS = {
  problem_and_user: {label:"Problem & User", abbrev:"P&U"},
  problem_understanding: {label:"Problem Understanding", abbrev:"PU"},
  outcomes: {label:"Outcomes", abbrev:"O"},
  test_and_learn: {label:"Test & Learn", abbrev:"T&L"},
};
const SCORE_LABELS = {1:"Weak",2:"Limited",3:"Good",4:"Strong",5:"Excellent"};

// --- Navigation ---
const topbarTitle = document.getElementById('topbar-title');
const topbarMeta = document.getElementById('topbar-meta');

const TOPBAR = {
  criteria: {title:"Criteria", meta:"PC8 Product Thinking rubric · 40 points total"},
  results: {title:"Results", meta:""},
  judge: {title:"Judge a deck", meta:"Upload a .pptx to score it live"},
};

function navigate(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.sb-nav a, .mobile-nav a').forEach(a => a.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  document.querySelectorAll(`[data-page="${page}"]`).forEach(a => a.classList.add('active'));
  topbarTitle.textContent = TOPBAR[page].title;
  if (page === 'results') {
    renderResults();
  } else {
    topbarMeta.textContent = TOPBAR[page].meta;
  }
}

document.querySelectorAll('.sb-nav a, .mobile-nav a').forEach(a => {
  a.addEventListener('click', e => { e.preventDefault(); navigate(a.dataset.page); });
});

// --- Helpers ---
function badge(score, sm) {
  const cls = sm ? 'badge badge-sm' : 'badge';
  return `<span class="${cls} badge-${score}">${score}</span>`;
}

function distBars(distribution) {
  if (!distribution || !distribution.length) return '';
  return '<div class="dist-bars">' + distribution.map((p, i) =>
    `<div class="dist-row">
      <span class="dist-level">${SCORE_LABELS[i+1]}</span>
      <div class="dist-bar-wrap"><div class="dist-bar" style="width:${Math.round(p*100)}%"></div></div>
      <span class="dist-pct">${Math.round(p*100)}%</span>
    </div>`
  ).join('') + '</div>';
}

// --- Results page (always fetches fresh from API) ---
let _sortedResults = [];
let _selectedIdx = 0;

async function renderResults() {
  const container = document.getElementById('results-content');
  container.innerHTML = '<div style="color:var(--ink-3);padding:2rem 0">Loading…</div>';

  let results;
  try {
    const resp = await fetch('/api/results');
    results = await resp.json();
  } catch(e) {
    container.innerHTML = '<div style="color:#D93025;padding:2rem 0">Failed to load results.</div>';
    return;
  }

  if (!results.length) {
    topbarMeta.textContent = 'No submissions yet';
    container.innerHTML = `
      <div class="summary-grid">
        <div class="summary-card" style="grid-column:1/-1;text-align:center;padding:2rem">
          <div style="color:var(--ink-3)">No results yet. Upload a deck using <strong>Judge a deck</strong> to get started.</div>
        </div>
      </div>`;
    return;
  }

  _sortedResults = [...results].sort((a,b) => b.weighted_score - a.weighted_score);
  _selectedIdx = 0;

  const sorted = _sortedResults;
  const highest = Math.max(...results.map(r => r.weighted_score));
  const avg = Math.round(results.reduce((s,r) => s+r.weighted_score, 0) / results.length);
  const flags = results.reduce((s,r) => s + CRITERIA_ORDER.filter(k => r.criteria[k]?.borderline).length, 0);
  const lastDate = results.reduce((latest, r) => r.judged_at > latest ? r.judged_at : latest, results[0].judged_at);
  const lastDateFmt = new Date(lastDate).toLocaleDateString('en-GB', {day:'numeric',month:'short',year:'numeric'});

  topbarMeta.textContent = `${results.length} submission${results.length !== 1 ? 's' : ''} judged · Last run ${lastDateFmt}`;

  const summaryHtml = `
    <div class="summary-grid">
      <div class="summary-card"><div class="summary-value">${results.length}</div><div class="summary-label">Teams judged</div></div>
      <div class="summary-card"><div class="summary-value">${highest.toFixed(0)}<span style="font-size:1rem;font-weight:400;color:var(--ink-3)">/40</span></div><div class="summary-label">Highest score</div></div>
      <div class="summary-card"><div class="summary-value">${avg}<span style="font-size:1rem;font-weight:400;color:var(--ink-3)">/40</span></div><div class="summary-label">Average score</div></div>
      <div class="summary-card"><div class="summary-value">${flags}</div><div class="summary-label">Borderline flags</div></div>
    </div>`;

  const tableRows = sorted.map((r, i) => {
    const rank = i + 1;
    const rankCls = rank <= 2 ? 'rank-num rank-top' : 'rank-num';
    const critCells = CRITERIA_ORDER.map(k => {
      const c = r.criteria[k];
      const dot = c?.borderline ? '<span class="borderline-dot"></span>' : '';
      return `<td class="col-criterion"><div class="criterion-cell">${badge(c.score)}${dot}</div></td>`;
    }).join('');
    const barW = Math.round((r.weighted_score / 40) * 100);
    return `<tr data-idx="${i}" onclick="selectBreakdown(${i})" style="cursor:pointer">
      <td class="col-rank"><span class="${rankCls}">${rank}</span></td>
      <td class="col-team"><div class="team-name">${esc(r.team)}</div><div class="team-file">${esc(r.file)}</div></td>
      ${critCells}
      <td class="col-raw"><span class="raw-score">${r.raw_total}/20</span></td>
      <td class="col-score">
        <div class="score-cell">
          <span class="score-num">${r.weighted_score.toFixed(0)}</span>
          <div class="score-bar-wrap"><div class="score-bar" style="width:${barW}%"></div></div>
        </div>
      </td>
    </tr>`;
  }).join('');

  const tableHtml = `
    <div class="leaderboard">
      <table class="lb-table" id="lb-table">
        <thead><tr>
          <th class="col-rank">#</th>
          <th class="col-team">Team</th>
          <th class="col-criterion">Problem &amp; User</th>
          <th class="col-criterion">Prob. Understanding</th>
          <th class="col-criterion">Outcomes</th>
          <th class="col-criterion">Test &amp; Learn</th>
          <th class="col-raw">Raw</th>
          <th class="col-score">Score /40</th>
        </tr></thead>
        <tbody id="lb-body">${tableRows}</tbody>
      </table>
    </div>`;

  const mobileCards = sorted.map((r, i) => {
    const rank = i + 1;
    const rankCls = rank <= 2 ? 'mlb-rank mlb-rank-top' : 'mlb-rank';
    const crits = CRITERIA_ORDER.map(k => {
      const c = r.criteria[k];
      const dot = c?.borderline ? '<span class="mlb-dot"></span>' : '';
      return `<div class="mlb-crit">
        <span class="mlb-crit-label">${CRITERIA_LABELS[k].abbrev}</span>
        ${badge(c.score)}${dot}
      </div>`;
    }).join('');
    return `<div class="mlb-card" data-idx="${i}" onclick="selectBreakdown(${i})">
      <div class="mlb-header">
        <span class="${rankCls}">#${rank}</span>
        <div class="mlb-team">
          <span class="mlb-name">${esc(r.team)}</span>
          <span class="mlb-file">${esc(r.file)}</span>
        </div>
        <span class="mlb-score">${r.weighted_score.toFixed(0)}<span class="mlb-score-denom">/40</span></span>
      </div>
      <div class="mlb-criteria">${crits}</div>
    </div>`;
  }).join('');

  const mobileLbHtml = `<div class="mobile-lb" id="mobile-lb">${mobileCards}</div>`;

  container.innerHTML = summaryHtml + tableHtml + mobileLbHtml + '<div id="breakdown-section"></div>';
  renderBreakdown(0);
}

function breakdownCard(r) {
  const cells = CRITERIA_ORDER.map(k => {
    const c = r.criteria[k];
    const lbl = CRITERIA_LABELS[k].abbrev;
    const bl = c?.borderline ? '<div class="mini-borderline">⚠ borderline</div>' : '';
    const conf = c?.confidence != null ? `<div class="mini-conf">conf ${Math.round(c.confidence*100)}%</div>` : '';
    const dist = distBars(c?.distribution);
    return `<div class="mini-cell">
      <div class="mini-label">${lbl}</div>
      ${badge(c.score)}
      ${bl}${conf}${dist}
    </div>`;
  }).join('');
  return `<div class="breakdown-card" style="grid-column:1/-1">
    <div class="breakdown-header">
      <span class="breakdown-team">${esc(r.team)}</span>
      <span class="breakdown-wscore">${r.weighted_score.toFixed(0)}/40 · Raw ${r.raw_total}/20</span>
    </div>
    <div class="mini-grid">${cells}</div>
  </div>`;
}

function renderBreakdown(idx) {
  _selectedIdx = idx;
  const section = document.getElementById('breakdown-section');
  if (!section) return;
  const r = _sortedResults[idx];

  // Desktop breakdown
  section.innerHTML = `
    <div class="breakdown-label" style="margin-top:1.8rem">Criterion breakdown — ${esc(r.team)}</div>
    <div class="breakdown-grid" style="grid-template-columns:1fr">${breakdownCard(r)}</div>`;

  // Desktop row highlight
  document.querySelectorAll('#lb-body tr').forEach(row => {
    row.style.background = parseInt(row.dataset.idx) === idx ? '#eef1ff' : '';
  });

  // Mobile: highlight card and inject breakdown after it
  document.querySelectorAll('.mlb-card').forEach(card => {
    card.classList.toggle('selected', parseInt(card.dataset.idx) === idx);
  });
  const existingMbd = document.getElementById('mobile-breakdown');
  if (existingMbd) existingMbd.remove();
  const selectedCard = document.querySelector(`.mlb-card[data-idx="${idx}"]`);
  if (selectedCard) {
    const cells = CRITERIA_ORDER.map(k => {
      const c = r.criteria[k];
      const bl = c?.borderline ? `<div class="mbd-bl">⚠ borderline</div>` : '';
      const conf = c?.confidence != null ? `<div class="mbd-conf">conf ${Math.round(c.confidence*100)}%</div>` : '';
      return `<div class="mbd-cell">
        <div class="mbd-label">${CRITERIA_LABELS[k].label}</div>
        ${badge(c.score)}
        ${bl}${conf}
        ${distBars(c?.distribution)}
      </div>`;
    }).join('');
    const mbd = document.createElement('div');
    mbd.id = 'mobile-breakdown';
    mbd.className = 'mobile-breakdown';
    mbd.innerHTML = `<div class="mbd-header">${esc(r.team)} · ${r.weighted_score.toFixed(0)}/40 · Raw ${r.raw_total}/20</div><div class="mbd-grid">${cells}</div>`;
    selectedCard.after(mbd);
  }
}

function selectBreakdown(idx) {
  renderBreakdown(idx);
}

// --- Judge page ---
const fileInput = document.getElementById('file-input');
const uploadZone = document.getElementById('upload-zone');
const uploadLabel = document.getElementById('upload-label');
const judgeBtn = document.getElementById('judge-btn');
const teamInput = document.getElementById('team-input');
const resultPanel = document.getElementById('result-panel');

let selectedFile = null;

uploadZone.addEventListener('click', () => fileInput.click());
uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('dragover'); });
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
uploadZone.addEventListener('drop', e => {
  e.preventDefault();
  uploadZone.classList.remove('dragover');
  const f = e.dataTransfer.files[0];
  if (f && f.name.endsWith('.pptx')) setFile(f);
});

fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) setFile(fileInput.files[0]);
});

function setFile(f) {
  selectedFile = f;
  uploadLabel.innerHTML = `<span class="upload-filename">${esc(f.name)}</span>`;
  if (!teamInput.value.trim()) {
    teamInput.value = f.name.replace(/\.pptx$/i, '');
  }
  judgeBtn.disabled = false;
}

judgeBtn.addEventListener('click', async () => {
  if (!selectedFile) return;
  judgeBtn.disabled = true;
  judgeBtn.textContent = '⏳ Judging…';
  resultPanel.innerHTML = '<div class="result-empty"><div>Judging — this takes about 30 seconds…</div></div>';

  const form = new FormData();
  form.append('file', selectedFile);
  const team = teamInput.value.trim() || selectedFile.name.replace(/\.pptx$/i, '');
  form.append('team', team);

  try {
    const resp = await fetch('/api/judge', { method: 'POST', body: form });
    const data = await resp.json();
    if (data.error) throw new Error(data.error);
    renderJudgeResult(data);
  } catch (err) {
    resultPanel.innerHTML = `<div class="result-empty" style="color:#D93025">Error: ${esc(err.message)}</div>`;
  } finally {
    judgeBtn.disabled = false;
    judgeBtn.textContent = 'Judge deck';
  }
});

function renderJudgeResult(result) {
  const critRows = CRITERIA_ORDER.map(k => {
    const c = result.criteria[k];
    const info = CRITERIA_LABELS[k];
    const anchor = `${c.score} — ${SCORE_LABELS[c.score]}`;
    return `<div class="crit-item">
      <div class="crit-row">
        ${badge(c.score)}
        <div class="crit-text">
          <div class="crit-name">${esc(info.label)}</div>
          <div class="crit-anchor">${anchor}</div>
        </div>
      </div>
      <div class="crit-dist-full">${distBars(c.distribution)}</div>
    </div>`;
  }).join('');

  const borderlineKeys = CRITERIA_ORDER.filter(k => result.criteria[k]?.borderline);
  const flagsHtml = borderlineKeys.length
    ? `<span class="result-flags">⚠ Borderline: ${borderlineKeys.map(k => CRITERIA_LABELS[k].abbrev).join(', ')}</span>`
    : '<span></span>';

  resultPanel.innerHTML = `
    <div class="result-header">
      <div>
        <div class="result-filename">${esc(result.file)}</div>
        <div class="result-team">${esc(result.team)}</div>
      </div>
      <div class="result-wscore">
        <span class="result-wscore-num">${result.weighted_score.toFixed(0)}</span>
        <span class="result-wscore-denom">/40</span>
      </div>
    </div>
    <div class="criteria-list">${critRows}</div>
    <div class="result-footer">
      <span>Raw: ${result.raw_total}/20</span>
      ${flagsHtml}
    </div>
    <button class="see-results-btn" onclick="navigate('results')">◈ View leaderboard →</button>`;
}

function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

navigate('criteria');
</script>
</body>
</html>"""


def load_results():
    if not RESULTS_PATH.exists():
        return []
    with open(RESULTS_PATH) as f:
        return json.load(f)


def save_results(results):
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)


def upsert_result(results, new_result):
    updated = [r for r in results if r.get("file") != new_result.get("file")]
    updated.append(new_result)
    return updated


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/judge", methods=["POST"])
def api_judge():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    uploaded = request.files["file"]
    if not uploaded.filename.endswith(".pptx"):
        return jsonify({"error": "File must be a .pptx"}), 400

    team = request.form.get("team", "").strip() or Path(uploaded.filename).stem
    filename = uploaded.filename

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            uploaded.save(tmp_path)

        content = extract_deck_content(tmp_path)
        criteria = score_deck(content)

        raw_total = sum(criteria[k]["score"] for k in CRITERIA_ORDER)
        weighted_score = (raw_total / 20) * 40

        result = {
            "team": team,
            "file": filename,
            "judged_at": datetime.now(timezone.utc).isoformat(),
            "raw_total": raw_total,
            "weighted_score": weighted_score,
            "criteria": criteria,
        }

        results = load_results()
        results = upsert_result(results, result)
        save_results(results)

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()


@app.route("/api/results")
def api_results():
    return jsonify(load_results())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") != "production"
    app.run(host="0.0.0.0", port=port, debug=debug)
