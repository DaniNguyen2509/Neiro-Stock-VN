---
name: multi-layer-dashboard-audit
description: Audits financial dashboards, charts, and data tables across 3 independent layers (Presentation, Data Pipeline, Column-by-Column Domain Logic). Use when reviewing, building, or debugging dashboards, tables, or metric views. Prevents tunnel vision, surface-level fixes, and enforces column-by-column domain logic verification.
---

# Multi-Layer Dashboard & UI Audit

## Overview

A financial dashboard is not just an HTML page or visual component—it is a critical decision-making cockpit for investors and algorithmic systems. A single misleading column, an inverted sign, or a false badge (such as marking a returning stock as "🆕 MỚI") can trigger flawed execution and capital loss.

AI agents often fall into **Tunnel Vision**: fixing obvious cosmetic bugs (hardcoded numbers, countdown timers, CSS layouts) while completely missing deep logical flaws in the underlying data table columns.

This skill enforces a **Three-Layer Audit Protocol** and a mandatory **Column-by-Column Domain Inspection** before any dashboard or reporting view can be considered complete.

---

## When to Use

- When asked to "review, check, or audit" a dashboard, terminal, report, or financial data view.
- When building or modifying table columns, metric cards, status badges, or live tickers.
- When integrating market feeds, scan snapshots, or history trackers into the user interface.
- When users report "lack of synchronization", "data feels wrong", or numbers don't match expectations.

---

## The Three-Layer Audit Framework

Every financial dashboard and data presentation must be audited across three distinct, independent layers:

```
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 1: Presentation & Realtime Interaction                    │
│ HTML/CSS Layout • Responsiveness • Client JS • Live Ticker •    │
│ Cache-Busting • Color Palette Standards (Purple/Green/Red/Floor)│
└────────────────────────────────┬────────────────────────────────┘
                                 │ fed by
┌────────────────────────────────┴────────────────────────────────┐
│ LAYER 2: Data Pipeline, Storage & State Continuity              │
│ REST API Feeds • Snapshot JSONL • Session Debounce • Deduplication│
│ Test Pollution Guard • Rolling Window Size & Performance Limits │
└────────────────────────────────┬────────────────────────────────┘
                                 │ computes
┌────────────────────────────────┴────────────────────────────────┐
│ LAYER 3: Column-by-Column Domain Logic & Reality Check          │
│ Mathematical Formulas • Historical Fallback • Sign Consistency  │
│ Badge Legitimacy • Anti-FOMO Guard • Investor Persona Intuition │
└─────────────────────────────────────────────────────────────────┘
```

---

## Layer-by-Layer Verification Checklist

### 1. Layer 1: Presentation & Realtime Interaction
- [ ] **No Hardcoded Values:** Every single KPI card, badge, summary metric, and table cell must derive dynamically from the ingested dataset.
- [ ] **Realtime Auto-Refresh & Ticker:** If a countdown or live poll exists, verify it fetches live data without full page reload and handles network drops gracefully.
- [ ] **Cache-Busting:** Script requests or API calls must include timestamps or random query parameters (`_t=Date.now()`) to prevent stale browser caching.
- [ ] **Standard Financial Color Semantics:**
  - Trần (Ceiling): Tím (`#c084fc` / `#d8b4fe`)
  - Tăng (Gain): Xanh lục (`#4ade80` / `#22c55e`)
  - Tham chiếu (Reference): Vàng (`#facc15` / `#eab308`)
  - Giảm (Loss): Đỏ (`#f87171` / `#ef4444`)
  - Sàn (Floor): Xanh lơ (`#38bdf8` / `#06b6d4`)
- [ ] **Screen Ergonomics:** Data tables must fit within standard viewports without breaking into horizontal scroll unless explicitly designed.

### 2. Layer 2: Data Pipeline & State Continuity
- [ ] **Session Debounce:** Repeated user requests or scans within short windows (e.g., 30 minutes) must not compare against themselves or generate duplicate noisy snapshots.
- [ ] **Test Pollution Guard:** Testing frameworks (`pytest`, mocks) must NEVER write to or contaminate production history logs (`data/ranking_history.jsonl`, `data/active_signals.jsonl`).
- [ ] **Rolling Window & Zero-Waste:** Historical logs must be capped (e.g., max 500 records) to keep file sizes under tens of kilobytes, preserving the $< 15\text{ MB}$ repository limit.
- [ ] **Graceful Fallback:** If live feeds or APIs fail, the dashboard must fall back to cached snapshots with clear visual status indicators rather than rendering blank or crashing.

### 3. Layer 3: Column-by-Column Domain Logic (CRITICAL)
Every column in the data table must pass an individual audit:

| Audit Question | Requirement | Red Flag Failure Mode |
|---|---|---|
| **What does this column actually represent?** | Clear business definition documented in spec. | Ambiguous abbreviation without tooltip or docs. |
| **Where does the previous baseline come from?** | Historical snapshot lookup across the entire timeline. | Assuming "previous period" only means the immediate prior scan batch. |
| **What happens if an entity temporarily drops out?** | **Historical Fallback:** Compare against the last known appearance. | Marking an existing stock as `🆕 MỚI` just because it was absent in 1 scan. |
| **Are signs and directions consistent?** | Improvement = `+` or `↗` (Green); Deterioration = `-` or `↘` (Red). Rank 1 is better than Rank 5 ($\Delta = 5 - 1 = +4$). | Mathematically $1 - 5 = -4$ displayed as a red drop when the stock actually surged into Top 1. |
| **Does it make sense to a real investor?** | Numbers reflect market realities under T+2.5 trading rules. | Overcomplicating a simple metric or assuming unrealistic T+0 intra-day exits. |

---

## Anti-Tunnel-Vision Gate (Chống Lỗi Bề Nổi)

When an agent is tasked with fixing "Dashboard desynchronization" or "Review Dashboard":

> [!CAUTION]
> **ANTI-RATIONALIZATION RULE:**
> It is FORBIDDEN to consider a dashboard audit complete after only fixing visual elements (Header Cards, CSS, Auto-reload, Countdown Timer). 
> The agent MUST explicitly inspect and audit the **domain logic of each individual column in the main data table**.

### Required Action Flow:
1. **Catalog all columns:** List every column header in the table (e.g., Symbol, Price, ADTV20, Liquidity Tier, IBD Score, Accumulation Grade, Prev Rank Delta, Entry Zone).
2. **Trace data origins:** Identify the exact Python/JS function generating values for each column.
3. **Simulate 3 temporal states:**
   - State A: Stock appears for the very first time.
   - State B: Stock stays in the list across consecutive scans.
   - State C: Stock drops out for 1-2 scans, then re-enters the list.
4. **Verify edge cases:** Ensure missing history, zero values, or division by zero yield sensible badges instead of `NaN`, `None`, or misleading `🆕 MỚI`.

---

## The Investor Persona Test

Before closing any dashboard task, ask:
> *"If I were an active portfolio manager or individual trader risking real capital using this dashboard, would any number or label on this screen confuse me or mislead my trading decision?"*

If the answer is yes or uncertain:
- Do not assume.
- Surface the ambiguity directly.
- Apply the simplest, most intuitive domain logic.
