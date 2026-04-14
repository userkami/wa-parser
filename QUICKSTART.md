# WhatsApp Property Parser - Quick Start Guide

## Installation (One-time setup)

### 1. Install Python 3.11+
Ensure you have Python installed:
```bash
python --version  # Should be 3.11 or higher
```

### 2. Install Dependencies
From the project directory:
```bash
pip install -r whatsapp_parser/requirements.txt
```

Dependencies:
- `streamlit` - Web UI
- `pandas` - Data processing
- `openpyxl` - Excel export
- `chardet` - Encoding detection
- `python-dateutil` - Date parsing
- `regex` - Advanced regex patterns

## Running the Parser

### Option 1: Web UI (Recommended for most users)

```bash
cd e:\Apps\wa-parser
streamlit run whatsapp_parser/ui/app.py
```

This opens a browser at `http://localhost:8501` where you can:
- Upload WhatsApp .txt files
- View parsing results
- Download Excel exports
- Review flagged records
- Manage dictionaries

### Option 2: Command Line

```bash
cd e:\Apps\wa-parser
python main.py /path/to/your/chat_export.txt
```

Outputs Excel file to `./exports/`

### Option 3: Test with Sample Data

```bash
cd e:\Apps\wa-parser
python main.py whatsapp_parser/tests/fixtures/sample_chat.txt
```

Parses a 15-message sample and outputs to `./exports/sample_chat_*.xlsx`

## Exporting WhatsApp Chats

### From Android
1. Open WhatsApp Group
2. Tap three dots (menu) → Settings
3. Select "Chat" → "Export chat" → "Without media"
4. Save the .txt file to your computer

### From iPhone
1. Open WhatsApp Group
2. Swipe left on chat → More → Export Chat → Without Media
3. Save the text file

### Required Format
The exported file must:
- Be `.txt` (text) format
- Have messages with timestamps
- Follow format like: `12/04/2026, 9:30 am - Name: Message`

## Output Files

### Excel Export Sheets

| Sheet Name | Contents |
|---|---|
| **Imports** | Metadata about the import (1 row) |
| **Raw Messages** | Original messages with classifications |
| **Parsed Records** | Structured extracted data |
| **Needs Review** | Low-confidence records requiring human review |
| **High Confidence** | Records with confidence ≥ 0.7 |
| **Prism Offers** | Phase 9 Prism properties |
| **1 Kanal Offers** | 1 kanal listings |
| **10 Marla Offers** | 10 marla listings |

### Key Columns in Parsed Records

**Identity**
- `sender_name` - Who posted (normalized)
- `message_datetime` - When posted

**Property Details**
- `phase` - Phase 7, 8, 9 Prism, 10
- `standardized_plot_size` - 5 marla, 10 marla, 1 kanal, 2 kanal
- `sector_or_block` - Q Block, AA Block, J Block, etc.
- `plot_number` - Number if found

**Pricing**
- `demand_amount_pkr` - Price in integer KR (most important!)
- `demand_amount_lakh` - Derived from PKR
- `demand_amount_display` - Human-readable (e.g., "2.95 Crore")

**Flags**
- `corner_flag` - Corner lot marker
- `urgency_flag` - Urgent sale indication
- `direct_client_flag` - Direct from owner
- `possession_flag` - Ready possession
- `utility_paid_flag` - Utilities paid

**Quality**
- `extraction_confidence` - 0.0 to 1.0 score
- `needs_review` - Whether flagged for manual review
- `duplicate_type` - none/exact/near_same_sender/possible_same_inventory
- `original_message` - Raw text preserved

## Customizing Extraction

Edit JSON files in `whatsapp_parser/dictionaries/`:

### phase_aliases.json
Add variations your group uses:
```json
{
  "phase_9_prism": ["prism", "p9 prism", "phase 9", "prizm", "your_local_name"]
}
```

### size_aliases.json
Normalize size patterns:
```json
{
  "1 kanal": ["1 kanal", "1k", "1-kanal", "one kanal", "your_local_term"]
}
```

### block_aliases.json
Standardize block names:
```json
{
  "Q Block": ["q block", "q blk", "block q", "local_nickname"]
}
```

### keyword_signals.json
Words that indicate a property offer:
```json
{
  "property_offer_keywords": [
    "available", "sale", "demand", "asking", "urgent", "possession",
    "your_keyword_here"
  ]
}
```

**After editing dictionaries**, restart the parser for changes to take effect.

## Perfect Extraction Conditions

For best results, messages should include:
- ✅ **Phase** - "Prism", "Phase 7", "P10"
- ✅ **Size** - "1 kanal", "10 marla", "5 marla"  
- ✅ **Price** - "2.95 cr", "1.10 crore", "85 lac"
- ✅ **Block** - "Q Block", "AA Block"

Example ideal message:
```
1 kanal Q block Prism 2.95cr direct client plot 234
```

Result:
- Phase: phase_9_prism
- Size: 1 kanal
- Block: Q Block
- Price: 29,500,000 PKR
- Plot: 234
- Confidence: 0.95

## Understanding Confidence Scores

Confidence = 0.0 to 1.0

**0.9+** - Excellent (publish as-is)
**0.7-0.9** - Good (high confidence)
**0.5-0.7** - Fair (review recommended)
**<0.5** - Low (definitely review)

Lower scores indicate:
- Missing phase or size
- Ambiguous price
- Single-letter blocks without context
- Possible multi-offer not split

Records below 0.5 appear in "Needs Review" sheet.

## Duplicate Detection Explained

The parser identifies 3 types of duplicates:

### Exact Duplicates (99% confidence)
Same sender posted same message within ±5 minutes
→ Remove one manually

### Near Duplicates (75% confidence)
Same seller, same property (phase+size+block), price within 5%
→ Keep latest, archive older

### Same Inventory (Different Sellers) (60% confidence)
Different dealers posting same plot/property
→ Investigate - might be best offer

All duplicates marked with:
- `duplicate_group_id` - Links all duplicates together
- `duplicate_type` - Type of duplication
- `is_latest_in_duplicate_group` - Which one to use

Filter out old duplicates or keep all for audit trail.

## Troubleshooting

### "File not found" error
- Check the file path is correct
- Ensure .txt file exists
- Try absolute path: `C:\Users\YourName\Downloads\chat.txt`

### "Could not decode file" error
- File might be corrupted or wrong encoding
- Re-export from WhatsApp
- Try: `iconv -f WINDOWS-1252 -t UTF-8 input.txt > output.txt`

### Very few records extracted
- Check messages have phase OR size OR price
- Greetings and irrelevant messages are automatically excluded
- Look at "Raw Messages" sheet - check `message_class` column

### Prices not parsing correctly
- Check format: must be like "2.95 cr" not "2.95crore" (with space)
- Look at `demand_amount_text` column to see what was found
- Add custom patterns if needed

### Wrong size or phase extraction
- Check `dictionaries/*.json` files for coverage
- Add missing variations to appropriate JSON file
- Restart parser for changes to take effect

## Best Practices

1. **Regular imports** - Import weekly or bi-weekly to track new inventory
2. **Review low confidence** - Always review records flagged in "Needs Review"
3. **Track duplicates** - Keep duplicate records but archive older ones
4. **Update dictionaries** - Add local terms as you encounter them
5. **Preserve history** - Never delete old imports, always append

## Example Workflow

```
1. Export WhatsApp chat → chat_export.txt
2. Upload to parser
3. Download Excel
4. Review "Needs Review" sheet
5. Fix any extracted values
6. Filter by phase/size as needed
7. Track price trends over time
```

## Support & Issues

For detailed information, see:
- `README.md` - Full documentation
- `WhatsApp_Property_Parser_Blueprint_v2.md` - Technical specification
- Sample chat: `whatsapp_parser/tests/fixtures/sample_chat.txt`

For technical questions, refer to the blueprint's sections on:
- Message format detection (Module B)
- Extraction details (Module E)
- PKR normalization (Section 6)
- Duplicate detection (Module G)
