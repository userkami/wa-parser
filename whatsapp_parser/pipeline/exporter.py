import pandas as pd
from typing import Dict, Any
from pathlib import Path
from .base import BaseModule
import tempfile
import sys


class Exporter(BaseModule):
    """
    Module J: Export and Persistence
    - Exports to Excel (.xlsx)
    - Exports to CSV
    - Creates multiple sheets with proper structure
    """
    
    def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Input: {
            import_id, file_name, format_detected,
            raw_messages, parsed_records, error_log
        }
        Output: file paths and export status
        """
        
        # Build dataframes
        raw_messages = payload.get('raw_messages', [])
        parsed_records = payload.get('parsed_records', [])
        
        df_import = pd.DataFrame([{
            'import_id': payload.get('import_id'),
            'file_name': payload.get('file_name'),
            'uploaded_at': pd.Timestamp.now().isoformat(),
            'parser_version': '1.0.0',
            'rule_version': '1.0.0',
            'format_detected': payload.get('format_detected'),
            'total_lines': payload.get('total_lines', 0),
            'total_messages': len(raw_messages),
            'relevant_messages': sum(1 for m in raw_messages if m.message_class != 'irrelevant_chat'),
            'total_records_created': len(parsed_records),
            'duplicate_records_found': sum(1 for r in parsed_records if r.duplicate_type != 'none'),
            'records_needing_review': sum(1 for r in parsed_records if r.needs_review),
            'import_status': 'success',
        }])
        
        df_raw = pd.DataFrame([m.to_dict() for m in raw_messages])
        df_parsed = pd.DataFrame([r.to_dict() for r in parsed_records])
        
        # Create Excel with multiple sheets
        output_path = self._export_excel(payload, df_import, df_raw, df_parsed)
        
        payload['export_path'] = output_path
        payload['export_status'] = 'success'
        
        return payload
    
    def _export_excel(self, payload: Dict, df_import, df_raw, df_parsed) -> str:
        """Export all data to Excel with multiple sheets."""
        try:
            # Use temp directory first (always has write permissions)
            output_dir = Path(tempfile.gettempdir()) / 'wa_parser_exports'
            
            try:
                output_dir.mkdir(exist_ok=True, parents=True)
                print(f"[Exporter] Using temp directory: {output_dir}")
            except Exception as e:
                print(f"[Exporter] Warning: Could not use temp dir, trying project dir: {e}")
                # Try project directory as fallback
                output_dir = Path.cwd() / 'exports'
                output_dir.mkdir(exist_ok=True, parents=True)
            
            import_id = payload.get('import_id', 'export')
            file_name = payload.get('file_name', 'export').replace('.txt', '')
            output_path = output_dir / f"{file_name}_{import_id[:8]}.xlsx"
            
            print(f"[Exporter] Exporting to: {output_path}")
            
            # Write Excel file
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                print(f"[Exporter] Writing Imports sheet...")
                df_import.to_excel(writer, sheet_name='Imports', index=False)
                
                if not df_raw.empty:
                    print(f"[Exporter] Writing Raw Messages sheet ({len(df_raw)} rows)...")
                    df_raw.to_excel(writer, sheet_name='Raw Messages', index=False)
                
                if not df_parsed.empty:
                    print(f"[Exporter] Writing Parsed Records sheet ({len(df_parsed)} rows)...")
                    df_parsed.to_excel(writer, sheet_name='Parsed Records', index=False)
                    
                    # Create filtered views
                    print(f"[Exporter] Creating filtered views...")
                    self._create_views(writer, df_parsed)
            
            # Verify file exists
            if output_path.exists():
                file_size = output_path.stat().st_size
                print(f"[Exporter] ✅ Success! File created: {output_path} ({file_size} bytes)")
                return str(output_path)
            else:
                raise FileNotFoundError(f"Export file was not created at {output_path}")
        
        except Exception as e:
            error_msg = f"Error exporting to Excel: {str(e)}"
            print(f"[Exporter] ❌ {error_msg}", file=sys.stderr)
            raise Exception(error_msg)
    
    def _create_views(self, writer, df: pd.DataFrame):
        """Create filtered view sheets."""
        
        # Needs Review view
        df_review = df[df['needs_review'] == True]
        if not df_review.empty:
            df_review.to_excel(writer, sheet_name='Needs Review', index=False)
        
        # High confidence only
        df_high = df[df['extraction_confidence'] >= 0.7]
        if not df_high.empty:
            df_high.to_excel(writer, sheet_name='High Confidence', index=False)
        
        # Phase 9 Prism offers
        df_prism = df[df['phase'] == 'phase_9_prism']
        if not df_prism.empty:
            df_prism.to_excel(writer, sheet_name='Prism Offers', index=False)
        
        # 1 Kanal offers
        df_1k = df[df['standardized_plot_size'] == '1 kanal']
        if not df_1k.empty:
            df_1k.to_excel(writer, sheet_name='1 Kanal Offers', index=False)
        
        # 10 Marla offers
        df_10m = df[df['standardized_plot_size'] == '10 marla']
        if not df_10m.empty:
            df_10m.to_excel(writer, sheet_name='10 Marla Offers', index=False)
