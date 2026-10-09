# PC8 Product Thinking Judge — UI Spec

Version 1.1 · 9 October 2026

This document is the complete UI specification for the PC8 Product Thinking AI
Judge web application. Implement exactly what is described here. Do not add
features, pages, or components not listed. Do not use a UI component library —
write plain HTML and CSS.

---

## 1. Design Tokens

### Colors
```
--ink:     #12162C   /* primary text */
--ink-2:   #5A5F7A   /* secondary text */
--ink-3:   #9499B5   /* muted text, labels */
--surface: #F7F8FA   /* page background */
--white:   #FFFFFF   /* card background */
--border:  #E2E5EF   /* dividers, card borders */
--accent:  #4055D4   /* rank numbers, criterion abbreviations, bar fills */
```

### Score badge colors (applied to 1–5 score badges)
```
Score 1: background #D93025, text #FFFFFF
Score 2: background #E8750A, text #FFFFFF
Score 3: background #C8A000, text #FFFFFF
Score 4: background #2E7D32, text #FFFFFF
Score 5: background #00695C, text #FFFFFF
```

### Score level labels
Used everywhere a score level name appears (distribution bars, anchor cells, etc.):
```
1 → Weak
2 → Limited
3 → Good
4 → Strong
5 → Excellent
```

### Typography
- Font stack: `-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif`
- Base size: 14px, line-height 1.5
- Use `font-variant-numeric: tabular-nums` on all score numbers and totals

### Spacing
- Card padding: 1.1rem 1.2rem
- Content area padding: 1.8rem 2rem
- Gap between major sections: 1.8rem

---

## 2. Shell Layout

The app uses a fixed left sidebar + scrollable main area on desktop, and a
fixed bottom tab bar on mobile.

```
Desktop (> 768px):
┌──────────────┬─────────────────────────────────────┐
│              │  Topbar (sticky, 52px)               │
│   Sidebar    ├─────────────────────────────────────┤
│   (220px     │                                      │
│    fixed)    │  Content area (scrollable)           │
│              │                                      │
└──────────────┴─────────────────────────────────────┘

Mobile (≤ 768px):
┌───────────────────────────────────────┐
│  Topbar (sticky, 52px, no meta text)  │
├───────────────────────────────────────┤
│                                       │
│  Content area (scrollable)            │
│  padding-bottom: 5rem (above nav)     │
│                                       │
├───────────────────────────────────────┤
│  Bottom tab bar (fixed, 56px)         │
└───────────────────────────────────────┘
```

### Sidebar (desktop only, hidden on mobile)
- Background: `--ink`
- Fixed, full height
- Three sections top to bottom: Brand, Nav, Footer

**Brand block** (top, border-bottom rgba(255,255,255,.08)):
- Eyebrow: "PC8 · AI BUILDER DAY" — 0.65rem, weight 700, color rgba(255,255,255,.35), letter-spacing .12em, uppercase
- Title: "Product Thinking Judge" — 0.95rem, weight 700, color #fff

**Nav block** (flex: 1):
- Four nav items (in order): Criteria, Results, Judge a deck, Text preview
- Each item: icon + label, padding .6rem 1.4rem, font .85rem weight 500
- Default state: color rgba(255,255,255,.5)
- Hover: color rgba(255,255,255,.85), background rgba(255,255,255,.04)
- Active: color #fff, background rgba(255,255,255,.07), left border 2px solid #7B93FF
- Icons: ◎ Criteria · ◈ Results · ⊕ Judge a deck · ≡ Text preview

**Footer block** (bottom, border-top rgba(255,255,255,.08)):
- Text: "Scoring via jev.ai" + "Rubric: Product Thinking v1"
- 0.72rem, color rgba(255,255,255,.25)

### Topbar
- Background: `--white`, border-bottom `--border`, height 52px, sticky
- Left: page title (0.9rem, weight 600)
- Right: contextual meta text (0.78rem, color `--ink-3`) — **hidden on mobile**

### Bottom tab bar (mobile only, hidden on desktop)
- Background: `--ink`, border-top rgba(255,255,255,.1), height 56px, fixed bottom
- Four tabs matching sidebar nav order: ◎ Criteria · ◈ Results · ⊕ Judge · ≡ Preview
- Each tab: icon (1.15rem) + label (0.62rem), flex column, centered
- Default: color rgba(255,255,255,.45)
- Active: color #fff

---

## 3. Page: Criteria (default landing page)

**Topbar:** "Criteria" | "PC8 Product Thinking rubric · 40 points total"

**Intro paragraph** (max-width 720px):
> The AI judge assesses **product thinking** demonstrated in a team's slide deck —
> not technical sophistication, implementation quality, or slide design.
> Each of the four criteria is scored **1–5** using a holistic best-fit rubric,
> contributing up to **10 points** each toward the competition's 40-point product thinking total.

### Criterion block (repeat × 4)

Each criterion block contains:

**Header row** (flex, align baseline):
- Abbreviation: bold, 1rem, color `--accent` (P&U / PU / O / T&L)
- Name: bold, 1rem (Problem & User / Problem Understanding / Outcomes / Test & Learn)
- "up to 10 pts" right-aligned, 0.78rem, color `--ink-3`

**Judging question** (italic, 0.82rem, color `--ink-2`):
- P&U: "How clearly and meaningfully does the submission establish who has the problem, what the problem is, and why it matters?"
- PU: "How well does the submission demonstrate that the team investigated and understood the problem rather than simply assuming its initial idea was correct?"
- O: "Does the team define success as a meaningful change for users or operations rather than merely producing an AI solution?"
- T&L: "Does the submission demonstrate genuine experimentation and learning rather than assuming the proposed idea will work?"

**Anchor grid** — 5 columns on desktop, 1 column on mobile (each cell shows badge + level inline). Each cell:
- Background tint matching score level:
  - Score 1: #fef2f2 · Score 2: #fff7ed · Score 3: #fefce8 · Score 4: #f0fdf4 · Score 5: #f0fdfa
- Border-radius 7px, padding .6rem .7rem
- Score badge (1.6rem × 1.6rem, border-radius 6px, font .75rem)
- Level label (0.7rem, weight 700, color `--ink-2`, margin-top .4rem)
- Description (0.7rem, color `--ink-3`, line-height 1.4)

**Anchor descriptions:**

| | Score 1 Weak | Score 2 Limited | Score 3 Good | Score 4 Strong | Score 5 Excellent |
|---|---|---|---|---|---|
| P&U | User and/or problem is absent or vague. May jump straight to a solution. | User and problem identifiable but framing is superficial or generic. | Clearly identifies user, problem, and why it matters. Sufficiently specific. | Specific, meaningful account of user's situation and consequences. Convincing context. | Compelling, specific problem. User, situation, impediment and consequences are exceptionally clear. |
| PU | Understanding mostly assumed. Little evidence of investigation before building. | Some attempt to understand the problem but insight remains superficial. | Meaningful investigation through relevant evidence or cause-and-effect reasoning. | Strong understanding through relevant evidence and exploration of underlying causes. | Strong, specific evidence producing convincing insight. One strong piece can be sufficient. |
| O | Success is producing an output. No indication of what improves for users. | Benefit implied but vague or too solution-centric to be meaningful. | Clearly describes improvement intended for users or operations beyond just shipping. | Specific, meaningful change defined with indication of how success could be recognised. | Meaningful outcome with an explicit measurable success measure. Team knows how to verify change. |
| T&L | Idea assumed to work. No testing, learning, or uncertainty demonstrated. | Assumptions or risks identified but little actual learning or connection to decisions. | Meaningful testing and what was learned is described. Some uncertainty acknowledged. | Tests important assumptions, extracts learning, clearly connects to decisions or next steps. | Clear test → learning → consequence loop. Learning actually changed the solution or next test. |

### Score conversion table

A single row of 6 cells (border 1px `--border`, border-radius 8px, overflow hidden):
- Cell 1: header — "Rubric score" (0.78rem)
- Cells 2–6: one per score level (1–5), showing badge + "X pts" below
  - 1 → 2 pts, 2 → 4 pts, 3 → 6 pts, 4 → 8 pts, 5 → 10 pts
  - Cell background matches score tint colors above
- Below table: "Each criterion contributes up to 10 points. Product Thinking total = (sum of four scores ÷ 20) × 40." (0.75rem, `--ink-3`)

---

## 4. Page: Results

**Topbar:** "Results" | "{N} submissions judged · Last run {date}"
(When results.json is empty: "Results" | "No submissions yet")

### Summary row

4 cards in a row (grid, equal columns, gap 1rem; 2×2 on mobile):
- Teams judged (count of entries in results.json)
- Highest score /40
- Average score /40 (rounded to nearest integer)
- Borderline flags (count of criteria across all teams where `borderline: true`)

Each card: white, border `--border`, border-radius 10px, padding 1.1rem 1.2rem.
Value: 1.7rem, weight 800. Label: 0.72rem, `--ink-3`, margin-top .35rem.

**Empty state** (when no results): single centered card with message:
"No results yet. Upload a deck using Judge a deck to get started."

### Leaderboard

**Desktop:** white card, border `--border`, border-radius 10px, overflow hidden.
`<table>` with `table-layout: fixed`, full width.

Column widths:
- # (rank): 2.5rem, center-aligned
- Team: 11rem
- Problem & User: 7.5rem, center-aligned
- Prob. Understanding: 7.5rem, center-aligned
- Outcomes: 7.5rem, center-aligned
- Test & Learn: 7.5rem, center-aligned
- Raw: 4.5rem, center-aligned
- Score /40: 8rem

Header row: background `--surface`, border-bottom `--border`, padding .6rem .75rem,
font .65rem weight 700, `--ink-3`, uppercase, letter-spacing .05em.

Data rows: sorted by weighted_score descending. Padding .75rem, border-bottom `--border`,
hover background #fafbff. Rows are **clickable** — clicking a row selects that team
for the Criterion breakdown section. Selected row highlighted #eef1ff.

Rank cell: weight 700, `--ink-3`. Top 2 ranks: color `--accent`.

Team cell:
- Team name: weight 600, 0.88rem
- Filename below: 0.72rem, `--ink-3`

Criterion cells: centered score badge. If `borderline: true`, show an orange dot
(5px circle, #E8750A) immediately to the right of the badge.

Raw cell: "{raw_total}/20", weight 700, `--ink-2`.

Score cell: flex row — bold number (1rem, weight 800) + progress bar (4px height,
`--accent` fill, `--border` background, border-radius 99px). Bar width = weighted_score / 40 × 100%.

**Mobile:** table is hidden. A card list (`.mobile-lb`) is shown instead — one card per team:
- Rank + team name + filename + score /40 in a header row
- 4 criterion badges in a 4-column grid below
- Tapping a card selects it (highlighted border `--accent`) and inserts a breakdown
  panel below it (`.mobile-breakdown`)

### Criterion breakdown

Section label "Criterion breakdown — {team name}" above a single full-width card.
Selecting any row/card in the leaderboard updates this section.
Default selection: top-ranked team.

Card: white, border `--border`, border-radius 10px, padding 1.1rem 1.2rem.

**Card header:** team name (weight 700, 0.9rem) + weighted score + raw score right-aligned.

**Criterion mini-grid:** 4 cells. Each cell: `--surface` background,
border-radius 6px, padding .5rem .6rem, text-align center.
- Criterion label (0.65rem, `--ink-3`)
- Score badge
- If borderline: "⚠ borderline" in #E8750A, 0.62rem
- If confidence present: "conf {N}%" in `--ink-3`, 0.72rem
- Distribution bars below (see §6)

**Desktop:** breakdown section is in a separate `#breakdown-section` div below the table.
**Mobile:** breakdown is hidden on desktop; instead a `.mobile-breakdown` div is
inserted after the selected `.mlb-card` in the card list.

---

## 5. Page: Judge a deck

**Topbar:** "Judge a deck" | "Upload a .pptx or .pdf to score it live"

Two-column layout (1fr 1fr, gap 1.5rem, align-items start). Single column on mobile.

### Left panel — Upload

White card, border `--border`, border-radius 10px, padding 1.5rem.

**Team name input:** text field above the upload zone, label "Team name", placeholder "e.g. Team Alpha".
Auto-filled from filename stem when a file is selected if the field is empty
or still matches the previous file's stem. Selecting a new file updates an
automatically filled name; a manually customized name is preserved.

**Upload zone:**
- Border: 2px dashed `--border`, border-radius 8px, padding 2.5rem 1.5rem, text-align center, cursor pointer
- Hover/dragover: border-color `--accent`, background #f6f7ff
- Icon: 📂 (2rem)
- Label: "Drop a .pptx or .pdf file here, or click to browse" (0.88rem, `--ink-2`)
- Hint: ".pptx and .pdf files only — slide/page and image text is extracted automatically" (0.75rem, `--ink-3`)
- On file selected: replace label with the filename in `--accent`

**Extract text button:** below upload zone, background `--ink`, white text, border-radius 7px,
padding .6rem 1.2rem, font .85rem weight 600. Disabled until file selected.
Shows "⏳ Extracting…" while waiting for extraction.

**What this scores section** (below button, separated by border-top):
- Section label "What this scores"
- Four rows, one per criterion: abbreviation (bold, `--accent`) + description in plain text (`--ink-2`, 0.82rem)

### Right panel — stateful

White card, border `--border`, border-radius 10px, padding 1.5rem.

**State 0 — empty** (before any file selected):
- Centered, `--ink-3`, icon ◈, text "Results will appear here once a deck is judged"

**State 1 — text extracted** (after extraction):
The card shows an editable text panel (`text-edit-panel`) that fills the card:
- **Header** (border-bottom `--border`): filename (weight 600, 0.82rem) + live char/word count (0.72rem, `--ink-3`, updates as user types)
- **Editable textarea** (monospace font, 0.75rem, `--ink-2`): pre-filled with extracted markdown, scrollable (max-height 55vh), no border/outline
- **Footer** (border-top `--border`): hint text "Check image text for OCR errors, edit if needed, then judge it." + **"Judge this text →" button** (background `--accent`, white text)

**State 2 — judging** (while waiting for jev.ai):
- Centered message: "Judging — this takes about 30 seconds…"

**State 3 — result** (after judge returns):

*Header* (flex, space-between, border-bottom `--border`, margin-bottom 1.2rem):
- Left: filename (weight 700, 0.9rem) + team name below (0.72rem, `--ink-3`)
- Right: weighted score as large number (1.6rem weight 800) + "/40" (0.85rem, `--ink-3`)

*Criteria list* (flex column, gap .7rem): one item per criterion:
- Score badge + label + anchor description ("3 — Good") in a flex row
- Each criterion with `borderline: true` shows an orange "⚠ borderline" label
  below its score level. Highlight every flagged criterion independently.
- Distribution bars below, indented under the text (padding-left 2.8rem)

*Footer* (border-top, flex space-between, 0.75rem, `--ink-3`):
- Left: "Raw: {raw_total}/20"
- Right: reviewer flags if any (borderline criteria) — color #E8750A, weight 600

*"◈ View leaderboard →" button* below footer — navigates to Results page.

---

## 6. Distribution bars component

Used in: Criterion breakdown (Results page) and Judge result panel.

Renders one row per score level (1–5), each row:
- Level label (full word: "Weak" / "Limited" / "Good" / "Strong" / "Excellent"), 0.65rem, `--ink-3`, fixed width 4.2rem
- Bar: flex:1, 4px height, `--accent` fill, `--border` background, border-radius 99px. Width = probability × 100%
- Percentage: 0.65rem, `--ink-3`, fixed width 2.2rem, right-aligned

---

## 7. Page: Text preview

**Topbar:** "Text preview" | "See how slide text is extracted before scoring"

Two-column layout (280px left, 1fr right, gap 1.5rem, align-items start). Single column on mobile.

### Left panel — Upload

White card (`.upload-card`), border `--border`, border-radius 10px, padding 1.5rem.

**Upload zone:** same style as Judge page upload zone.
- Hint: ".pptx and .pdf files only"
- On file selected: replace label with filename in `--accent`

**Extract text button:** below upload zone, same style as Judge page extract button.
Label: "Extract text". Shows "⏳ Extracting…" while waiting.

**What this shows section** (below button, separated by border-top):
- Section label "What this shows"
- Explanatory paragraph: "PPTX slide text and image OCR, or OCR of rendered PDF pages. Text is labeled by slide/image or PDF page number. OCR may misread words; check the text before scoring. On Judge a deck, you can edit this text before sending it to jev.ai."

### Right panel — text output

White card (`.text-card`), border `--border`, border-radius 10px, `display:flex`, `flex-direction:column`, `min-height:400px`.

**Empty state:** centered `--ink-3` text "Upload a .pptx or .pdf to see its extracted text"

**Populated state** (after extraction):
- **Header** (`.text-card-header`, border-bottom `--border`): filename (weight 600, 0.82rem) + char/word count (0.72rem, `--ink-3`)
- **Scrollable text** (`.text-output`): monospace font, 0.75rem, `--ink-2`, `white-space:pre-wrap`, `max-height:70vh`

---

## 8. Score badge component

Used everywhere scores appear.

```
width: 2rem, height: 2rem
border-radius: 6px
font-size: .85rem, weight 800
font-variant-numeric: tabular-nums
display: inline-flex, align-items: center, justify-content: center
```

On the Criteria page, badge size is 1.6rem × 1.6rem, font .75rem (same otherwise).

---

## 9. Navigation behaviour

- Clicking a nav item (sidebar or bottom tab bar) shows its page, hides the others
- Active nav item is highlighted in both sidebar and bottom tab bar simultaneously
- Default page on load: Criteria
- Navigating to Results always fetches fresh data from `/api/results`

---

## 10. Mobile breakpoint

At ≤ 768px:
- Sidebar hidden; bottom tab bar shown
- Topbar meta text hidden
- Content padding: 1rem horizontal, 5rem bottom (above tab bar)
- Summary grid: 2×2 instead of 1×4
- Anchor grid: 1 column (each cell is a flex row with badge + level + description)
- Judge layout: single column
- Leaderboard table hidden; mobile card list shown
- Desktop breakdown section hidden; mobile breakdown inserted below selected card
- Preview layout: single column
