import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import tempfile
import os
import uuid

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from whatsapp_parser.pipeline import ParsingPipeline


def main():
    st.set_page_config(page_title="WhatsApp Property Parser", layout="wide")
    
    st.title("🏠 WhatsApp Property Group Parser")
    st.markdown("""
    Parse WhatsApp chat exports and extract structured property listings.
    Converts messy text into a searchable, structured inventory database.
    """)
    
    # Sidebar navigation
    page = st.sidebar.radio("Navigation", [
        "Upload & Parse",
        "View Results",
        "Settings"
    ])
    
    if page == "Upload & Parse":
        render_upload_page()
    elif page == "View Results":
        render_results_page()
    elif page == "Settings":
        render_settings_page()


def render_upload_page():
    """Render the file upload and parsing page."""
    st.header("📤 Upload WhatsApp Chat Export")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a WhatsApp exported .txt file",
        type=["txt"],
        help="Export your WhatsApp group chat without media for best results"
    )
    
    if uploaded_file is not None:
        # Save uploaded file to system temp directory (handles permissions automatically)
        
        # Create unique temp file
        temp_filename = f"wa_parser_{uuid.uuid4().hex[:8]}_{uploaded_file.name}"
        temp_path = Path(tempfile.gettempdir()) / temp_filename
        
        try:
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.success(f"✅ File uploaded: {uploaded_file.name}")
        except Exception as e:
            st.error(f"❌ Error saving file: {str(e)}")
            return
        
        # Parsing options
        col1, col2 = st.columns(2)
        with col1:
            import_mode = st.radio(
                "Import Mode",
                ["Full Import", "Incremental Append"],
                help="Full: Process entire file. Incremental: Only new messages."
            )
        
        with col2:
            skip_imported = st.checkbox(
                "Skip already imported messages",
                value=True,
                help="Use fingerprinting to avoid duplicates"
            )
        
        # Parse button
        if st.button("🚀 Parse File", type="primary", use_container_width=True):
            with st.spinner("Processing... This may take a minute."):
                try:
                    pipeline = ParsingPipeline()
                    result = pipeline.process(str(temp_path))
                    
                    # Debug: print result status
                    print(f"[UI] Parse result status: {result.get('parsing_status')}")
                    print(f"[UI] Export path: {result.get('export_path')}")
                    
                    # Store in session for viewing
                    st.session_state['last_result'] = result
                    st.session_state['last_import_id'] = result.get('import_id')
                    
                    # Display summary
                    st.success("✅ Parsing completed!")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Messages", result.get('messages_count', 0))
                    with col2:
                        st.metric("Records Created", len(result.get('parsed_records', [])))
                    with col3:
                        st.metric("Needs Review", sum(1 for r in result.get('parsed_records', []) if r.needs_review))
                    with col4:
                        st.metric("Duplicates Found", sum(1 for r in result.get('parsed_records', []) if r.duplicate_type != 'none'))
                    
                    # Export options
                    st.divider()
                    st.subheader("📊 Export Results")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    # Get export path and setup download
                    export_path = result.get('export_path')
                    
                    # Convert to absolute path if relative
                    if export_path:
                        export_path = str(Path(export_path).resolve())
                    
                    with col1:
                        if export_path and Path(export_path).exists():
                            try:
                                with open(export_path, 'rb') as f:
                                    file_data = f.read()
                                    st.download_button(
                                        label="📥 Download Excel",
                                        data=file_data,
                                        file_name=Path(export_path).name,
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        use_container_width=True
                                    )
                            except Exception as e:
                                st.error(f"❌ Error reading file: {str(e)}")
                        else:
                            # Show debug info
                            if export_path:
                                st.error(f"❌ File not found at:\n`{export_path}`\n\nCheck the terminal for export logs.")
                            else:
                                st.error("❌ No export path returned from parser. Check terminal logs.")
                    
                    with col2:
                        st.info("💡 Google Sheets coming soon")
                    
                    with col3:
                        if st.button("⚙️ View Details", use_container_width=True):
                            st.session_state['show_details'] = True
                    
                except Exception as e:
                    error_msg = str(e)
                    print(f"[UI] Error during parsing: {error_msg}")
                    st.error(f"❌ Error during parsing: {error_msg}\n\nCheck terminal for detailed logs.")


def render_results_page():
    """Render the results viewing page."""
    st.header("📊 View Parsed Results")
    
    if 'last_result' not in st.session_state:
        st.info("No results yet. Upload and parse a file first.")
        return
    
    result = st.session_state['last_result']
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs([
        "Raw Messages",
        "Parsed Records",
        "Needs Review",
        "Duplicates"
    ])
    
    with tab1:
        st.subheader("Raw Messages")
        raw_messages = result.get('raw_messages', [])
        if raw_messages:
            df = pd.DataFrame([m.to_dict() for m in raw_messages])
            st.dataframe(df, use_container_width=True, height=400)
        else:
            st.info("No raw messages")
    
    with tab2:
        st.subheader("Parsed Records")
        parsed_records = result.get('parsed_records', [])
        if parsed_records:
            df = pd.DataFrame([r.to_dict() for r in parsed_records])
            
            # Display summary stats
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Records", len(parsed_records))
            with col2:
                avg_confidence = df['extraction_confidence'].mean() if not df.empty else 0
                st.metric("Avg Confidence", f"{avg_confidence:.2f}")
            with col3:
                prism_count = len(df[df['phase'] == 'phase_9_prism']) if 'phase' in df.columns else 0
                st.metric("Prism Offers", prism_count)
            with col4:
                high_conf = len(df[df['extraction_confidence'] >= 0.7]) if 'extraction_confidence' in df.columns else 0
                st.metric("High Confidence", high_conf)
            
            st.dataframe(df, use_container_width=True, height=400)
        else:
            st.info("No parsed records")
    
    with tab3:
        st.subheader("Records Needing Review")
        parsed_records = result.get('parsed_records', [])
        review_records = [r for r in parsed_records if r.needs_review]
        
        if review_records:
            df = pd.DataFrame([r.to_dict() for r in review_records])
            st.dataframe(df, use_container_width=True, height=400)
            
            st.info(f"📝 {len(review_records)} records need review")
        else:
            st.success("✅ All records are high confidence!")
    
    with tab4:
        st.subheader("Duplicate Analysis")
        parsed_records = result.get('parsed_records', [])
        dup_records = [r for r in parsed_records if r.duplicate_type != 'none']
        
        if dup_records:
            df = pd.DataFrame([r.to_dict() for r in dup_records])
            
            # Show distribution
            col1, col2, col3 = st.columns(3)
            with col1:
                exact = len([r for r in dup_records if r.duplicate_type == 'exact'])
                st.metric("Exact Duplicates", exact)
            with col2:
                near = len([r for r in dup_records if r.duplicate_type == 'near_same_sender'])
                st.metric("Near Duplicates", near)
            with col3:
                possible = len([r for r in dup_records if r.duplicate_type == 'possible_same_inventory'])
                st.metric("Same Inventory", possible)
            
            st.dataframe(df, use_container_width=True, height=400)
        else:
            st.success("✅ No duplicates found!")


def render_settings_page():
    """Render the settings page."""
    st.header("⚙️ Settings & Dictionaries")
    
    st.subheader("Dictionary Management")
    st.info("Edit phase, size, and block aliases to improve extraction accuracy")
    
    # Show current dictionaries
    tab1, tab2, tab3 = st.tabs(["Phase Aliases", "Size Aliases", "Block Aliases"])
    
    with tab1:
        st.write("Phase recognition patterns")
        phase_dict = {
            "phase_7": ["phase 7", "ph 7", "p7"],
            "phase_8": ["phase 8", "ph 8", "p8"],
            "phase_9_prism": ["prism", "phase 9 prism", "p9 prism"],
            "phase_10": ["phase 10", "ph 10", "p10"],
        }
        st.json(phase_dict)
    
    with tab2:
        st.write("Size recognition patterns")
        size_dict = {
            "1 kanal": ["1 kanal", "1k", "one kanal"],
            "10 marla": ["10 marla", "10m", "ten marla"],
            "5 marla": ["5 marla", "5m", "five marla"],
        }
        st.json(size_dict)
    
    with tab3:
        st.write("Block normalization")
        block_dict = {
            "Q Block": ["q block", "q blk"],
            "AA Block": ["aa block", "a a block"],
        }
        st.json(block_dict)
    
    st.divider()
    st.subheader("Import History")
    st.info("Tracking of all imported files coming soon...")


if __name__ == "__main__":
    main()
