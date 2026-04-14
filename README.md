# WhatsApp Property Group Parser

A comprehensive system for parsing WhatsApp group chat exports and converting messy property listings into structured, searchable inventory data.

## Overview

This parser processes exported WhatsApp chat files from property dealer groups and extracts:
- **Property details**: Phase, size, block, plot number, property type
- **Pricing**: Normalized to canonical PKR integer format
- **Flags**: Urgency, possession, direct client, corner lot, etc.
- **Metadata**: Sender, timestamp, confidence scores, duplicates

The system uses **broad parsing + structured storage + spreadsheet filtering** as recommended in the blueprint.

## Features

✅ **Format Detection** - Supports Android & iOS WhatsApp export variants  
✅ **Message Segmentation** - Reliable multi-line message splitting  
✅ **Smart Normalization** - Urdu phonetics, alias mapping  
✅ **Multi-Offer Detection** - Splits messages with multiple listings  
✅ **Price Normalization** - All prices converted to integer PKR  
✅ **Duplicate Detection** - 3-level duplicate identification  
✅ **Confidence Scoring** - Flags low-confidence extractions for review  
✅ **Excel/CSV Export** - Multiple sheets with filtered views  
✅ **Web UI** - Streamlit interface for easy use  

## Tech Stack

- **Backend**: Python 3.11+
- **Data**: pandas, openpyxl (Excel export)
- **Text Processing**: regex, unicodedata
- **Encoding**: chardet
- **Date Parsing**: python-dateutil
- **UI**: Streamlit

## Installation

### 1. Clone/Setup

```bash
cd e:\Apps\wa-parser
```

### 2. Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r whatsapp_parser/requirements.txt
```

## Usage

### Option A: Web UI (Recommended)

```bash
streamlit run whatsapp_parser/ui/app.py
```

This opens a web interface where you can:
- Upload WhatsApp .txt files
- View parsed results
- Download Excel exports
- Review flagged records
- Manage alias dictionaries

### Option B: Command Line

```bash
python main.py /path/to/chat_export.txt
```

This parses the file and exports Excel to `./exports/`

## Project Structure

```
whatsapp_parser/
├── main.py                          # CLI entry point
├── requirements.txt
├── pipeline/
│   ├── __init__.py
│   ├── pipeline.py                  # Main orchestrator
│   ├── base.py                      # Base module + error handling
│   ├── dictionary_manager.py         # Alias management
│   ├── file_loader.py               # Module A: File intake
│   ├── message_splitter.py           # Module B: Message segmentation
│   ├── normalizer.py                # Module C: Normalization
│   ├── classifier.py                # Module D: Classification
│   ├── multi_offer_splitter.py       # Module F: Multi-offer detection
│   ├── extractor.py                 # Module E: Field extraction
│   ├── pkr_normalizer.py            # PKR conversion
│   ├── deduper.py                   # Module G: Duplicate detection
│   ├── confidence_scorer.py         # Module H: Confidence scoring
│   └── exporter.py                  # Module J: Export
├── models/
│   ├── __init__.py
│   ├── raw_message.py               # RawMessage dataclass
│   └── parsed_record.py             # ParsedRecord dataclass
├── dictionaries/
│   ├── phase_aliases.json
│   ├── size_aliases.json
│   ├── block_aliases.json
│   ├── keyword_signals.json
│   └── ignore_keywords.json
├── ui/
│   └── app.py                       # Streamlit web interface
└── tests/
    └── fixtures/
        └── sample_chat.txt          # Sample WhatsApp export
```

## Pipeline Modules

The parser executes a 10-module pipeline:

1. **File Loader** - Validates file type, detects encoding, normalizes line endings
2. **Message Splitter** - Detects WhatsApp format, segments messages, handles multiline
3. **Normalizer** - Lowercases, removes whitespace, maps Urdu phonetics
4. **Classifier** - Assigns message class (offer/requirement/update/irrelevant)
5. **Multi-Offer Splitter** - Detects and splits multi-offer messages
6. **Field Extractor** - Extracts phase, size, block, price, flags, keywords
7. **PKR Normalizer** - Converts all prices to canonical integer PKR
8. **Deduper** - Identifies exact/near/possible duplicate records
9. **Confidence Scorer** - Calculates confidence 0.0-1.0, flags for review
10. **Exporter** - Writes to Excel with multiple sheets and views

## Data Model

### RawMessage
Represents original WhatsApp message, never modified after ingestion:
- `message_text_raw`: Original untouched text
- `sender_raw`, `sender_normalized`: Sender info
- `message_datetime`: Parsed timestamp
- `message_class`: Classification label
- `message_fingerprint`: SHA256 for duplicate detection

### ParsedRecord
Structured extraction of property information:
- **Identification**: `record_id`, `raw_message_id`, `import_id`
- **Property**: `phase`, `sector_or_block`, `standardized_plot_size`, `property_category`
- **Price**: `demand_amount_pkr` (integer), `demand_amount_lakh`, `demand_amount_display`
- **Flags**: `corner_flag`, `urgency_flag`, `direct_client_flag`, etc.
- **QA**: `extraction_confidence`, `needs_review`, `reviewed_status`
- **Duplicates**: `duplicate_group_id`, `duplicate_type`, `is_latest_in_duplicate_group`

## Excel Export Sheets

1. **Imports** - Metadata about each import
2. **Raw Messages** - Original messages with classification
3. **Parsed Records** - Fully structured extractions
4. **Needs Review** - Low-confidence records requiring human review
5. **High Confidence** - Records with confidence ≥ 0.7
6. **Prism Offers** - Phase 9 Prism properties
7. **1 Kanal Offers** - 1 kanal listings
8. **10 Marla Offers** - 10 marla listings

## Configuration

Edit dictionaries in `whatsapp_parser/dictionaries/` to customize:

### phase_aliases.json
Map variations of phase names to canonical values:
```json
{
  "phase_9_prism": ["prism", "p9 prism", "phase 9 prism", "prizm"]
}
```

### size_aliases.json
Normalize plot size variations:
```json
{
  "1 kanal": ["1 kanal", "1k", "one kanal"]
}
```

### block_aliases.json
Standardize block names:
```json
{
  "Q Block": ["q block", "q blk"]
}
```

## Key Features Explained

### Broad Parsing Strategy
The parser does NOT filter at ingestion time. Instead:
- ✅ Ingest ALL property-relevant messages
- ✅ Extract maximum structured info
- ✅ Preserve raw text untouched
- ✅ Mark confidence and flag for review
- ✅ Let spreadsheet filtering handle business logic

### PKR Normalization
All prices stored as integer PKR for clean analytics:
```
Input: "2 cr 95 lac"
PKR: 29,500,000 (integer)
Lakh: 295.0 (derived)
Display: "2.95 Crore" (human-readable)
```

### Duplicate Detection - 3 Levels

**Level 1: Exact Duplicate**
- Same sender + same normalized text + same time window (±5 min)
- Confidence: 99%

**Level 2: Near Duplicate (Same Seller)**
- Same sender + same phase + same size + same block + price ±5%
- Confidence: 75%

**Level 3: Possible Same Inventory (Different Sellers)**
- Same phase + size + block + plot number OR text similarity > 0.85
- Confidence: 60%

### Confidence Scoring

Score = 0.0 to 1.0 based on:
- **+0.6 base**: Phase + size + demand all present
- **+0.1** each: Block, plot number, flags
- **-0.2 each**: Phase/size missing
- **-0.1**: Price missing or ambiguous

Records with score < 0.5 or missing critical fields flagged for review.

## Testing

Use included sample chat:

```bash
python main.py whatsapp_parser/tests/fixtures/sample_chat.txt
```

This parses a 15-message sample with various formats and produces Excel export.

## Future Enhancements

- Google Sheets API integration for direct append
- Advanced ML-based keyword and duplicate detection
- Batch re-parsing with rule version tracking
- Admin review workflow UI
- Advanced analytics and price trend analysis
- Multi-language support beyond Urdu

## Troubleshooting

### File encoding issues
The parser auto-detects UTF-8, UTF-16 LE/BE, Latin-1. If issues persist, try:
```bash
iconv -f WINDOWS-1252 -t UTF-8 input.txt > output.txt
```

### Messages not being split
This usually means the format wasn't detected. Check:
1. Export format (Android vs iOS)
2. Line format: `DD/MM/YYYY, HH:MM - Name:`
3. Check first 50 lines have consistent format

### Empty results
Verify messages are classified correctly:
- Must have property signals (size, phase, price, keywords)
- System messages and greetings are automatically excluded
- Check `message_class` in Raw Messages sheet

## License

Proprietary - DHA Property Parser System

## Support

For issues or feature requests, check the blueprint specification in `WhatsApp_Property_Parser_Blueprint_v2.md`
