# WhatsApp Property Group Parser — Developer Blueprint v2.0

> **One-Line Product Summary:** A WhatsApp dealer-group parsing system that converts messy exported chat text into a searchable, structured, reviewable property inventory database for Excel and Google Sheets.
>
> **Core Principle:** Parse broadly. Structure deeply. Filter later.

---

## Table of Contents

1. [Objective](#1-objective)
2. [Core Product Decision](#2-core-product-decision)
3. [End-to-End Workflow](#3-end-to-end-workflow)
4. [Functional Modules](#4-functional-modules)
   - [Module A — File Intake](#module-a--file-intake)
   - [Module B — Message Segmentation](#module-b--message-segmentation-highest-risk)
   - [Module C — Normalization Layer](#module-c--normalization-layer)
   - [Module D — Message Classification](#module-d--message-classification)
   - [Module E — Structured Field Extraction](#module-e--structured-field-extraction)
   - [Module F — Multi-Offer Splitter](#module-f--multi-offer-splitter-new)
   - [Module G — Duplicate and Similarity Detection](#module-g--duplicate-and-similarity-detection)
   - [Module H — Confidence and Review Scoring](#module-h--confidence-and-review-scoring)
   - [Module I — Alias Feedback Engine](#module-i--alias-feedback-engine-new)
   - [Module J — Export and Persistence](#module-j--export-and-persistence)
5. [Extraction Logic Details](#5-extraction-logic-details)
6. [PKR Price Normalization Standard](#6-pkr-price-normalization-standard-new)
7. [Data Storage Design](#7-data-storage-design)
8. [Error Handling and Recovery Contract](#8-error-handling-and-recovery-contract-new)
9. [Incremental Import Logic](#9-incremental-import-logic)
10. [Reporting and Analytics](#10-reporting-and-analytics)
11. [UI Blueprint](#11-ui-blueprint)
12. [Recommended Architecture](#12-recommended-architecture)
13. [Tech Stack](#13-tech-stack)
14. [Edge Cases Reference](#14-edge-cases-reference)
15. [Quality Rules](#15-quality-rules)
16. [Future-Proofing Recommendations](#16-future-proofing-recommendations)
17. [MVP Deliverables](#17-mvp-deliverables)
18. [Developer Handover Summary](#18-developer-handover-summary)

---

## 1. Objective

Build a system that:

- Accepts exported WhatsApp group chat `.txt` files
- Parses all property-related messages
- Converts them into structured records
- Stores output in Excel or Google Sheets for filtering, tracking, and analysis

The parser must **not** narrowly filter at ingestion time (e.g., only Prism or only 1 Kanal). It must:

- Ingest all property-relevant messages
- Extract maximum structured information from each
- Preserve the original raw message untouched
- Mark parsing confidence and flag duplicates
- Deliver data that is easy to filter in Excel / Google Sheets

---

## 2. Core Product Decision

### Recommended Strategy

**Broad parser + structured storage + spreadsheet filtering**

### Why

Filtering at parse time creates permanent data loss and future limitations. A master structured dataset allows the business to later filter by:

| Dimension | Examples |
|---|---|
| Phase | Phase 7, Phase 8, Prism, Phase 10 |
| Plot size | 5 Marla, 10 Marla, 1 Kanal, 2 Kanal |
| Type | Plot, File, House, Commercial |
| Block | Q Block, AA Block, J Block |
| Dealer | By sender name |
| Date range | Last 7 days, last 30 days |
| Price range | 2.5 Cr – 3 Cr |
| Intent signals | Direct client, urgent sale, possession |

### Scope of Parser

The **only** high-level filter at ingestion is:

- ✅ Include — messages likely to be property offers or property-relevant
- ❌ Exclude — greetings, chatter, media placeholders, unrelated text

Do **not** exclude Phase 7, Phase 8, Prism, or any size at this stage.

---

## 3. End-to-End Workflow

```
Step 1 — Export Chat
  └─ User exports WhatsApp group as .txt (preferably without media)

Step 2 — Upload File
  └─ User uploads .txt into the parser tool

Step 3 — Parse Raw Chat
  └─ System reads, validates, and normalizes the file

Step 4 — Message Segmentation
  └─ Split into individual messages with sender + timestamp

Step 5 — Message Classification
  └─ Classify each as property_offer / buyer_requirement /
       market_update / irrelevant_chat / system_message / unclassified

Step 6 — Multi-Offer Detection
  └─ Detect if one message contains multiple property listings
  └─ Split into child records with parent_raw_message_id reference

Step 7 — Field Extraction
  └─ Extract structured fields from relevant messages

Step 8 — PKR Normalization
  └─ Convert all price variants to canonical integer PKR value

Step 9 — Duplicate Detection
  └─ Flag exact duplicates, near duplicates, same inventory by different dealer

Step 10 — Confidence Scoring
  └─ Score each record 0.0–1.0 and flag low-confidence for review

Step 11 — Alias Feedback Logging
  └─ Log unknown terms to Suggested Aliases sheet for admin review

Step 12 — Storage
  └─ Write to Imports / Raw Messages / Parsed Records sheets

Step 13 — User Filtering
  └─ User applies filters in Excel / Google Sheets
```

---

## 4. Functional Modules

---

### Module A — File Intake

**Input:** WhatsApp exported `.txt`

**Responsibilities:**

- Validate file type (must be `.txt`)
- Detect encoding: UTF-8, UTF-16 LE/BE, Latin-1
- Normalize line endings (`\r\n` → `\n`)
- Reject empty or corrupt files with a user-visible error
- Store import metadata (filename, size, timestamp, encoding detected)

**Output:** Normalized raw text payload + `import_id`

---

### Module B — Message Segmentation *(Highest Risk)*

**Goal:** Split raw text into individual WhatsApp messages reliably across all export format variants.

#### Format Detection Strategy

Before any parsing begins, run a **format scorer** against the first 50 lines.

| Format ID | Pattern | Example |
|---|---|---|
| `android_v1` | `DD/MM/YYYY, H:MM am/pm - Name:` | `12/04/2026, 9:30 am - Ali Estate: text` |
| `android_v2` | `DD/MM/YYYY, HH:MM - Name:` | `12/04/2026, 09:30 - Ali Estate: text` |
| `ios_v1` | `[DD/MM/YYYY, H:MM:SS AM] Name:` | `[12/04/2026, 9:30:12 AM] Ali Estate: text` |
| `ios_v2` | `[DD.MM.YYYY, HH:MM:SS] Name:` | `[12.04.2026, 09:30:12] Ali Estate: text` |
| `unknown` | None matched | Log and alert user |

**Format scoring logic:**

1. Run all 4 regex patterns against first 50 lines
2. Count matches per pattern
3. Select pattern with highest match count (minimum threshold: 5 matches)
4. If no pattern scores above threshold → store as `format_unknown`, flag the import, continue with best-effort parsing

#### Segmentation Rules

- Each new timestamp line starts a new message
- Lines without a timestamp prefix are continuations of the previous message (multiline support)
- Urdu + English mixed text: treat as single text block, do not split on language change
- Media placeholders (`<Media omitted>`, `image omitted`, `video omitted`, `sticker omitted`) → classify as `system_message`
- Forwarded labels → strip label, preserve message body
- Sender names with emojis → normalize by stripping emoji from sender field, preserve in raw
- Sender names with colons (e.g., `A:B Estate:`) → use last colon as the sender/message boundary

#### Output Fields Per Message

| Field | Type | Notes |
|---|---|---|
| `source_file_id` | string | Links to import |
| `raw_message_id` | string | Unique per message |
| `message_datetime_raw` | string | As found in file |
| `message_datetime` | datetime | Parsed ISO 8601 |
| `sender_raw` | string | As found |
| `sender_normalized` | string | Lowercased, trimmed |
| `message_text_raw` | text | Complete original text |
| `line_start` | int | Source line number |
| `line_end` | int | Source line number |
| `format_detected` | string | Which format was used |
| `is_multiline` | boolean | |
| `is_media_placeholder` | boolean | |
| `is_forwarded` | boolean | |

---

### Module C — Normalization Layer

**Goal:** Create a standardized text version for extraction without modifying the raw text.

**Rules:**

- Lowercase all English text
- Preserve `message_text_raw` separately — never overwrite
- Remove extra whitespace
- Normalize punctuation variants (dashes, dots used as separators)
- Normalize Unicode forms (NFC normalization)

#### Abbreviation and Alias Normalization

| Category | Raw Input Variants | Normalized Output |
|---|---|---|
| Phase | `prism`, `phase 9 prism`, `p9 prism`, `9 prism`, `prizm` | `phase_9_prism` |
| Phase | `phase 7`, `ph 7`, `p7`, `ph7` | `phase_7` |
| Phase | `phase 8`, `ph 8`, `p8`, `ph8` | `phase_8` |
| Phase | `phase 10`, `ph 10`, `p10`, `ph10` | `phase_10` |
| Size | `1 kanal`, `1-kanal`, `1k kanal`, `one kanal`, `1kanl`, `1k` | `1 kanal` |
| Size | `10 marla`, `10m`, `10-marla`, `10mrla`, `ten marla` | `10 marla` |
| Size | `5 marla`, `5m`, `5-marla`, `5mrla` | `5 marla` |
| Price | `cr`, `crore`, `crores` | → price extraction module |
| Price | `lac`, `lakh`, `lacs`, `lakhs` | → price extraction module |

#### Transliteration Support (Urdu Phonetic)

Common Urdu words that appear in property messages should be mapped:

| Urdu Phonetic | English Meaning | Action |
|---|---|---|
| `farosh` / `farokht` | for sale | add `sale` keyword signal |
| `darkar` / `darkaar` | required/needed | add `requirement` keyword signal |
| `dastiyab` | available | add `available` keyword signal |
| `qeemat` / `qimat` | price/rate | add `price` keyword signal |
| `raqba` | area/size | add `size` keyword signal |

---

### Module D — Message Classification

**Goal:** Assign a class to every message.

#### Classes

| Class | Description |
|---|---|
| `property_offer` | Seller / dealer offering a property |
| `buyer_requirement` | Buyer looking for a property |
| `market_update` | Rate news, deal closed, market movement |
| `irrelevant_chat` | Greetings, prayers, jokes, admin messages |
| `system_message` | Media placeholders, group events, number changes |
| `unclassified` | Cannot determine — send to review |

#### Classification Logic

Use **hybrid logic**: rule-based first, optional ML later.

**Rule signals for `property_offer`:**

- Combinations of: size + phase, size + demand, plot + block
- Keywords: `available`, `sale`, `demand`, `asking`, `urgent`, `direct`, `possession`, `dastiyab`, `farosh`

**Rule signals for `buyer_requirement`:**

- Patterns: `required`, `need`, `buyer need`, `client demand`, `looking for`, `darkaar`, `chahiye`

**Rule signals for `market_update`:**

- Patterns: `rate update`, `market down`, `today rate`, `deal closed`, `prices`, `file rate`

**Rule signals for `irrelevant_chat`:**

- Patterns: greetings (`salaam`, `hello`, `good morning`), dua/prayer chains, `sticker omitted`, jokes, group admin messages

#### Output Fields

| Field | Notes |
|---|---|
| `message_class` | One of the 6 classes |
| `relevance_score` | 0.0–1.0 |
| `classification_reason` | Short human-readable reason |

---

### Module E — Structured Field Extraction

**Goal:** Extract all property fields from classified relevant messages.

#### Full Field List

**Identity Fields:**

| Field | Type |
|---|---|
| `record_id` | UUID |
| `raw_message_id` | FK to Raw Messages |
| `parent_raw_message_id` | FK (if split from multi-offer) |
| `offer_index` | int (1-based, for multi-offer splits) |
| `import_id` | FK to Imports |
| `message_date` | date |
| `message_time` | time |
| `sender_name` | string |
| `sender_phone` | string (if available) |
| `message_class` | string |
| `original_message` | text (preserved verbatim) |
| `normalized_message` | text |

**Property Fields:**

| Field | Type | Controlled Values |
|---|---|---|
| `phase` | string | `phase_6`, `phase_7`, `phase_8`, `phase_9_prism`, `phase_10`, `other`, `unknown` |
| `sub_phase` | string | Free text |
| `project_name` | string | e.g., `DHA Lahore` |
| `sector_or_block` | string | Normalized block name |
| `plot_size_value` | float | Numeric only |
| `plot_size_unit` | string | `marla`, `kanal` |
| `standardized_plot_size` | string | `5 marla`, `10 marla`, `1 kanal`, `2 kanal`, `other`, `unknown` |
| `property_category` | string | `plot`, `file`, `house`, `commercial`, `apartment`, `shop`, `requirement`, `market_update`, `unknown` |
| `property_subcategory` | string | Free text |
| `plot_number` | string | Store with lower confidence if ambiguous |
| `road_width_if_found` | string | e.g., `30 feet`, `40 feet` |
| `facing_if_found` | string | `park`, `road`, `corner`, `main boulevard` |

**Flags (Boolean):**

| Field | Signal Words |
|---|---|
| `corner_flag` | `corner`, `crner` |
| `boulevard_flag` | `boulevard`, `blvd`, `main` |
| `possession_flag` | `possession`, `possesion`, `poss` |
| `utility_paid_flag` | `utility paid`, `utilities paid` |
| `urgency_flag` | `urgent`, `urgent sale`, `asap` |
| `direct_client_flag` | `direct`, `direct client`, `owner` |
| `dealer_flag` | `dealer`, `agent`, `estate` in sender name |

**Price Fields:**

| Field | Type | Notes |
|---|---|---|
| `demand_amount_pkr` | bigint | Canonical integer, see Section 6 |
| `demand_amount_lakh` | float | Derived from PKR |
| `demand_amount_display` | string | Human-readable e.g. `2.95 Crore` |
| `demand_amount_text` | string | Raw price text from message |
| `price_per_marla_pkr` | bigint | Computed if size known |

**QA Fields:**

| Field | Type |
|---|---|
| `extraction_confidence` | float (0.0–1.0) |
| `needs_review` | boolean |
| `review_reason` | string |
| `reviewed_by` | string |
| `reviewed_status` | string: `pending`, `approved`, `corrected`, `rejected` |
| `keywords_detected` | JSON array |
| `parser_version` | string |
| `rule_version` | string |

---

### Module F — Multi-Offer Splitter *(New)*

**Problem:** Dealers frequently post multiple offers in a single message:

```
1 kanal Q block Prism 2.95cr
10 marla AA block Phase 7 1.10cr urgent
5 marla J block Phase 8 available direct
```

**Without this module:** One raw message → One record → Missed data.

**Data Model:**

```
raw_messages
  └─ raw_message_id: MSG_001

parsed_records
  ├─ record_id: REC_001  parent_raw_message_id: MSG_001  offer_index: 1
  ├─ record_id: REC_002  parent_raw_message_id: MSG_001  offer_index: 2
  └─ record_id: REC_003  parent_raw_message_id: MSG_001  offer_index: 3
```

**Detection Logic:**

1. After normalization, scan for multiple size tokens or multiple phase tokens in one message
2. Use line-break patterns as primary split signal
3. Use semicolon, bullet, or numbered list as secondary split signal
4. If ambiguous: create one record with `needs_review = true` and `review_reason = "possible_multi_offer"`

**Rules:**

- `original_message` is always the **full parent message** — never truncated
- `offer_index` starts at 1; single-offer messages set `offer_index = 1`
- `parent_raw_message_id` equals `raw_message_id` for both single and multi-offer records (self-referencing for single)

---

### Module G — Duplicate and Similarity Detection

**Critical module — build from day one.**

**Why:** Dealer groups contain the same inventory posted repeatedly, same plot shared by multiple dealers, and same message reposted many times.

#### Duplicate Levels

**Level 1 — Exact Duplicate**

- Condition: Same normalized sender + same normalized message body + same date/time window (±5 minutes)
- Action: `duplicate_type = exact`

**Level 2 — Near Duplicate (Same Sender)**

- Condition: Same sender + same phase + same size + same block + same price (±5%) within last 7 days
- Action: `duplicate_type = near_same_sender`

**Level 3 — Possible Same Inventory (Different Sender)**

- Condition: Same phase + same size + same block + same plot number OR text similarity > 0.85
- Action: `duplicate_type = possible_same_inventory`

#### Deduplication Output Fields

| Field | Type | Notes |
|---|---|---|
| `duplicate_group_id` | UUID | Shared across all records in a duplicate cluster |
| `duplicate_type` | string | `none`, `exact`, `near_same_sender`, `possible_same_inventory` |
| `is_latest_in_duplicate_group` | boolean | True for the most recent record in the cluster |
| `duplicate_confidence` | float | 0.0–1.0 |

#### Business Rules

- **Never delete** duplicates from raw storage
- Mark them and let spreadsheet views or filters hide them
- The most recent record in a duplicate group should be the default visible one (`is_latest = true`)

#### Message Fingerprint for Import Deduplication

Generate a fingerprint for each message before storage:

```
fingerprint = SHA256(
  normalized_sender +
  normalized_message_body +
  rounded_timestamp (to nearest 10 minutes)
)
```

If fingerprint already exists in the database → mark as `already_imported`, skip re-parsing.

---

### Module H — Confidence and Review Scoring

**Goal:** Surface uncertain records for human review without blocking the full import.

#### Confidence Score Calculation

| Condition | Score Impact |
|---|---|
| Phase + size + demand all extracted | +0.6 base |
| Block extracted | +0.1 |
| Plot number extracted | +0.05 |
| Flags detected | +0.05 each, capped at +0.1 |
| Phase missing | -0.2 |
| Size missing | -0.2 |
| Demand missing | -0.1 |
| Multiple phases detected | -0.15 |
| Multiple sizes detected | -0.15 |
| Price ambiguous | -0.1 |
| Possible multi-offer unsplit | -0.2 |

Final score clamped to `[0.0, 1.0]`.

#### When to Set `needs_review = true`

- `extraction_confidence < 0.5`
- Phase detected but not resolved to controlled value
- Price text present but numeric extraction failed
- Multiple sizes detected in one record
- Multiple phases detected in one record
- Block matched weakly (e.g., single letter without context)
- Plot number uncertain
- Possible multi-offer not split

---

### Module I — Alias Feedback Engine *(New)*

**Problem:** Static dictionaries accumulate unknowns with no path to fix them systematically.

**Solution:** When the parser encounters a term it cannot resolve, log it.

#### Logging Rules

Log to **Suggested Aliases** sheet when:

- Phase-like token found but matches no alias → log to Phase Alias suggestions
- Size-like token found but matches no alias → log to Size Alias suggestions
- Strong property keyword present but classification still `unclassified` → log message to Unclassified Review

#### Suggested Aliases Sheet Columns

| Column | Notes |
|---|---|
| `suggestion_id` | Auto-increment |
| `raw_term` | The unrecognized term |
| `context_snippet` | 50-character window around the term |
| `suggested_category` | `phase`, `size`, `block`, `keyword` |
| `occurrence_count` | How many times seen |
| `first_seen` | Date |
| `last_seen` | Date |
| `admin_resolution` | Admin fills: target alias or `ignore` |
| `applied_in_version` | Parser version when applied |

**Admin workflow:** Review Suggested Aliases weekly → add resolutions → trigger re-parse or batch update on affected records.

---

### Module J — Export and Persistence

**Responsibilities:**

- Write to all 5 sheets in correct order
- Support `.xlsx` export
- Support `.csv` export
- Support Google Sheets API append
- Support incremental append without breaking historical records
- Handle partial failures gracefully (see Section 8)

---

## 5. Extraction Logic Details

### Phase Extraction

Build an alias dictionary with priority rules:

```
Priority 1: Exact phrase match
Priority 2: Alias match (from dictionary)
Priority 3: Contextual inference (e.g., "Prism" alone → phase_9_prism)
Priority 4: unknown
```

| Alias(es) | Resolved Value |
|---|---|
| `prism`, `phase 9 prism`, `p9 prism`, `9 prism`, `prizm`, `prism phase` | `phase_9_prism` |
| `phase 7`, `ph 7`, `p7`, `ph7`, `phase seven` | `phase_7` |
| `phase 8`, `ph 8`, `p8`, `ph8`, `phase eight` | `phase_8` |
| `phase 10`, `ph 10`, `p10`, `ph10`, `phase ten` | `phase_10` |
| `phase 6`, `ph 6`, `p6` | `phase_6` |

### Size Extraction

Use regex + alias mapping. Store both raw matched text and standardized size.

```python
# Example patterns (non-exhaustive)
r'\b1\s*[-]?\s*kan[a]?[l]?\b'         # 1 kanal variants
r'\bone\s*kan[a]?[l]?\b'              # one kanal
r'\b10\s*[-]?\s*mar[l]?[a]?\b'       # 10 marla variants
r'\b5\s*[-]?\s*mar[l]?[a]?\b'        # 5 marla variants
r'\b8\s*[-]?\s*mar[l]?[a]?\b'        # 8 marla variants
r'\b2\s*[-]?\s*kan[a]?[l]?\b'        # 2 kanal
```

### Block Extraction

Detect and normalize block patterns:

| Raw Input | Normalized |
|---|---|
| `Q block`, `block Q`, `q blk`, `blk q` | `Q Block` |
| `AA block`, `aa block`, `block aa` | `AA Block` |
| `J block`, `j blk`, `block j` | `J Block` |
| `C block`, `c-block` | `C Block` |

Single-letter blocks without surrounding context → extract with `duplicate_confidence` penalty.

### Plot Number Extraction

Patterns:

```
plot no 123       plot # 456
plot number 789   #123
123 plot          p-123
```

**Always store with lower confidence if context is ambiguous.** Never confidently assign a plot number from a generic numeric string.

---

## 6. PKR Price Normalization Standard *(New)*

**Canonical unit:** Integer PKR (Pakistani Rupees)

**Why integer PKR:** Avoids float precision errors in analytics. Lakh and display format are derived, not stored as primary.

### Conversion Table

| Input Text | PKR Integer |
|---|---|
| `2.95 cr` | `29,500,000` |
| `2 crore 95 lac` | `29,500,000` |
| `295 lakh` | `29,500,000` |
| `2 crore 85 lac` | `28,500,000` |
| `3.10 cr` | `31,000,000` |
| `asking 85 lac` | `8,500,000` |

### Conversion Formula

```
1 Crore = 10,000,000 PKR
1 Lakh  = 100,000 PKR

PKR = (crore_value × 10,000,000) + (lakh_value × 100,000)
```

### Storage Fields

| Field | Example |
|---|---|
| `demand_amount_text` | `"2 crore 95 lac"` (raw, preserved) |
| `demand_amount_pkr` | `29500000` (integer) |
| `demand_amount_lakh` | `295.0` (float, derived) |
| `demand_amount_display` | `"2.95 Crore"` (human-readable) |
| `price_per_marla_pkr` | Computed: `demand_amount_pkr / marla_count` |

### Ambiguous Price Handling

- Multiple prices in one message → extract first, flag `needs_review`
- Price range (e.g., `3-3.2 cr`) → store lower as `demand_amount_pkr`, full range text in `demand_amount_text`
- No numeric price, only `negotiable` or `DM for price` → set `demand_amount_pkr = NULL`, set `urgency_flag` signals accordingly

---

## 7. Data Storage Design

### Sheet 1 — Imports

Tracks each uploaded file.

| Column | Type | Notes |
|---|---|---|
| `import_id` | UUID | |
| `file_name` | string | |
| `uploaded_at` | datetime | |
| `parsed_at` | datetime | |
| `parser_version` | string | |
| `rule_version` | string | |
| `format_detected` | string | Which WhatsApp format was detected |
| `total_lines` | int | |
| `total_messages` | int | |
| `relevant_messages` | int | |
| `total_records_created` | int | |
| `duplicate_records_found` | int | |
| `records_needing_review` | int | |
| `import_status` | string | `success`, `partial`, `failed` |
| `error_log` | text | See Section 8 |
| `notes` | text | |

---

### Sheet 2 — Raw Messages

Source-of-truth layer. Never modified after insert.

| Column | Type |
|---|---|
| `raw_message_id` | UUID |
| `import_id` | FK |
| `message_date` | date |
| `message_time` | time |
| `message_datetime` | datetime (ISO 8601) |
| `sender_raw` | text |
| `sender_normalized` | text |
| `message_text_raw` | text |
| `normalized_text` | text |
| `message_class` | string |
| `relevance_score` | float |
| `classification_reason` | string |
| `is_multiline` | boolean |
| `is_forwarded` | boolean |
| `is_media_placeholder` | boolean |
| `format_detected` | string |
| `parse_status` | string |
| `line_start` | int |
| `line_end` | int |
| `message_fingerprint` | string (SHA256) |

---

### Sheet 3 — Parsed Records

Structured layer for filtering and analysis.

| Column | Type |
|---|---|
| `record_id` | UUID |
| `raw_message_id` | FK |
| `parent_raw_message_id` | FK |
| `offer_index` | int |
| `import_id` | FK |
| `message_datetime` | datetime |
| `sender_name` | string |
| `sender_phone` | string |
| `phase` | string (controlled) |
| `sub_phase` | string |
| `sector_or_block` | string |
| `plot_number` | string |
| `standardized_plot_size` | string (controlled) |
| `plot_size_value` | float |
| `plot_size_unit` | string |
| `property_category` | string (controlled) |
| `property_subcategory` | string |
| `road_width_if_found` | string |
| `facing_if_found` | string |
| `demand_amount_pkr` | bigint |
| `demand_amount_lakh` | float |
| `demand_amount_display` | string |
| `demand_amount_text` | string |
| `price_per_marla_pkr` | bigint |
| `possession_flag` | boolean |
| `corner_flag` | boolean |
| `boulevard_flag` | boolean |
| `utility_paid_flag` | boolean |
| `urgency_flag` | boolean |
| `direct_client_flag` | boolean |
| `dealer_flag` | boolean |
| `keywords_detected` | JSON array |
| `extraction_confidence` | float |
| `needs_review` | boolean |
| `review_reason` | string |
| `reviewed_by` | string |
| `reviewed_status` | string |
| `duplicate_group_id` | UUID |
| `duplicate_type` | string |
| `is_latest_in_duplicate_group` | boolean |
| `duplicate_confidence` | float |
| `original_message` | text |
| `parser_version` | string |
| `rule_version` | string |

---

### Sheet 4 — Views / Filtered Use Cases

Formula-driven or manually filtered views.

| View Name | Filter Logic |
|---|---|
| Prism Offers | `phase = phase_9_prism` |
| 1 Kanal Offers | `standardized_plot_size = 1 kanal` |
| 10 Marla Offers | `standardized_plot_size = 10 marla` |
| Phase 7 Offers | `phase = phase_7` |
| Latest 7 Days | `message_datetime >= today - 7` |
| Needs Review | `needs_review = true AND reviewed_status = pending` |
| Duplicate Candidates | `duplicate_type != none AND is_latest = false` |
| Direct / Urgent | `direct_client_flag = true OR urgency_flag = true` |
| High Confidence Only | `extraction_confidence >= 0.7` |

---

### Sheet 5 — Dictionaries

Business-maintained mapping tables.

| Dictionary | Purpose |
|---|---|
| Phase Aliases | Raw term → controlled phase value |
| Size Aliases | Raw term → standardized size |
| Block Normalization | Raw block text → canonical block name |
| Keyword Signals | Word → signal category |
| Ignore Keywords | Terms that always mean irrelevant |

---

### Sheet 6 — Suggested Aliases *(New)*

Auto-populated by the Alias Feedback Engine.

Columns: `suggestion_id`, `raw_term`, `context_snippet`, `suggested_category`, `occurrence_count`, `first_seen`, `last_seen`, `admin_resolution`, `applied_in_version`

---

## 8. Error Handling and Recovery Contract *(New)*

**Every import must have a defined failure behavior.**

### Failure Levels

| Level | Description | Behavior |
|---|---|---|
| `FATAL` | File unreadable, completely corrupt, wrong encoding | Reject file, surface error to user, do not create import record |
| `IMPORT_PARTIAL` | File partially read, segmentation failed mid-file | Create import record with `status = partial`, store successfully parsed messages, log error position |
| `RECORD_FAIL` | Individual message extraction failed | Skip that record, log to `error_log`, continue with remaining messages |
| `FIELD_FAIL` | Individual field extraction failed | Store `unknown` for that field, add to `needs_review`, continue |

### Error Log Format

```json
{
  "import_id": "abc123",
  "errors": [
    {
      "level": "RECORD_FAIL",
      "raw_message_id": "msg_047",
      "line_start": 312,
      "line_end": 315,
      "error_type": "segmentation_mismatch",
      "error_message": "Could not determine sender boundary",
      "timestamp": "2026-04-12T10:30:00Z"
    }
  ]
}
```

### Partial Import Behavior

- A partial import is **not a failed import** — it is stored and flagged
- The import record shows `status = partial` with a count of skipped messages
- User is shown: "Import completed with warnings. X messages could not be parsed. View error log."
- Partial imports can be **re-attempted** with an updated parser version

### Re-Parse Support

Because `parser_version` is stored on every record:

- Admin can identify records parsed with an older rule set
- Batch re-parse can be triggered on selected `import_id` values
- New records are created with `offer_index` incremented if structure changed
- Old records are marked `superseded = true` (never deleted)

---

## 9. Incremental Import Logic

**Problem:** User will import files repeatedly over time. New exports overlap with old ones.

### Message Fingerprint Check

Before processing any message:

1. Generate fingerprint: `SHA256(normalized_sender + normalized_body + rounded_timestamp)`
2. Query existing fingerprints in database
3. If match found → set `parse_status = already_imported`, skip extraction
4. If no match → proceed normally

### Import Modes

| Mode | Description |
|---|---|
| `full_import` | Process entire file, use fingerprints to skip already-seen messages |
| `incremental_append` | Process only messages newer than last import timestamp for this group |

### Recommended Approach

Use both:

- Preserve full import history (never delete)
- Use fingerprints to prevent duplicate records in Parsed Records sheet
- Store `import_id` on every record so you always know which file introduced it

---

## 10. Reporting and Analytics

### Basic Analytics (V1)

- Count of offers by phase
- Count by standardized size
- Average demand (PKR) by phase + size
- Dealers posting most frequently
- Offers posted today / this week
- Duplicate ratio per import

### Advanced Analytics (V2+)

- Same plot price movement over time (using `plot_number` + `block` + `phase` composite key)
- Dealer-wise inventory activity (postings per day)
- Average asking price by block within a phase
- Demand trend for Prism 1 Kanal over rolling 30 days
- `needs_review` ratio per dealer (high ratio = messy poster)

### Recommendation

Store `demand_amount_pkr` as integer from day one. All future trend analysis and aggregation is trivial from this canonical field.

---

## 11. UI Blueprint

### Screen 1 — Upload

- File picker: `.txt` only
- Destination selector: `Excel Download` / `Google Sheets Append`
- Import mode: `Full Import` / `Incremental Append`
- Checkbox: Skip messages already imported (fingerprint check)
- **Parse** button

### Screen 2 — Import Summary

After parsing completes:

| Metric | Display |
|---|---|
| Total messages in file | e.g., `1,243` |
| Relevant messages | e.g., `487` |
| Records created | e.g., `512` (can exceed messages due to multi-offer splits) |
| Already imported (skipped) | e.g., `156` |
| Duplicates flagged | e.g., `89` |
| Records needing review | e.g., `34` |
| Format detected | e.g., `android_v1` |
| Errors / warnings | Link to error log |

Buttons: `Download Excel` / `Push to Google Sheets` / `Review Flagged Records`

### Screen 3 — Review Queue

Table of low-confidence rows:

| Column | Notes |
|---|---|
| Original message | Full text, read-only |
| Extracted phase | Editable inline |
| Extracted size | Editable inline |
| Extracted price | Editable inline |
| Extracted block | Editable inline |
| Confidence | Color-coded badge |
| Review reason | e.g., `phase missing`, `possible multi-offer` |
| Approve / Correct / Reject | Action buttons |

### Screen 4 — Alias Manager

- View current dictionaries (all 5 types)
- View Suggested Aliases with occurrence counts
- Resolve suggestions inline: assign to alias or mark ignore
- Trigger re-parse of affected imports after updates

### Screen 5 — Data Export

- Download `.xlsx` (full schema or view only)
- Download `.csv` (Parsed Records only)
- Push to Google Sheets (append or overwrite)
- Select which sheets to include

---

## 12. Recommended Architecture

### Parsing Pipeline

```
1. file_loader          → validate, detect encoding, store metadata
2. message_splitter     → detect format, segment messages, handle edge cases
3. normalizer           → lowercase, aliases, Urdu phonetic mapping
4. classifier           → rule-based message class assignment
5. multi_offer_splitter → detect and split multi-offer messages
6. extractor            → field-by-field regex extraction
7. pkr_normalizer       → price conversion to canonical PKR integer
8. deduper              → fingerprint check + 3-level duplicate detection
9. confidence_scorer    → score each record, flag for review
10. alias_logger        → log unknown terms to Suggested Aliases
11. exporter            → write to xlsx / csv / Google Sheets
```

### Module Interface Contract

Each module must implement:

```python
class BaseModule:
    def process(self, payload: dict) -> dict:
        """
        Input: payload dict from previous module
        Output: enriched payload dict
        Raises: ModuleError with level (FATAL / RECORD_FAIL / FIELD_FAIL)
        """
```

This keeps the pipeline composable and each module independently testable.

---

## 13. Tech Stack

### Backend

| Library | Purpose |
|---|---|
| Python 3.11+ | Core language |
| `pandas` | Data transformation and export |
| `re` (stdlib) | Regex-based extraction |
| `openpyxl` | Excel `.xlsx` export |
| `gspread` | Google Sheets API write |
| `hashlib` (stdlib) | SHA256 fingerprinting |
| `unicodedata` (stdlib) | Unicode NFC normalization |
| `chardet` | Encoding detection |
| `python-dateutil` | Date parsing across multiple formats |

### Frontend Options

| Option | When to Use |
|---|---|
| **Streamlit** | Fastest V1 internal tool — recommended for MVP |
| **React + FastAPI** | When you need a polished multi-user product |

### Why Python

- Best fit for text parsing and regex
- Excellent spreadsheet export libraries
- Fast iteration on rule tuning
- No overhead of a compiled language for this use case

### File Structure

```
whatsapp_parser/
├── main.py                  # Entry point
├── pipeline/
│   ├── file_loader.py
│   ├── message_splitter.py
│   ├── normalizer.py
│   ├── classifier.py
│   ├── multi_offer_splitter.py
│   ├── extractor.py
│   ├── pkr_normalizer.py
│   ├── deduper.py
│   ├── confidence_scorer.py
│   ├── alias_logger.py
│   └── exporter.py
├── dictionaries/
│   ├── phase_aliases.json
│   ├── size_aliases.json
│   ├── block_aliases.json
│   ├── keyword_signals.json
│   └── ignore_keywords.json
├── models/
│   ├── raw_message.py
│   └── parsed_record.py
├── tests/
│   ├── test_splitter.py
│   ├── test_extractor.py
│   ├── test_deduper.py
│   └── fixtures/
│       └── sample_chat.txt
├── ui/
│   └── app.py               # Streamlit app
└── requirements.txt
```

---

## 14. Edge Cases Reference

Developer must explicitly handle all of the following:

| Edge Case | Handling Strategy |
|---|---|
| Multiline messages | Detect by absence of timestamp prefix on continuation lines |
| Mixed Urdu + English | Treat as single text block; apply Urdu phonetic mapping in normalizer |
| Inconsistent date/time formats | Use `python-dateutil` with fallback format list |
| Sender names with colons | Use last colon before message body as boundary |
| Sender names with emojis | Strip emoji from `sender_normalized`, preserve in `sender_raw` |
| Copied forwarded messages | Strip forwarded label; mark `is_forwarded = true` |
| Media placeholders | Classify as `system_message`; do not extract |
| Messages with multiple offers | Route to `multi_offer_splitter` |
| Price omitted | Set `demand_amount_pkr = NULL`; do not guess |
| Size omitted | Set `standardized_plot_size = unknown`; still store if other signals strong |
| Typo spellings (`kanl`, `mrla`, `prizm`) | Cover in alias dictionary + fuzzy match fallback |
| Vague shorthand (`1k p9 available`) | Extract what is found; flag remaining unknowns |
| Same message quoted by another user | Fingerprint will catch; mark as `exact` duplicate |
| Plot number ambiguous | Store with `extraction_confidence` penalty; flag review |
| Price range given (`3–3.2 cr`) | Store lower bound as PKR; full range in `demand_amount_text` |
| No sender after colon | Mark `sender_normalized = unknown`; parse message body normally |
| Empty message body | Mark `parse_status = empty_body`; do not create Parsed Record |
| File with BOM (UTF-16) | Detect and strip BOM in `file_loader` before segmentation |

---

## 15. Quality Rules

### Minimum Conditions to Create a Parsed Record

Create a structured record if **any** of these are true:

- Phase + size detected
- Size + demand detected
- Phase + demand detected
- Strong property-offer keywords detected (≥ 2 signals)

### Do Not Create a Parsed Record When

- Pure greeting with no property content
- Media placeholder only
- No property indicators whatsoever
- System message (group events, contact cards)

### Preserve Ambiguity

If a record is relevant but incomplete:

- Still store it
- Mark unknown fields as `unknown` or `NULL`
- Set `needs_review = true`
- Do **not** discard the record

---

## 16. Future-Proofing Recommendations

Include these fields from day one even if not fully used:

| Field | Why |
|---|---|
| `parser_version` | Enables targeted re-parsing when rules improve |
| `rule_version` | Separate versioning for dictionaries vs code |
| `demand_amount_pkr` (integer) | Clean base for all future price analytics |
| `duplicate_group_id` | Enables inventory history tracking across time |
| `needs_review` + `reviewed_status` | Enables human-in-the-loop quality pipeline |
| `source_file_id` / `import_id` | Full traceability back to source |
| `import_timestamps` | Allows time-windowed re-analysis |
| `offer_index` | Enables multi-offer parent-child relationships |
| `message_fingerprint` | Prevents re-import duplication forever |

---

## 17. MVP Deliverables

| # | Deliverable |
|---|---|
| 1 | WhatsApp `.txt` upload parser |
| 2 | Format detector (supports Android + iOS variants) |
| 3 | Raw Messages sheet export |
| 4 | Parsed Records sheet export |
| 5 | Phase, size, block, price, flag extraction |
| 6 | PKR integer normalization for all prices |
| 7 | Multi-offer detection and splitting (basic) |
| 8 | Duplicate marking (all 3 levels) |
| 9 | `needs_review` flagging + review queue screen |
| 10 | Suggested Aliases sheet (auto-populated) |
| 11 | Error log per import |
| 12 | Google Sheets append option |
| 13 | Excel `.xlsx` download |
| 14 | Admin-editable alias dictionaries (JSON files) |
| 15 | Message fingerprinting for incremental imports |

---

## 18. Developer Handover Summary

### Build V1 Around Rule-Based Parsing — Not AI-First

| V1 Priorities | Avoid in V1 |
|---|---|
| Reliable WhatsApp message splitting with format detection | Overcomplicated ML models |
| Strong normalization dictionaries | Over-filtering at ingestion |
| Rule-based classification | Permanently deleting duplicates |
| Regex-based extraction with multi-offer support | Relying on only one WhatsApp export format |
| PKR integer normalization | Guessing prices when text is ambiguous |
| Duplicate grouping (all 3 levels) | Hard-coding phase/size filters at parse time |
| Spreadsheet export (Excel + Google Sheets) | |
| Review workflow with confidence scores | |
| Suggested Aliases feedback loop | |
| Error contract with partial import support | |

### Architecture Decision Summary

| Decision | Choice | Reason |
|---|---|---|
| Canonical price unit | Integer PKR | Avoids float errors; trivial to derive lakh/crore |
| Multi-offer model | Parent-child with `offer_index` | Preserves traceability |
| Duplicate strategy | Mark, never delete | Business data must be auditable |
| Format detection | Score-based multi-pattern | Real-world exports vary too much for one regex |
| Dictionary management | JSON files + Suggested Aliases sheet | Fastest iteration without code deployments |
| Error handling | 4-level contract | Partial imports are business reality, not failures |

---

*Blueprint v2.0 — Improved and extended from original specification.*
*Additions: Format detection strategy, multi-offer data model, PKR normalization standard, alias feedback engine, error handling contract, re-parse support, message fingerprinting.*
