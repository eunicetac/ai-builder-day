"""PC8 Product Thinking AI Judge — Flask web app."""

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request

from judge import CRITERIA_ORDER, SUPPORTED_EXTENSIONS, extract_deck_content, score_deck

from storage import load_results as read_results, store_result, update_result, delete_result
from judge import CRITERIA
from review import summarize_result, review_criterion, finalize_result, check_version, ReviewConflict

app = Flask(__name__)

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
.summary-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:1rem;margin-bottom:1.8rem}
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
.confidence-band{display:inline-block;font-size:.65rem;font-weight:600;border-radius:4px;padding:.15rem .35rem;margin-top:.3rem}
.confidence-high{color:#2E7D32;background:#f0fdf4}
.confidence-medium{color:#9A5800;background:#fff7ed}
.confidence-low{color:#D93025;background:#fef2f2}
.confidence-unavailable{color:var(--ink-2);background:var(--border)}
.confidence-dot{display:inline-block;width:6px;height:6px;border-radius:50%;flex-shrink:0}
.confidence-dot.confidence-high{background:#2E7D32}
.confidence-dot.confidence-medium{background:#E8750A}
.confidence-dot.confidence-low{background:#D93025}
.confidence-dot.confidence-unavailable{background:var(--ink-3)}
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

/* Text edit panel (inside result-card) */
.text-edit-panel{display:flex;flex-direction:column;margin:-1.5rem;height:calc(100% + 3rem);min-height:420px}
.text-edit-header{padding:.75rem 1rem;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;flex-shrink:0}
.text-edit-title{font-size:.82rem;font-weight:600}
.text-edit-meta{font-size:.72rem;color:var(--ink-3)}
.text-edit-area{flex:1;padding:1rem;font-family:'SF Mono',Menlo,Monaco,'Courier New',monospace;font-size:.75rem;line-height:1.6;color:var(--ink-2);border:none;outline:none;resize:none;background:transparent;min-height:300px;max-height:55vh;overflow-y:auto}
.text-edit-footer{padding:.75rem 1rem;border-top:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;flex-shrink:0;gap:.5rem}
.text-edit-hint{font-size:.72rem;color:var(--ink-3)}
.judge-text-btn{padding:.5rem 1.1rem;background:var(--accent);color:#fff;border:none;border-radius:7px;font-size:.82rem;font-weight:600;cursor:pointer;flex-shrink:0}
.judge-text-btn:disabled{opacity:.4;cursor:not-allowed}
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
.crit-borderline{color:#E8750A;font-size:.72rem;font-weight:600;margin-top:.2rem}
.crit-dist-full{padding-left:2.8rem;margin-top:.35rem}
.result-footer{border-top:1px solid var(--border);margin-top:1rem;padding-top:.75rem;display:flex;justify-content:space-between;align-items:center;font-size:.75rem;color:var(--ink-3)}
.result-flags{color:#E8750A;font-weight:600}
.see-results-btn{display:inline-block;margin-top:1rem;padding:.45rem .9rem;background:var(--accent);color:#fff;border:none;border-radius:6px;font-size:.82rem;font-weight:600;cursor:pointer}

/* Human review */
.review-toolbar{display:flex;flex-wrap:wrap;gap:1rem;align-items:center;margin-bottom:1rem;font-size:.8rem;color:var(--ink-2)}
.review-toolbar label{font-weight:600;display:flex;gap:.4rem;align-items:center}
.review-button{padding:.4rem .65rem;border:1px solid var(--border);background:var(--white);color:var(--accent);border-radius:6px;cursor:pointer;font-size:.75rem;margin-top:.4rem}
.review-button:disabled{opacity:.5;cursor:not-allowed}
.delete-button{color:#D93025}
.human-note{display:block;font-size:.65rem;color:var(--accent);margin-top:.2rem}
.review-status{font-size:.7rem;color:var(--ink-2);margin-top:.2rem}
.review-dialog{border:1px solid var(--border);border-radius:12px;padding:1.4rem;width:min(900px,95vw);max-height:90vh;margin:auto;color:var(--ink);background:var(--white)}
.review-dialog::backdrop{background:rgba(18,22,44,.45)}
.review-head{display:flex;justify-content:space-between;gap:1rem;align-items:center;margin-bottom:1rem}
.review-columns{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
.review-form label{display:block;font-size:.8rem;font-weight:600;margin-top:.8rem}
.review-form input,.review-form select,.review-form textarea{display:block;width:100%;padding:.5rem;border:1px solid var(--border);border-radius:6px;margin-top:.3rem;font:inherit}
.review-form textarea{min-height:85px}
.review-evidence{white-space:pre-wrap;max-height:45vh;overflow:auto;background:var(--surface);padding:.8rem;border-radius:6px;font-family:monospace;font-size:.75rem}
.review-anchors{font-size:.78rem;margin-top:1rem;line-height:1.5}
.review-anchors p{margin:.5rem 0}
.review-history{font-size:.78rem;margin-top:1rem;white-space:pre-wrap}
.review-error{color:#D93025;margin-top:.7rem;font-size:.82rem}
@media(max-width:768px){.review-columns{grid-template-columns:1fr}.review-dialog{padding:1rem}.review-evidence{max-height:30vh}}

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

/* Text preview page */
.preview-layout{display:grid;grid-template-columns:280px 1fr;gap:1.5rem;align-items:start}
.extract-btn{display:block;width:100%;margin-top:1rem;padding:.6rem 1.2rem;background:var(--ink);color:#fff;border:none;border-radius:7px;font-size:.85rem;font-weight:600;cursor:pointer}
.extract-btn:disabled{opacity:.4;cursor:not-allowed}
.text-card{background:var(--white);border:1px solid var(--border);border-radius:10px;display:flex;flex-direction:column;min-height:400px}
.text-card-header{padding:.75rem 1rem;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;flex-shrink:0}
.text-card-title{font-size:.82rem;font-weight:600}
.text-card-meta{font-size:.72rem;color:var(--ink-3)}
.text-output{flex:1;padding:1rem;font-family:'SF Mono',Menlo,Monaco,'Courier New',monospace;font-size:.75rem;line-height:1.6;color:var(--ink-2);white-space:pre-wrap;word-break:break-word;overflow-y:auto;max-height:70vh}
.text-empty{display:flex;align-items:center;justify-content:center;flex:1;color:var(--ink-3);font-size:.85rem;padding:2rem;text-align:center}
@media(max-width:768px){.preview-layout{grid-template-columns:1fr}}

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
    <a href="#" data-page="preview">≡ Text preview</a>
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
    <div class="review-toolbar"><label><input type="checkbox" id="needs-review" onchange="renderResults()"> Needs review only</label><span>Human reviews update competition scores; AI assessments are preserved.</span></div>
    <p id="results-feedback" role="status" aria-live="polite"></p>
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
          <input type="file" id="file-input" accept=".pptx,.pdf">
          <div class="upload-icon">📂</div>
          <div class="upload-label" id="upload-label">Drop a .pptx or .pdf file here, or click to browse</div>
          <div class="upload-hint">.pptx and .pdf files only — slide/page and image text is extracted automatically</div>
        </div>
        <button class="judge-btn" id="judge-btn" disabled>Extract text</button>
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

  <!-- ========================== PAGE: TEXT PREVIEW ========================== -->
  <div class="content page" id="page-preview">
    <div class="preview-layout">
      <!-- Left: Upload -->
      <div class="upload-card">
        <div class="upload-zone" id="preview-upload-zone">
          <input type="file" id="preview-file-input" accept=".pptx,.pdf">
          <div class="upload-icon">📂</div>
          <div class="upload-label" id="preview-upload-label">Drop a .pptx or .pdf file here, or click to browse</div>
          <div class="upload-hint">.pptx and .pdf files only</div>
        </div>
        <button class="extract-btn" id="extract-btn" disabled>Extract text</button>
        <div class="what-scores" style="margin-top:1rem;padding-top:1rem">
          <div class="what-label">What this shows</div>
          <p style="font-size:.82rem;color:var(--ink-2);line-height:1.5">
            PPTX slide text and image OCR, or OCR of rendered PDF pages. Text is labeled by slide/image or PDF page number.
            OCR may misread words; check the text before scoring. On Judge a deck, you can edit this text
            before sending it to jev.ai.
          </p>
        </div>
      </div>
      <!-- Right: Extracted text -->
      <div class="text-card" id="text-card">
        <div class="text-empty">Upload a .pptx or .pdf to see its extracted text</div>
      </div>
    </div>
  </div>
</div>

<nav class="mobile-nav" id="mobile-nav">
  <a href="#" data-page="criteria" class="active"><span class="mobile-nav-icon">◎</span>Criteria</a>
  <a href="#" data-page="results"><span class="mobile-nav-icon">◈</span>Results</a>
  <a href="#" data-page="judge"><span class="mobile-nav-icon">⊕</span>Judge</a>
  <a href="#" data-page="preview"><span class="mobile-nav-icon">≡</span>Preview</a>
</nav>

<dialog id="review-dialog" class="review-dialog" aria-labelledby="review-dialog-title">
  <div id="review-dialog-content"></div>
</dialog>

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
  judge: {title:"Judge a deck", meta:"Upload a .pptx or .pdf to score it live"},
  preview: {title:"Text preview", meta:"See how slide text is extracted before scoring"},
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
function confidenceIndicator(c) {
  const band = ['high','medium','low'].includes(c?.confidence_band) ? c.confidence_band : 'unavailable';
  const labels = {high:'High confidence',medium:'Medium confidence',low:'Low confidence',unavailable:'Confidence unavailable'};
  const guidance = {high:'Routine review',medium:'Review recommended',low:'Review required before finalizing',unavailable:'Confidence was not provided; review manually'};
  return `<span class="confidence-band confidence-${band}" title="${guidance[band]}">${labels[band]}</span>`;
}

function confidenceDot(c) {
  const band = ['high','medium','low'].includes(c?.confidence_band) ? c.confidence_band : 'unavailable';
  const labels = {high:'High confidence',medium:'Medium confidence',low:'Low confidence',unavailable:'Confidence unavailable'};
  return `<span class="confidence-dot confidence-${band}" role="img" aria-label="${labels[band]}" title="${labels[band]}"></span>`;
}

function criterionMetrics(c, className) {
  const probability = c?.distribution?.[c.score - 1];
  const scoreProbability = Number.isFinite(probability)
    ? `<div class="${className}">AI score ${c.score} probability: ${Math.round(probability*100)}%</div>`
    : '';
  const confidence = c?.confidence != null
    ? `<div class="${className}" title="Summarizes how concentrated the full score distribution is; it is not the probability of one score level.">Model confidence: ${Math.round(c.confidence*100)}%</div>`
    : '';
  return scoreProbability + confidence;
}

function resultScore(r) { return r.effective_weighted_score ?? r.weighted_score; }
function resultRaw(r) { return r.effective_raw_total ?? r.raw_total; }
function resultBadge(c) {
  const score = c.effective_score ?? c.score;
  const note = c.human_review ? `<span class="human-note">${c.human_review.status === 'overridden' ? `Human override (AI: ${c.score})` : 'Human confirmed'}</span>` : '';
  return `<span>${badge(score)}${note}</span>`;
}

let _sortedResults = [];
let _selectedIdx = 0;

async function renderResults() {
  const container = document.getElementById('results-content');
  container.innerHTML = '<div style="color:var(--ink-3);padding:2rem 0">Loading…</div>';

  let results;
  try {
    const resp = await fetch('/api/results');
    results = await resp.json();
    if (!resp.ok || !Array.isArray(results)) throw new Error('Invalid results response');
  } catch(e) {
    container.innerHTML = '<div style="color:#D93025;padding:2rem 0">Failed to load results.</div>';
    return;
  }

  if (!results.length) {
    _sortedResults = [];
    _selectedIdx = 0;
    topbarMeta.textContent = 'No submissions yet';
    container.innerHTML = `
      <div class="summary-grid">
        <div class="summary-card" style="grid-column:1/-1;text-align:center;padding:2rem">
          <div style="color:var(--ink-3)">No results yet. Upload a deck using <strong>Judge a deck</strong> to get started.</div>
        </div>
      </div>`;
    return;
  }

  const previousFile = _sortedResults[_selectedIdx]?.file;
  const ranked = [...results].sort((a,b) => resultScore(b) - resultScore(a));
  _sortedResults = document.getElementById('needs-review').checked ? ranked.filter(r => r.pending_review?.length) : ranked;
  _selectedIdx = Math.max(0, _sortedResults.findIndex(r => r.file === previousFile));

  const sorted = _sortedResults;
  const highest = Math.max(...results.map(r => resultScore(r)));
  const lastDate = results.reduce((latest, r) => r.judged_at > latest ? r.judged_at : latest, results[0].judged_at);
  const lastDateFmt = new Date(lastDate).toLocaleDateString('en-GB', {day:'numeric',month:'short',year:'numeric'});

  topbarMeta.textContent = `${results.length} submission${results.length !== 1 ? 's' : ''} judged · Last run ${lastDateFmt}`;

  const summaryHtml = `
    <div class="summary-grid">
      <div class="summary-card"><div class="summary-value">${results.length}</div><div class="summary-label">Teams judged</div></div>
      <div class="summary-card"><div class="summary-value">${highest.toFixed(0)}<span style="font-size:1rem;font-weight:400;color:var(--ink-3)">/40</span></div><div class="summary-label">Highest score</div></div>
    </div>`;

  const tableRows = sorted.map((r, i) => {
    const rank = ranked.indexOf(r) + 1;
    const rankCls = rank <= 2 ? 'rank-num rank-top' : 'rank-num';
    const critCells = CRITERIA_ORDER.map(k => {
      const c = r.criteria[k];
      const dot = confidenceDot(c);
      return `<td class="col-criterion"><div class="criterion-cell">${resultBadge(c)}${dot}</div></td>`;
    }).join('');
    const barW = Math.round((resultScore(r) / 40) * 100);
    return `<tr data-idx="${i}" onclick="selectBreakdown(${i})" style="cursor:pointer">
      <td class="col-rank"><span class="${rankCls}">${rank}</span></td>
      <td class="col-team"><div class="team-name">${esc(r.team)}</div><div class="team-file">${esc(r.file)}</div><div class="review-status">${esc(r.submission_status || 'provisional')}</div></td>
      ${critCells}
      <td class="col-raw"><span class="raw-score">${resultRaw(r)}/20</span></td>
      <td class="col-score">
        <div class="score-cell">
          <span class="score-num">${resultScore(r).toFixed(0)}</span>
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
    const rank = ranked.indexOf(r) + 1;
    const rankCls = rank <= 2 ? 'mlb-rank mlb-rank-top' : 'mlb-rank';
    const crits = CRITERIA_ORDER.map(k => {
      const c = r.criteria[k];
      const dot = confidenceDot(c);
      return `<div class="mlb-crit">
        <span class="mlb-crit-label">${CRITERIA_LABELS[k].abbrev}</span>
        ${resultBadge(c)}${dot}
      </div>`;
    }).join('');
    return `<div class="mlb-card" data-idx="${i}" onclick="selectBreakdown(${i})">
      <div class="mlb-header">
        <span class="${rankCls}">#${rank}</span>
        <div class="mlb-team">
          <span class="mlb-name">${esc(r.team)}</span>
          <span class="mlb-file">${esc(r.file)} · ${esc(r.submission_status || 'provisional')}</span>
        </div>
        <span class="mlb-score">${resultScore(r).toFixed(0)}<span class="mlb-score-denom">/40</span></span>
      </div>
      <div class="mlb-criteria">${crits}</div>
    </div>`;
  }).join('');

  const mobileLbHtml = `<div class="mobile-lb" id="mobile-lb">${mobileCards}</div>`;

  container.innerHTML = summaryHtml + tableHtml + mobileLbHtml + '<div id="breakdown-section"></div>';
  if (_sortedResults.length) renderBreakdown(_selectedIdx);
  else container.insertAdjacentHTML('beforeend', '<p>No submissions need review.</p>');
}

function breakdownCard(r) {
  const cells = CRITERIA_ORDER.map(k => {
    const c = r.criteria[k];
    const lbl = CRITERIA_LABELS[k].abbrev;
    const bl = confidenceIndicator(c);
    const conf = criterionMetrics(c, 'mini-conf');
    const dist = distBars(c?.distribution);
    return `<div class="mini-cell">
      <div class="mini-label">${lbl}</div>
      ${resultBadge(c)}
      ${bl}${conf}${dist}<button class="review-button" onclick="openReview(_selectedIdx, '${k}')">Review / override</button>
    </div>`;
  }).join('');
  return `<div class="breakdown-card" style="grid-column:1/-1">
    <div class="breakdown-header">
      <span class="breakdown-team">${esc(r.team)}</span>
      <span class="breakdown-wscore">${resultScore(r).toFixed(0)}/40 · Raw ${resultRaw(r)}/20</span>
    </div>
    <div class="review-status">${esc(r.submission_status || 'provisional')} · AI total ${r.weighted_score}/40</div><div class="mini-grid">${cells}</div><button class="review-button" onclick="openReview(_selectedIdx)">Review history / finalize</button>
    <button class="review-button delete-button" data-delete-result onclick="deleteSelectedResult(_selectedIdx)">Delete result</button>
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
      const bl = confidenceIndicator(c);
      const conf = criterionMetrics(c, 'mbd-conf');
      return `<div class="mbd-cell">
        <div class="mbd-label">${CRITERIA_LABELS[k].label}</div>
        ${resultBadge(c)}
        ${bl}${conf}
        ${distBars(c?.distribution)}<button class="review-button" onclick="openReview(_selectedIdx, '${k}')">Review / override</button>
      </div>`;
    }).join('');
    const mbd = document.createElement('div');
    mbd.id = 'mobile-breakdown';
    mbd.className = 'mobile-breakdown';
    mbd.innerHTML = `<div class="mbd-header">${esc(r.team)} · ${resultScore(r).toFixed(0)}/40 · Raw ${resultRaw(r)}/20</div><div class="review-status">${esc(r.submission_status || 'provisional')} · AI total ${r.weighted_score}/40</div><div class="mbd-grid">${cells}</div><button class="review-button" onclick="openReview(_selectedIdx)">Review history / finalize</button><button class="review-button delete-button" data-delete-result onclick="deleteSelectedResult(_selectedIdx)">Delete result</button>`;
    selectedCard.after(mbd);
  }
}

function selectBreakdown(idx) {
  renderBreakdown(idx);
}

let _deleteBusy = false;
async function deleteSelectedResult(idx) {
  if (_deleteBusy) return;
  const result = _sortedResults[idx];
  if (!result || !window.confirm(`Delete the result for ${result.team} (${result.file})?\n\nThis permanently removes its scores, saved text, and human review history. This cannot be undone.`)) return;
  _deleteBusy = true;
  const feedback = document.getElementById('results-feedback');
  feedback.textContent = 'Deleting result…';
  document.querySelectorAll('[data-delete-result]').forEach(b => b.disabled = true);
  try {
    const resp = await fetch('/api/results/delete', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({file:result.file, judged_at:result.judged_at, revision:result.review_revision ?? 0})});
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || 'Could not delete result');
    await renderResults();
    feedback.textContent = `Deleted the result for ${result.team}. You can upload the deck again with the correct team name.`;
  } catch (error) {
    feedback.textContent = error.message;
  } finally {
    _deleteBusy = false;
    document.querySelectorAll('[data-delete-result]').forEach(b => b.disabled = false);
  }
}

let _reviewData = null;
let _reviewKey = null;
let _reviewBusy = false;

async function openReview(idx, key, filename) {
  if (_reviewBusy) return;
  const dialog = document.getElementById('review-dialog');
  const content = document.getElementById('review-dialog-content');
  content.innerHTML = '<div class="review-head"><h2 id="review-dialog-title">Loading review…</h2><button class="review-button" onclick="closeReview()">Close</button></div>';
  if (!dialog.open) dialog.showModal();
  try {
    const resp = await fetch('/api/results/detail?file=' + encodeURIComponent(filename || _sortedResults[idx].file));
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || 'Could not load submission');
    _reviewData = data;
    _reviewKey = key || CRITERIA_ORDER[0];
    renderReviewDialog();
  } catch (error) {
    content.insertAdjacentHTML('beforeend', `<p class="review-error" role="alert">${esc(error.message)}</p>`);
  }
}

function closeReview() {
  if (!_reviewBusy) document.getElementById('review-dialog').close();
}

function renderReviewDialog() {
  const r = _reviewData.result;
  const c = r.criteria[_reviewKey];
  const human = c.human_review;
  const reviewer = document.getElementById('reviewer-name')?.value || sessionStorage.getItem('reviewer-name') || '';
  const history = (r.review_history || []).map(entry => {
    if (entry.action === 'rejudged') return `<p>${esc(entry.at)} · Rejudged; previous reviews archived. Previous AI total: ${entry.previous_result?.weighted_score ?? '?'} /40.</p>`;
    const review = entry.review;
    return `<p>${esc(entry.at)} · ${esc(entry.reviewer)} · ${esc(entry.action)} ${esc(CRITERIA_LABELS[entry.criterion]?.label || '')}${review ? ` · score ${review.score}` : ''}
      ${review?.rationale ? `<br>Rationale: ${esc(review.rationale)}` : ''}${review?.evidence_refs ? `<br>Evidence: ${esc(review.evidence_refs)}` : ''}</p>`;
  }).join('') || '<p>No human reviews yet.</p>';
  const required = (r.required_review || []).map(k => CRITERIA_LABELS[k].label).join(', ');
  document.getElementById('review-dialog-content').innerHTML = `
    <div class="review-head"><h2 id="review-dialog-title">Review — ${esc(r.team)}</h2><div><button class="review-button" onclick="openReview(0,_reviewKey,_reviewData.result.file)">Refresh assessment</button><button class="review-button" onclick="closeReview()">Close</button></div></div>
    <p>${esc(r.file)} · ${esc(r.submission_status)} · Current ${resultScore(r)}/40 · AI ${r.weighted_score}/40</p>
    <div class="review-columns">
      <div class="review-form">
        <label for="reviewer-name">Reviewer name</label><input id="reviewer-name" maxlength="100" value="${esc(reviewer)}" autocomplete="name">
        <label for="review-criterion">Criterion</label><select id="review-criterion" onchange="_reviewKey=this.value;renderReviewDialog()">${CRITERIA_ORDER.map(k => `<option value="${k}" ${k===_reviewKey?'selected':''}>${CRITERIA_LABELS[k].label}</option>`).join('')}</select>
        <p>AI: ${c.score} — ${SCORE_LABELS[c.score]} · Current: ${c.effective_score} · ${esc(c.review_status)}</p>
        ${confidenceIndicator(c)}${criterionMetrics(c, 'mini-conf')}${distBars(c.distribution)}
        ${human ? `<p>Reviewed by ${esc(human.reviewer)} at ${esc(human.reviewed_at)}</p>` : ''}
        <label for="review-score">Human score</label><select id="review-score">${[1,2,3,4,5].map(n=>`<option value="${n}" ${n===c.effective_score?'selected':''}>${n} — ${SCORE_LABELS[n]}</option>`).join('')}</select>
        <label for="review-rationale">Rationale (required for override)</label><textarea id="review-rationale" maxlength="5000">${esc(human?.rationale || '')}</textarea>
        <label for="review-evidence">Slide/page references (required for override)</label><input id="review-evidence" maxlength="2000" placeholder="e.g. Slides 2 and 4, or PDF page 3" value="${esc(human?.evidence_refs || '')}">
        <button class="review-button" data-review-save onclick="saveReview('confirm')">Confirm AI score</button>
        <button class="review-button" data-review-save onclick="saveReview('override')">Save override</button>
        ${human ? '<button class="review-button" data-review-save onclick="saveReview(\'reset\')">Reset to AI / pending</button>' : ''}
        <div class="review-anchors"><strong>Rubric anchors</strong>${_reviewData.anchors[_reviewKey].map(a=>`<p>${esc(a)}</p>`).join('')}</div>
      </div>
      <div><h3>Assessed slide/page text</h3><p class="mini-conf">This is the text used for this AI assessment, including any edits before judging.</p><pre class="review-evidence">${esc(r.assessed_text || 'This older assessment has no saved text. Consult the original deck, or rejudge to save its extraction.')}</pre></div>
    </div>
    <p>${required ? `Review required before finalizing: ${esc(required)}.` : 'Required reviews complete. Medium-confidence review remains recommended.'}</p>
    ${r.finalization ? `<p>Finalized by ${esc(r.finalization.reviewer)} at ${esc(r.finalization.at)}. Editing a review makes the submission provisional again.</p>` : ''}
    <button class="review-button" data-review-save onclick="saveReview('finalize')" ${required || r.finalization ? 'disabled' : ''}>Finalize submission</button>
    <div id="review-error" class="review-error" role="alert"></div>
    <details class="review-history"><summary>Review history (${(r.review_history || []).length})</summary>${history}</details>`;
}

async function saveReview(action) {
  if (_reviewBusy) return;
  const r = _reviewData.result;
  const reviewer = document.getElementById('reviewer-name').value.trim();
  const data = {file:r.file, judged_at:r.judged_at, revision:r.review_revision, reviewer,
    criterion:_reviewKey, action, score:Number(document.getElementById('review-score').value),
    rationale:document.getElementById('review-rationale').value, evidence_refs:document.getElementById('review-evidence').value};
  _reviewBusy = true;
  const buttons = [...document.querySelectorAll('[data-review-save]')].map(b => [b, b.disabled]);
  buttons.forEach(([b]) => b.disabled = true);
  const criterionSelect = document.getElementById('review-criterion');
  criterionSelect.disabled = true;
  const errorBox = document.getElementById('review-error');
  errorBox.textContent = '';
  try {
    const resp = await fetch(action === 'finalize' ? '/api/results/finalize' : '/api/results/review', {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
    const updated = await resp.json();
    if (!resp.ok) throw new Error(updated.error || 'Could not save review');
    sessionStorage.setItem('reviewer-name', reviewer);
    _reviewData.result = updated;
    renderReviewDialog();
    await renderResults();
  } catch (error) {
    document.getElementById('review-error').textContent = error.message;
  } finally {
    _reviewBusy = false;
    buttons.forEach(([b, disabled]) => { if (b.isConnected) b.disabled = disabled; });
    if (criterionSelect.isConnected) criterionSelect.disabled = false;
  }
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
  if (f && /\.(pptx|pdf)$/i.test(f.name)) setFile(f);
});

fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) setFile(fileInput.files[0]);
});

function setFile(f) {
  selectedFile = f;
  uploadLabel.innerHTML = `<span class="upload-filename">${esc(f.name)}</span>`;
  teamInput.value = f.name.replace(/\.(pptx|pdf)$/i, '');
  resultPanel.innerHTML = '<div class="result-empty"><div>Extract text from this deck to get started.</div></div>';
  judgeBtn.disabled = false;
  judgeBtn.textContent = 'Extract text';
}

// Step 1: Extract text from PPTX or PDF
judgeBtn.addEventListener('click', async () => {
  if (!selectedFile) return;
  const file = selectedFile;
  judgeBtn.disabled = true;
  judgeBtn.textContent = '⏳ Extracting…';
  resultPanel.innerHTML = '<div class="result-empty"><div>Extracting slide text…</div></div>';

  const form = new FormData();
  form.append('file', file);

  try {
    const resp = await fetch('/api/extract', { method: 'POST', body: form });
    const data = await resp.json();
    if (selectedFile !== file) return;
    if (data.error) throw new Error(data.error);
    renderTextEditor(data.text);
  } catch (err) {
    if (selectedFile !== file) return;
    resultPanel.innerHTML = `<div class="result-empty" style="color:#D93025">Error: ${esc(err.message)}</div>`;
    judgeBtn.disabled = false;
    judgeBtn.textContent = 'Extract text';
  }
});

function renderTextEditor(text) {
  judgeBtn.disabled = false;
  judgeBtn.textContent = 'Extract text';

  const charCount = text.length.toLocaleString();
  const wordCount = text.trim() ? text.trim().split(/\s+/).length.toLocaleString() : '0';

  resultPanel.innerHTML = `
    <div class="text-edit-panel">
      <div class="text-edit-header">
        <span class="text-edit-title">${esc(selectedFile.name)}</span>
        <span class="text-edit-meta" id="edit-meta">${charCount} chars · ${wordCount} words</span>
      </div>
      <textarea class="text-edit-area" id="edit-textarea" spellcheck="false">${esc(text)}</textarea>
      <div class="text-edit-footer">
        <span class="text-edit-hint">Check image text for OCR errors, edit if needed, then judge it.</span>
        <button class="judge-text-btn" id="judge-text-btn">Judge this text →</button>
      </div>
    </div>`;

  const textarea = document.getElementById('edit-textarea');
  const metaEl = document.getElementById('edit-meta');
  textarea.addEventListener('input', () => {
    const t = textarea.value;
    const c = t.length.toLocaleString();
    const w = t.trim() ? t.trim().split(/\s+/).length.toLocaleString() : '0';
    metaEl.textContent = `${c} chars · ${w} words`;
  });

  document.getElementById('judge-text-btn').addEventListener('click', () => judgeText(textarea.value));
}

// Step 2: Judge the (possibly edited) text
async function judgeText(text) {
  const file = selectedFile;
  judgeBtn.disabled = true;
  resultPanel.innerHTML = '<div class="result-empty" role="status"><div>Judging — this takes about 30 seconds…</div></div>';

  const team = teamInput.value.trim() || file.name.replace(/\.(pptx|pdf)$/i, '');
  const form = new FormData();
  form.append('text', text);
  form.append('team', team);
  form.append('filename', file.name);

  try {
    const resp = await fetch('/api/judge-text', { method: 'POST', body: form });
    const data = await resp.json();
    if (selectedFile !== file) return;
    if (data.error) throw new Error(data.error);
    renderJudgeResult(data);
  } catch (err) {
    if (selectedFile === file) resultPanel.innerHTML = `<div class="result-empty" style="color:#D93025">Error: ${esc(err.message)}</div>`;
  } finally {
    if (selectedFile === file) judgeBtn.disabled = false;
  }
}

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
          ${confidenceIndicator(c)}
          ${criterionMetrics(c, 'mini-conf')}
        </div>
      </div>
      <div class="crit-dist-full">${distBars(c.distribution)}</div>
    </div>`;
  }).join('');

  const borderlineKeys = CRITERIA_ORDER.filter(k => result.criteria[k]?.borderline);
  const flagsHtml = borderlineKeys.length
    ? `<span class="result-flags">⚠ Review recommended/required: ${borderlineKeys.map(k => CRITERIA_LABELS[k].abbrev).join(', ')}</span>`
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

// --- Text preview page ---
const previewUploadZone = document.getElementById('preview-upload-zone');
const previewFileInput = document.getElementById('preview-file-input');
const previewUploadLabel = document.getElementById('preview-upload-label');
const extractBtn = document.getElementById('extract-btn');
const textCard = document.getElementById('text-card');

let previewFile = null;

previewUploadZone.addEventListener('click', () => previewFileInput.click());
previewUploadZone.addEventListener('dragover', e => { e.preventDefault(); previewUploadZone.classList.add('dragover'); });
previewUploadZone.addEventListener('dragleave', () => previewUploadZone.classList.remove('dragover'));
previewUploadZone.addEventListener('drop', e => {
  e.preventDefault();
  previewUploadZone.classList.remove('dragover');
  const f = e.dataTransfer.files[0];
  if (f && /\.(pptx|pdf)$/i.test(f.name)) setPreviewFile(f);
});

previewFileInput.addEventListener('change', () => {
  if (previewFileInput.files[0]) setPreviewFile(previewFileInput.files[0]);
});

function setPreviewFile(f) {
  previewFile = f;
  previewUploadLabel.innerHTML = `<span class="upload-filename">${esc(f.name)}</span>`;
  extractBtn.disabled = false;
  textCard.innerHTML = '<div class="text-empty">Press "Extract text" to see the extracted content</div>';
}

extractBtn.addEventListener('click', async () => {
  if (!previewFile) return;
  extractBtn.disabled = true;
  extractBtn.textContent = '⏳ Extracting…';
  textCard.innerHTML = '<div class="text-empty">Extracting text…</div>';

  const form = new FormData();
  form.append('file', previewFile);

  try {
    const resp = await fetch('/api/extract', { method: 'POST', body: form });
    const data = await resp.json();
    if (data.error) throw new Error(data.error);
    const text = data.text || '';
    const charCount = text.length.toLocaleString();
    const wordCount = text.trim() ? text.trim().split(/\s+/).length.toLocaleString() : '0';
    textCard.innerHTML = `
      <div class="text-card-header">
        <span class="text-card-title">${esc(previewFile.name)}</span>
        <span class="text-card-meta">${charCount} chars · ${wordCount} words</span>
      </div>
      <div class="text-output">${esc(text)}</div>`;
  } catch (err) {
    textCard.innerHTML = `<div class="text-empty" style="color:#D93025">Error: ${esc(err.message)}</div>`;
  } finally {
    extractBtn.disabled = false;
    extractBtn.textContent = 'Extract text';
  }
});

function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

navigate('criteria');
</script>
</body>
</html>"""


def load_results():
    return [summarize_result(result) for result in read_results()]


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/judge", methods=["POST"])
def api_judge():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    uploaded = request.files["file"]
    if Path(uploaded.filename or "").suffix.lower() not in SUPPORTED_EXTENSIONS:
        return jsonify({"error": "File must be a .pptx or .pdf"}), 400

    team = request.form.get("team", "").strip() or Path(uploaded.filename).stem
    filename = uploaded.filename

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=Path(uploaded.filename).suffix.lower(), delete=False) as tmp:
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
            "assessed_text": content,
        }

        store_result(result)

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()


@app.route("/api/results")
def api_results():
    return jsonify([{k: v for k, v in r.items() if k not in ("assessed_text", "review_history")}
                    for r in load_results()])


@app.route("/api/results/detail")
def api_result_detail():
    result = next((r for r in load_results() if r.get("file") == request.args.get("file")), None)
    if result is None:
        return jsonify({"error": "Submission not found"}), 404
    return jsonify({"result": result, "anchors": {k: CRITERIA[k]["criteria"] for k in CRITERIA_ORDER}})


def apply_human_review(operation):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("file"), str):
        return jsonify({"error": "A JSON request with a submission filename is required"}), 400
    try:
        result = update_result(data["file"], lambda r: operation(r, data))
        return jsonify(result)
    except ReviewConflict as exc:
        return jsonify({"error": str(exc)}), 409
    except KeyError:
        return jsonify({"error": "Submission not found"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except OSError:
        return jsonify({"error": "Could not save the review. Please try again."}), 500


@app.route("/api/results/review", methods=["POST"])
def api_review():
    return apply_human_review(review_criterion)


@app.route("/api/results/finalize", methods=["POST"])
def api_finalize():
    return apply_human_review(finalize_result)


@app.route("/api/results/delete", methods=["POST"])
def api_delete_result():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("file"), str) or not data["file"]:
        return jsonify({"error": "A JSON request with a submission filename is required"}), 400
    try:
        delete_result(data["file"], lambda result: check_version(result, data))
        return jsonify({"deleted": data["file"]})
    except ReviewConflict:
        return jsonify({"error": "This result changed. Refresh Results before deleting it."}), 409
    except KeyError:
        return jsonify({"error": "Submission not found"}), 404
    except OSError:
        return jsonify({"error": "Could not delete the result. Please try again."}), 500


@app.route("/api/judge-text", methods=["POST"])
def api_judge_text():
    text = request.form.get("text", "")
    team = request.form.get("team", "").strip() or "Unknown"
    filename = request.form.get("filename", "unknown.pptx")

    if not text.strip():
        return jsonify({"error": "No text provided"}), 400

    try:
        criteria = score_deck(text)
        raw_total = sum(criteria[k]["score"] for k in CRITERIA_ORDER)
        weighted_score = (raw_total / 20) * 40
        result = {
            "team": team,
            "file": filename,
            "judged_at": datetime.now(timezone.utc).isoformat(),
            "raw_total": raw_total,
            "weighted_score": weighted_score,
            "criteria": criteria,
            "assessed_text": text,
        }
        store_result(result)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/extract", methods=["POST"])
def api_extract():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    uploaded = request.files["file"]
    if Path(uploaded.filename or "").suffix.lower() not in SUPPORTED_EXTENSIONS:
        return jsonify({"error": "File must be a .pptx or .pdf"}), 400

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=Path(uploaded.filename).suffix.lower(), delete=False) as tmp:
            tmp_path = Path(tmp.name)
            uploaded.save(tmp_path)

        text = extract_deck_content(tmp_path)
        return jsonify({"text": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") != "production"
    app.run(host="0.0.0.0", port=port, debug=debug)
