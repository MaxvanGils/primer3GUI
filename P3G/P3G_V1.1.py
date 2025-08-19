# Primer3GUI version 1.0

import warnings
from cryptography.utils import CryptographyDeprecationWarning
warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning) 
from pathlib import Path
import streamlit as st
import subprocess
import tempfile
import pandas as pd
import os
from xhtml2pdf import pisa
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Preformatted, PageBreak
from io import BytesIO



sidebar_clicked = st.sidebar.button("▶️ Run Primer3", key="sidebar_run")




########################
### Helper Functions ###
######################## 

# Function to extract target sequence from the input sequence
def extract_target_from_sequence(sequence: str):

    start_bracket = sequence.find('[')
    end_bracket = sequence.find(']')

    if (start_bracket != -1 and end_bracket == -1) or (start_bracket == -1 and end_bracket != -1):
        st.error("Mismatched brackets detected. Please ensure both '[' and ']' are present.")
        return None, None
    
    if start_bracket != -1 and end_bracket != -1 and end_bracket > start_bracket:
        target_start = start_bracket +1
        target_length = end_bracket - start_bracket - 1
        return target_start, target_length
    return None, None

# Function to extract excluded regions from the input sequence
def exclude_regions(sequence:str): 
    start_section = sequence.find('<')
    end_section = sequence.find('>')
    
    if (start_section != -1 and end_section == -1) or (start_section == -1 and end_section != -1):
        st.error("Mismatch detected. Please ensure both '<' and '>' are present.")
        return None, None
    if start_section != -1 and end_section != -1 and end_section > start_section:
        excluded_start = start_section + 1
        excluded_length = end_section - start_section - 1
        return excluded_start, excluded_length
    return None, None

# function to set the primer task based on the selected checks and/or sequences 
def determine_primer_task(pick_left, pick_right, pick_internal, left, right, internal):
    # If probe is picked or provided, and at least one primer is picked or provided
    probe_selected = pick_internal or bool(internal.strip())
    left_selected = pick_left or bool(left.strip())
    right_selected = pick_right or bool(right.strip())

    if left_selected and right_selected and probe_selected:
        return "pick_pcr_primers_and_hyb_probe"
    elif left_selected and right_selected:
        return "pick_pcr_primers"
    elif left_selected and probe_selected:
        return "pick_pcr_primers_and_hyb_oligo"
    elif left_selected:
        return "pick_left_only"
    elif right_selected and probe_selected:
        return "pick_pcr_primers_and_hyb_oligo"
    elif right_selected:
        return "pick_right_only"
    elif probe_selected:
        return "pick_hyb_probe_only"
    else:
        return "pick_detection_primers"  # fallback
    
# function to load previous files:
def parse_primer3_input_file(file_text):
    parsed_input_data = {}
    for line in file_text.splitlines():
        if '='in line:
            key, value = line.split('=',1)
            parsed_input_data[key.strip()] = value.strip()
    return parsed_input_data

###


def dataframe_to_html_table(df):
    return df.to_html(index=False, border=1, justify="left", classes="dataframe", escape=False)

def format_sequence_block(rows):
    block = ""
    for idx_row, (seq_row, marker_row) in enumerate(rows):
        row_start = idx_row * 60 + 1
        line_prefix = f"{row_start:>6}" if idx_row else f"   {row_start:>3}"
        block += f"{line_prefix}  {seq_row}\n       {marker_row}\n\n"
    return f"<pre>{block}</pre>"

def generate_full_html_report(results, explanation_summary_df=None, pair_explain_text="", seq_id=""):
    html = f"""
    <html><head>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h2 {{ color: #2c3e50; }}
        table.dataframe {{border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
        table.dataframe th, table.dataframe td {{ border: 1px solid #ccc; padding: 8px; text-align: center; }}
        pre {{ background-color: #f4f4f4; padding: 10px; font-family: monospace; }}
    </style>
    <h1>Primer3 Results — {seq_id}</h1>
    """

    for idx, res in enumerate(results):
        html += f"<h2>Result {idx + 1}</h2>"
        html += dataframe_to_html_table(res['primer_table'])
        html += dataframe_to_html_table(res['product_table'])
        html += "<h3>Binding Sites</h3>"
        html += format_sequence_block(res['sequence_block'])
        html += "<br><hr>"

    #  Add explanation summary at the bottom
    if explanation_summary_df is not None:
        html += "<h2>Primer Explanation Summary</h2>"
        html += dataframe_to_html_table(explanation_summary_df.T)  # flip rows/cols for layout

        if pair_explain_text:
            html += f"<p><strong>Pair summary:</strong> {pair_explain_text}</p>"

    html += "</body></html>"
    return html


def generate_pdf_reportlab(results, explanation_summary_df=None, pair_explain_text=""):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
    leftMargin=36,
    rightMargin=36,
    topMargin=36,
    bottomMargin=36)
    elements = []
    styles = getSampleStyleSheet()
    mono = ParagraphStyle(name='Mono', fontName='Courier', fontSize=8, leading=9)

    elements.append(Paragraph(f"Primer3 Results - {seq_id}", styles["Heading1"]))

    for idx, res in enumerate(results):
        elements.append(Paragraph(f"Result {idx + 1}", styles["Heading2"]))

        # Primer table
        primer_table_data = [res['primer_table'].columns.tolist()] + res['primer_table'].values.tolist()
        primer_table = Table(primer_table_data, repeatRows=1,  colWidths=[110, 45, 30, 45, 45, 35, 35, 180])
        primer_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(primer_table)
        elements.append(Spacer(1, 6))

        # Product table
        product_table_data = [res['product_table'].columns.tolist()] + res['product_table'].values.tolist()
        product_table = Table(product_table_data, repeatRows=1, colWidths=[131,131,131,131])
        product_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(product_table)
        elements.append(Spacer(1, 6))

        # Sequence block
        elements.append(Paragraph("Binding Sites", styles["Heading3"]))
        seq_lines = []
        for seq, marker in res['sequence_block']:
            seq_lines.append(f"{seq}\n{marker}\n")
        elements.append(Preformatted("".join(seq_lines), mono))
        elements.append(Spacer(1, 12))
        # Add a page break after each result except the last one
        if idx < len(results) - 1:
            elements.append(PageBreak())
        
        

    # Explanation Summary Table
    elements.append(PageBreak())
    if explanation_summary_df is not None:
        elements.append(Paragraph("Primer Explanation Summary", styles["Heading2"]))
        explain_table_data = [[""] + list(explanation_summary_df.columns)]
        for idx in explanation_summary_df.index:
            explain_table_data.append([idx] + list(explanation_summary_df.loc[idx]))

        explain_table = Table(explain_table_data, repeatRows=1)
        explain_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#cccccc")),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(explain_table)

    # Pair explanation text
    if pair_explain_text:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(f"<b>Pair summary:</b> {pair_explain_text}", styles["Normal"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer

def convert_windows_to_linux_path(windows_path):
    if ":" not in windows_path:
        raise ValueError("Path must include a drive letter, e.g., C:")
    
    drive, path_part = windows_path.split(":", 1)
    drive = drive.lower()
    path_part = path_part.strip("\\").replace("\\", "/")
    linux_path = f"/mnt/{drive}/{path_part}"
    return linux_path

def resolve_and_check_path(path_input):
    """
    Resolves input path which can be:
    - Absolute Windows path with drive letter -> converted to WSL path
    - Relative path -> resolved relative to current working directory
    Returns tuple: (resolved_path_str, exists_bool)
    """
    path_input = path_input.strip().strip('"').strip("'")  # strip quotes and spaces

    if not path_input:
        return "", False
    
    # Check if it's a Windows absolute path (has drive letter, e.g. C:\)
    if len(path_input) > 1 and path_input[1] == ":":
        try:
            resolved_path = convert_windows_to_linux_path(path_input)
        except Exception as e:
            # If conversion fails, treat as relative fallback
            resolved_path = str(Path(path_input).resolve())
    else:
        # treat as relative path, resolve with current working directory
        resolved_path = str(Path(path_input).resolve())
    
    exists = os.path.exists(resolved_path)
    return resolved_path, exists

#
### === Handle uploaded file before widgets are created ===
uploaded_file = st.sidebar.file_uploader(
    label="Upload Primer3 file created using this tool",
    accept_multiple_files=False,
    type="txt",
    key="file_uploader"
)

if uploaded_file and "imported" not in st.session_state:
    content = uploaded_file.read().decode("utf-8")
    parsed = parse_primer3_input_file(content)
    st.session_state["primer3_parsed"] = parsed

    # Safe to set values before widgets are created
    st.session_state.update({
        "sequence": parsed.get("SEQUENCE_TEMPLATE", ""),
        "seq_id": parsed.get("SEQUENCE_ID", ""),
        "left": parsed.get("SEQUENCE_PRIMER", ""),
        "right": parsed.get("SEQUENCE_PRIMER_REVCOMP", ""),
        "internal": parsed.get("SEQUENCE_INTERNAL_OLIGO", ""),
        "pick_left": parsed.get("PRIMER_PICK_LEFT_PRIMER", "1") == "1",
        "pick_right": parsed.get("PRIMER_PICK_RIGHT_PRIMER", "1") == "1",
        "pick_internal": parsed.get("PRIMER_PICK_INTERNAL_OLIGO", "1") == "1",
        "target": parsed.get("SEQUENCE_TARGET", ""), 
        "excluded_region": parsed.get("EXCLUDED_REGION", "" ),
        "product_size_range": parsed.get("PRIMER_PRODUCT_SIZE_RANGE", ""), 
        "num_return": parsed.get("PRIMER_NUM_RETURN", "" ),
        "max_repeat_mispriming": float(parsed.get("PRIMER_MAX_MISPRIMING", "" )),
        "max_template_mispriming": float(parsed.get("PRIMER_MAX_TEMPLATE_MISPRIMING", "")), 
        "max_3_prime_stability":  float(parsed.get("PRIMER_MAX_END_STABILITY", "" )),
        "pair_max_repeat_mispriming": float(parsed.get("PRIMER_PAIR_MAX_MISPRIMING", "")),
        "pair_max_template_mispriming": float(parsed.get("PRIMER_PAIR_MAX_TEMPLATE_MISPRIMING","")),
        # primer options
        "primer_min_size": int(parsed.get("PRIMER_MIN_SIZE", "")),
        "primer_opt_size": int(parsed.get("PRIMER_OPT_SIZE", "")),
        "primer_max_size": int(parsed.get("PRIMER_MAX_SIZE", "")),
        "primer_min_tm": float(parsed.get("PRIMER_MIN_TM", "")),
        "primer_opt_tm": float(parsed.get("PRIMER_OPT_TM", "")), 
        "primer_max_tm": float(parsed.get("PRIMER_MAX_TM", "")),
        "product_min_tm": float(parsed.get("PRIMER_PRODUCT_MIN_TM", "")),
        "product_opt_tm": float(parsed.get("PRIMER_PRODUCT_OPT_TM", "")),
        "product_max_tm": float(parsed.get("PRIMER_PRODUCT_MAX_TM", "")),
        "primer_min_GC": float(parsed.get("PRIMER_MIN_GC", "")),
        "primer_opt_GC": float(parsed.get("PRIMER_OPT_GC_PERCENT", "")),
        "max_tm_diff": float(parsed.get("PRIMER_PAIR_MAX_DIFF_TM", "")),
        "thermo_param_value": parsed.get("PRIMER_TM_SANTALUCIA", ""),
        "primer_max_self_comp": float(parsed.get("PRIMER_MAX_SELF_ANY", "")),
        "primer_max_3prime_self_comp": float(parsed.get("PRIMER_MAX_SELF_END", "")),
        "max_Ns": int(parsed.get("PRIMER_MAX_NS_ACCEPTED", "")),
        "max_poly_x": int(parsed.get("PRIMER_MAX_POLY_X", "")),
        "primer_inside_target_penalty": float(parsed.get("PRIMER_INSIDE_PENALTY", "")),
        "primer_outside_target_penalty": float(parsed.get("PRIMER_OUTSIDE_PENALTY", "")),
        "primer_first_base_index": int(parsed.get("PRIMER_FIRST_BASE_INDEX", "")),
        "CG_clamp": float(parsed.get("PRIMER_GC_CLAMP", "")),
        "primer_salt_conc_monocat": float(parsed.get("PRIMER_SALT_CONC", "")),
        "primer_salt_conc_divcat": float(parsed.get("PRIMER_DIVALENT_CONC", "")),
        "salt_correction_value": parsed.get("PRIMER_SALT_CORRECTIONS", "" ),
        "primer_dntp_conc": float(parsed.get("PRIMER_DNTP_CONC", "")),
        "annealing_oligo_conc": float(parsed.get("PRIMER_DNA_CONC", "" )),
        ### up to here works
        "liberal_base": parsed.get("PRIMER_LIBERAL_BASE", ""),
        "ambiguity_codes_consensus": parsed.get( "PRIMER_LIB_AMBIGUITY_CODES_CONSENSUS", ""),
        "lowercase_masking": parsed.get("PRIMER_LOWERCASE_MASKING", "" ),
        # probe options
        "probe_min_size": int(parsed.get("PRIMER_INTERNAL_MIN_SIZE", "" )),
        "probe_opt_size": int(parsed.get("PRIMER_INTERNAL_OPT_SIZE", "" )),
        "probe_max_size": int(parsed.get("PRIMER_INTERNAL_MAX_SIZE", "" )),
        "probe_min_tm": float(parsed.get("PRIMER_INTERNAL_MIN_TM", "" )),
        "probe_opt_tm": float(parsed.get("PRIMER_INTERNAL_OPT_TM", "" )),
        "probe_max_tm": float(parsed.get("PRIMER_INTERNAL_MAX_TM", "" )),
        "probe_min_GC": float(parsed.get("PRIMER_INTERNAL_MIN_GC", "" )),
        "probe_opt_GC": float(parsed.get("PRIMER_INTERNAL_OPT_GC_PERCENT", "" )),
        "probe_max_GC": float(parsed.get("PRIMER_INTERNAL_MAX_GC", "")),
        "probe_max_self_comp": float(parsed.get("PRIMER_INTERNAL_MAX_SELF_ANY", "" )),
        "probe_max_Ns": int(parsed.get("PRIMER_INTERNAL_MAX_NS_ACCEPTED", "")),
        "probe_min_seq_qual": float(parsed.get("PRIMER_INTERNAL_OLIGO_MIN_QUALITY", "" )),
        "probe_salt_conc_monocat": float(parsed.get("PRIMER_INTERNAL_OLIGO_SALT_CONC", "" )),
        "probe_salt_conc_divcat": float(parsed.get("PRIMER_INTERNAL_OLIGO_DIVALENT_CONC", "")),
        "probe_max_3prime_self_comp": float(parsed.get("PRIMER_INTERNAL_MAX_SELF_END", "")),
        "probe_max_poly_x": int(parsed.get("PRIMER_INTERNAL_MAX_POLY_X", "")),
        "probe_DNA_conc": float(parsed.get("PRIMER_INTERNAL_DNA_CONC", "")),
        "probe_dntp_conc": float(parsed.get("PRIMER_INTERNAL_DNTP_CONC", "")),
    
        "imported": True
    })
    # Set pick to False if sequence is present
    if st.session_state["left"]:
        st.session_state["pick_left"] = False
    if st.session_state["right"]:
        st.session_state["pick_right"] = False
    if st.session_state["internal"]:
        st.session_state["pick_internal"] = False
    
defaults = {
    "sequence": "",
    "seq_id": "example sequence",
    "left": "",
    "right": "",
    "internal": "",
    "pick_left": False,
    "pick_right": False,
    "pick_internal": False,
    "product_size_range": "100-300 150-250 301-400 401-500 501-600 601-700 701-850 851-1000",
    "num_return": 5,
    "max_template_mispriming": 12.0,
    "pair_max_template_mispriming": 24.0,
    "max_repeat_mispriming": 12.0,
    "pair_max_repeat_mispriming": 24.0,
    "max_3_prime_stability": 9.0,
    "save_input_file": False,
    "input_save_path": os.path.join(os.getcwd(), "primer3_input.txt"),

    # Primer settings
    "primer_min_size": 18,
    "primer_opt_size": 20,
    "primer_max_size": 27,
    "primer_min_tm": 57.0,
    "primer_opt_tm": 60.0,
    "primer_max_tm": 63.0,
    "primer_min_GC": 20.0,
    "primer_opt_GC": 50.0,
    "primer_max_GC": 80.0,
    "max_tm_diff": 100.0,
    "primer_max_self_comp": 8.0,
    "max_Ns": 0,
    "primer_inside_target_penalty": -1.0,
    "primer_outside_target_penalty": 0.0,
    "primer_first_base_index": 1,
    "primer_salt_conc_monocat": 50.0,
    "primer_salt_conc_divcat": 0.0,
    "annealing_oligo_conc": 50.0,
    "thermo_param_value": "0",
    "primer_max_3prime_self_comp": 3.0,
    "max_poly_x": 5,
    "CG_clamp": 0,
    "salt_correction_value": "0",
    "primer_dntp_conc": 0.0,
    "product_min_tm": -1000000,
    "product_opt_tm": 0.0,
    "product_max_tm": 1000000,

    # Probe (internal oligo) settings
    "probe_min_size": 18,
    "probe_opt_size": 20,
    "probe_max_size": 27,
    "probe_min_tm": 57.0,
    "probe_opt_tm": 60.0,
    "probe_max_tm": 63.0,
    "probe_min_GC": 20.0,
    "probe_opt_GC": 50.0,  # Leave empty for auto handling
    "probe_max_GC": 80.0,
    "probe_max_self_comp": 12.0,
    "probe_max_Ns": 0,
    "probe_min_seq_qual": 0,
    "probe_salt_conc_monocat": 50.0,
    "probe_salt_conc_divcat": 0.0,
    "probe_max_3prime_self_comp": 12.0,
    "probe_max_poly_x": 5,
    "probe_DNA_conc": 50.0,
    "probe_dntp_conc": 0.0,

    # Primer3 options
    "liberal_base_checkbox": True,
    "ambiguity_codes_checkbox": True,
    "lowercase_masking_checkbox": False,
    "liberal_base": 0,
    "ambiguity_codes_consensus": 1,
    "lowercase_masking": 1,
}
for key, default in defaults.items():
    st.session_state.setdefault(key, default)





# === Full Primer3 v0.4.0 settings template ===
PRIMER3_TEMPLATE = """SEQUENCE_ID={seq_id}
SEQUENCE_TEMPLATE={sequence}
SEQUENCE_PRIMER={seq_primer}
SEQUENCE_PRIMER_REVCOMP={seq_primer_rev}
SEQUENCE_INTERNAL_OLIGO={seq_internal}
PRIMER_THERMODYNAMIC_OLIGO_ALIGNMENT=0
PRIMER_THERMODYNAMIC_TEMPLATE_ALIGNMENT=0
PRIMER_TASK={primer_task}
PRIMER_PICK_LEFT_PRIMER=1
PRIMER_PICK_INTERNAL_OLIGO=1
PRIMER_PICK_RIGHT_PRIMER=1
PRIMER_NUM_RETURN={num_return}
PRIMER_MIN_5_PRIME_OVERLAP_OF_JUNCTION=5
PRIMER_PRODUCT_SIZE_RANGE={product_size_range}
PRIMER_PRODUCT_OPT_SIZE=0
PRIMER_PAIR_WT_PRODUCT_SIZE_LT=0.0
PRIMER_PAIR_WT_PRODUCT_SIZE_GT=0.0
PRIMER_MIN_SIZE={primer_min_size}
PRIMER_INTERNAL_MIN_SIZE={probe_min_size}
PRIMER_OPT_SIZE={primer_opt_size}
PRIMER_INTERNAL_OPT_SIZE={probe_opt_size}
PRIMER_MAX_SIZE={primer_max_size}
PRIMER_INTERNAL_MAX_SIZE={probe_max_size}
PRIMER_WT_SIZE_LT=1.0
PRIMER_INTERNAL_WT_SIZE_LT=1.0
PRIMER_WT_SIZE_GT=1.0
PRIMER_INTERNAL_WT_SIZE_GT=1.0
PRIMER_MIN_GC={primer_min_GC}
PRIMER_INTERNAL_MIN_GC={probe_min_GC}
PRIMER_OPT_GC_PERCENT={primer_opt_GC}
PRIMER_INTERNAL_OPT_GC_PERCENT={probe_opt_GC}
PRIMER_MAX_GC={primer_max_GC}
PRIMER_INTERNAL_MAX_GC={probe_max_GC}
PRIMER_WT_GC_PERCENT_LT=0.0
PRIMER_INTERNAL_WT_GC_PERCENT_LT=0.0
PRIMER_WT_GC_PERCENT_GT=0.0
PRIMER_INTERNAL_WT_GC_PERCENT_GT=0.0
PRIMER_GC_CLAMP={CG_clamp}
PRIMER_MAX_END_GC=5
PRIMER_MIN_TM={primer_min_tm}
PRIMER_INTERNAL_MIN_TM={probe_min_tm}
PRIMER_OPT_TM={primer_opt_tm}
PRIMER_INTERNAL_OPT_TM={probe_opt_tm}
PRIMER_MAX_TM={primer_max_tm}
PRIMER_INTERNAL_MAX_TM={probe_max_tm}
PRIMER_PAIR_MAX_DIFF_TM={max_tm_diff}
PRIMER_TM_SANTALUCIA={thermo_param_value}
PRIMER_WT_TM_LT=1.0
PRIMER_INTERNAL_WT_TM_LT=1.0
PRIMER_WT_TM_GT=1.0
PRIMER_INTERNAL_WT_TM_GT=1.0
PRIMER_PAIR_WT_DIFF_TM=0.0
PRIMER_PRODUCT_MIN_TM={product_min_tm}
PRIMER_PRODUCT_OPT_TM={product_opt_tm}
PRIMER_PRODUCT_MAX_TM= {product_max_tm}
PRIMER_INTERNAL_OLIGO_MIN_QUALITY={probe_min_seq_qual}
PRIMER_INTERNAL_OLIGO_SALT_CONC={probe_salt_conc_monocat}
PRIMER_INTERNAL_OLIGO_DIVALENT_CONC={probe_salt_conc_divcat}
PRIMER_PAIR_WT_PRODUCT_TM_LT=0.0
PRIMER_PAIR_WT_PRODUCT_TM_GT=0.0
PRIMER_TM_FORMULA=0
PRIMER_SALT_MONOVALENT=50.0
PRIMER_INTERNAL_SALT_MONOVALENT=50.0
PRIMER_SALT_DIVALENT=0.0
PRIMER_INTERNAL_SALT_DIVALENT=0.0
PRIMER_DNTP_CONC={primer_dntp_conc}
PRIMER_INTERNAL_DNTP_CONC={probe_dntp_conc}
PRIMER_SALT_CONC={primer_salt_conc_monocat}
PRIMER_SALT_CORRECTIONS={salt_correction_value}
PRIMER_DIVALENT_CONC={primer_salt_conc_divcat}
PRIMER_DNA_CONC={annealing_oligo_conc}
PRIMER_INTERNAL_DNA_CONC={probe_DNA_conc}
PRIMER_MAX_SELF_ANY={primer_max_self_comp}
PRIMER_INTERNAL_MAX_SELF_ANY={probe_max_self_comp}
PRIMER_PAIR_MAX_COMPL_ANY=8.00
PRIMER_WT_SELF_ANY=0.0
PRIMER_INTERNAL_WT_SELF_ANY=0.0
PRIMER_PAIR_WT_COMPL_ANY=0.0
PRIMER_MAX_SELF_END={primer_max_3prime_self_comp}
PRIMER_INTERNAL_MAX_SELF_END={probe_max_3prime_self_comp}
PRIMER_PAIR_MAX_COMPL_END=3.00
PRIMER_WT_SELF_END=0.0
PRIMER_INTERNAL_WT_SELF_END=0.0
PRIMER_PAIR_WT_COMPL_END=0.0
PRIMER_MAX_END_STABILITY={max_3_prime_stability}
PRIMER_WT_END_STABILITY=0.0
PRIMER_MAX_NS_ACCEPTED={max_Ns}
PRIMER_INTERNAL_MAX_NS_ACCEPTED={probe_max_Ns}
PRIMER_MAX_POLY_X={max_poly_x}
PRIMER_INTERNAL_MAX_POLY_X={probe_max_poly_x}
PRIMER_MIN_THREE_PRIME_DISTANCE=-1
PRIMER_PICK_ANYWAY=1
PRIMER_LOWERCASE_MASKING={lowercase_masking}
PRIMER_EXPLAIN_FLAG=1
PRIMER_LIBERAL_BASE={liberal_base}
PRIMER_FIRST_BASE_INDEX={primer_first_base_index}
PRIMER_MAX_MISPRIMING={max_repeat_mispriming}
PRIMER_PAIR_MAX_MISPRIMING={pair_max_repeat_mispriming}
PRIMER_MAX_TEMPLATE_MISPRIMING={max_template_mispriming}
PRIMER_PAIR_MAX_TEMPLATE_MISPRIMING={pair_max_template_mispriming}
PRIMER_WT_TEMPLATE_MISPRIMING=0.0
PRIMER_PAIR_WT_TEMPLATE_MISPRIMING=0.0
PRIMER_LIB_AMBIGUITY_CODES_CONSENSUS={ambiguity_codes_consensus}
PRIMER_MAX_LIBRARY_MISPRIMING=12.00
PRIMER_INTERNAL_MAX_LIBRARY_MISHYB=12.00
PRIMER_PAIR_MAX_LIBRARY_MISPRIMING=24.00
PRIMER_WT_LIBRARY_MISPRIMING=0.0
PRIMER_INTERNAL_WT_LIBRARY_MISHYB=0.0
PRIMER_PAIR_WT_LIBRARY_MISPRIMING=0.0
PRIMER_MIN_QUALITY=0
PRIMER_INTERNAL_MIN_QUALITY=0
PRIMER_MIN_END_QUALITY=0
PRIMER_QUALITY_RANGE_MIN=0
PRIMER_QUALITY_RANGE_MAX=100
PRIMER_WT_SEQ_QUAL=0.0
PRIMER_INTERNAL_WT_SEQ_QUAL=0.0
PRIMER_PAIR_WT_PR_PENALTY=1.0
PRIMER_PAIR_WT_IO_PENALTY=0.0
PRIMER_INSIDE_PENALTY={primer_inside_target_penalty}
PRIMER_OUTSIDE_PENALTY={primer_outside_target_penalty}
PRIMER_WT_POS_PENALTY=0.0
PRIMER_SEQUENCING_LEAD=50
PRIMER_SEQUENCING_SPACING=500
PRIMER_SEQUENCING_INTERVAL=250
PRIMER_SEQUENCING_ACCURACY=20
PRIMER_WT_END_QUAL=0.0
PRIMER_INTERNAL_WT_END_QUAL=0.0
SEQUENCE_TARGET={target}
EXCLUDED_REGION={excluded_region}
=
"""
tab1, tab2, tab3, tab4 = st.tabs([
    "🧬 Input Settings",
    "📄 Primer3 Raw Output",
    "⚠️ Primer3 Warnings",
    "📊 Primer3 Output",
    
])


# === Tab 1: Input ===
with tab1:
    st.title("Primer3 v0.4.0 - Streamlit GUI")

    sequence = st.text_area("Paste DNA Sequence (5'→3')", height=200, key="sequence")


    seq_id = st.text_input("Sequence ID", help="Identifier for the sequence. This will be used in the Primer3 output.", key="seq_id")

    # checkboxes
    col1, col2, col3 = st.columns(3)

    with col1:
        pick_left = st.checkbox("Pick Forward Primer", key="pick_left", help="Forward / 5' to 3' on same strand.If unchecked, the forward primer will not be designed and needs to be provided.")
        if st.session_state.get("pick_left", False):
            st.session_state["left"] = ""
        left = st.text_input("Forward Primer", key="left", disabled= st.session_state.get("pick_left", True))

    with col2:
        st.checkbox("Pick Probe", key="pick_internal", help="Internal oligo for hybridization. If unchecked, the internal oligo will not be designed and needs to be provided.")
        if st.session_state.get("pick_internal", False):
            st.session_state["internal"] = ""
        st.text_input("Probe (Internal Oligo)", key="internal", disabled=st.session_state.get("pick_internal", True))

    with col3:
        st.checkbox("Pick Reverse Primer", key="pick_right", help="Reverse / complementary 5' to 3' on opposite strand. If unchecked, the reverse primer will not be designed and needs to be provided.")
        if st.session_state.get("pick_right", False):
            st.session_state["right"] = ""
        st.text_input("Reverse Primer (RevComp)", key="right", disabled=st.session_state.get("pick_right", True))
    

    
    # set target and excluded regions
    amp_target = extract_target_from_sequence(st.session_state["sequence"])
    excluded_target = exclude_regions(st.session_state["sequence"])

    if amp_target[0] is not None and amp_target[1] is not None:
        st.info(f"Target sequence detected at position {amp_target[0]} with length {amp_target[1]}.")
        target_str = f"{amp_target[0]},{amp_target[1]}"
        st.session_state["target"] = target_str
    else:
        st.text_input("Target Sequence (optional)", key="target", help="Specify manually or use brackets like TCAT[CAT]GAT.")

    if excluded_target[0] is not None and excluded_target[1] is not None:
        st.info(f"Excluded region detected at position {excluded_target[0]} with length {excluded_target[1]}.")
        excluded_region_str = f"{excluded_target[0]},{excluded_target[1]}"
        st.session_state["excluded_region"] = excluded_region_str
    else:
        st.text_input("Excluded Region (optional)", key="excluded_region", help="Specify manually or use angle brackets like TCA<CTG>GAT.")

    # product size ranges        
    st.text_input("Custom Product Size Range", key="product_size_range", help="Space-separated size ranges (e.g. 100-200 300-400)")
    
    # basic settings
    col1, col2 = st.columns(2)

    if "num_return" in st.session_state and isinstance(st.session_state.num_return, str):
        try:
            st.session_state.num_return = int(st.session_state.num_return)
        except ValueError:
            st.session_state.num_return = 5  # fallback to a safe default 
    with col1:
        st.number_input("Number of Primers to Return", min_value=1, key="num_return", help="Default is 5.")
        st.number_input("Max Repeat Mispriming", min_value=0.0, key="max_repeat_mispriming", help="Default is 12.0")
        st.number_input("Max Template Mispriming", min_value=0.0, key="max_template_mispriming", help="Default is 12.0")

    with col2:
        st.number_input("Max 3' End Stability", min_value=0.0, key="max_3_prime_stability", help="Default is 9.0")
        st.number_input("Max Pair Repeat Mispriming", min_value=0.0, key="pair_max_repeat_mispriming", help="Default is 24.0")
        st.number_input("Max Pair Template Mispriming", min_value=0.0, key="pair_max_template_mispriming", help="Default is 24.0")
        

    #### -> General primer picking settings ####
    
    st.markdown("### General primer picking settings")

    with st.expander("General primer picking settings"):
        col1, col2 , col3 = st.columns(3)
        with col1:


            primer_min_size = st.number_input(
                "Minimum Primer Size",min_value=1,max_value=100,key="primer_min_size",help="Minimum size of the primer in bases. Default is 18."
            )

            primer_min_tm = st.number_input(
                "Minimum Primer Tm",min_value=0.0,max_value=100.0,key="primer_min_tm",help="Minimum melting temperature (Tm) of the primer in degrees Celsius. Default is 57.0."
            )

            
            product_min_tm = st.number_input("Minimum Product Tm",key="product_min_tm")
            
            primer_min_GC = st.number_input("Minimum Primer GC Content (%)",min_value=0.0,max_value=100.0,key="primer_min_GC",help="Minimum GC content of the primer in percentage. Default is 20.0.")

        with col2:

            primer_opt_size = st.number_input(
                "Optimal Primer Size",
                min_value=1,
                max_value=100,
                key="primer_opt_size",
                help="Optimal size of the primer in bases. Default is 20."
            )

            primer_opt_tm = st.number_input(
                "Optimal Primer Tm",
                min_value=0.0,
                max_value=100.0,
                key="primer_opt_tm",
                help="Optimal melting temperature (Tm) of the primer in degrees Celsius. Default is 60.0."
            )
            
            product_opt_tm = st.number_input(
                "Optimal Product Tm",
                key="product_opt_tm", 
            )
            primer_opt_GC = st.number_input(
                "Optimal Primer GC Content (%)",
                min_value=0.0,
                max_value=100.0,
                key="primer_opt_GC",
                help="Optimal GC content of the primer in percentage. Default is 50.0."
            )
        with col3:
            primer_max_size = st.number_input(
                "Maximum Primer Size",
                min_value=1,
                max_value=50,
                key= "primer_max_size",
                help="Maximum size of the primer in bases. Default is 27."
            )
            primer_max_tm = st.number_input(
                "Maximum Primer Tm",
                min_value=0.0,
                max_value=100.0,
                key="primer_max_tm",
                help="Maximum melting temperature (Tm) of the primer in degrees Celsius. Default is 63.0."
            )
                        
            product_max_tm = st.number_input(
                "Maximum Product Tm",
                key="product_max_tm", 
            )
            primer_max_GC = st.number_input(
                "Maximum Primer GC Content (%)",
                min_value=0.0,
                max_value=100.0,
                key="primer_max_GC",
                help="Maximum GC content of the primer in percentage. Default is 80.0."
            )
        col4, col5 = st.columns(2)
        with col4:
            max_tm_diff = st.number_input(
                "Max Tm Difference Between Primers",
                min_value=0.0,
                max_value=100.0,
                key =  "max_tm_diff",
                help="Maximum difference in melting temperature (Tm) between the forward and reverse primers. Default is 100.0."
            )

            primer_max_self_comp = st.number_input(
                "Max Self Complementarity",
                min_value=0.0,
                max_value=100.0,
                key = "primer_max_self_comp",
                help="Maximum self-complementarity allowed for the primer. Default is 8.00."
            )

            max_Ns = st.number_input(
                "Max Ns in Primer",
                min_value=0,
                max_value=100,
                key = "max_Ns",
                help="Maximum number of 'N' bases allowed in the primer. Default is 0."
            )
 

            primer_inside_target_penalty = st.number_input(
                "Primer Inside Target Penalty",
                min_value=-100.0,
                max_value=100.0,
                key = "primer_inside_target_penalty",
                help="Penalty for primers that fall inside the target sequence. Set to allow primers inside a target if multiple targets are given. Default is -1.0."
            )

            primer_first_base_index = st.number_input(
                "Primer First Base Index",
                min_value=1,
                max_value=100,
                key = "primer_first_base_index",
                help="Index of the first base in the primer sequence. Default is 1."
            )

            primer_salt_conc_monocat = st.number_input(
                "Primer Salt Concentration (monovalent, mM)",
                min_value=0.0,
                max_value=100.0,
                key = "primer_salt_conc_monocat",
                help="Salt concentration in millimolar (mM). Default is 50.0."
            )

            primer_salt_conc_divcat = st.number_input(
                "Primer Salt Concentration (divalent cations, mM)",
                min_value=-1.0,
                max_value=100.0,
                key="primer_salt_conc_divcat",
                help="Salt concentration of divalent cations in millimolar (mM). Default is 0.0."
            )

            annealing_oligo_conc = st.number_input(
                "Annealing Oligo Concentration (nM)",
                min_value=0.0,
                max_value=1000.0,
                key = "annealing_oligo_conc",
                help="Concentration of the annealing oligo in nanomolar (nM). Default is 50.0."
            )

        with col5:
            thermo_param_map = {
                "Breslauer et al. 1986": "0",
                "SantaLucia 1998": "1"
            }
            reverse_thermo = {v: k for k, v in thermo_param_map.items()}

            # Get current value (e.g., "0") from session_state or default to "0"
            thermo_value = st.session_state.get("thermo_param_value", "0")

            # Map to label safely, fallback to default label if key doesn't exist
            current_label = reverse_thermo.get(thermo_value, "Breslauer et al. 1986")

            # Now build the selectbox using that label as default
            selected_thermo = st.selectbox(
                "Thermodynamic Table Parameters",
                options=list(thermo_param_map.keys()),
                index=list(thermo_param_map.keys()).index(current_label),
                key="thermo_param_label"
            )

            # Update actual numeric value in session_state for use in template
            st.session_state["thermo_param_value"] = thermo_param_map[selected_thermo]


            primer_max_3prime_self_comp = st.number_input(
                "Max 3' Self Complementarity",
                min_value=0.0,
                max_value=100.0,
                key = "primer_max_3prime_self_comp",
                help="Maximum self-complementarity allowed at the 3' end of the primer. Default is 3.00."
            )

            max_poly_x = st.number_input(
                "Max Poly X",
                min_value=0,
                max_value=100,
                key="max_poly_x",
                help="Maximum number of consecutive identical bases (poly-X) allowed in the primer. Default is 5."
            )

            primer_outside_target_penalty = st.number_input(
                "Primer Outside Target Penalty",
                min_value=-100.0,
                max_value=100.0,
                key = "primer_outside_target_penalty",
                help="Penalty for primers that fall outside the target sequence. Default is 0.0."
            )

            CG_clamp = st.number_input(
                "CG Clamp",
                min_value=0,
                max_value=100,
                key = "CG_clamp",
                help="Require the specified number of consecutive Gs and Cs at the 3' end of both the left and right primer"
            )

            salt_correction_form_map = {
                "Schildkraut and Lifson 1965": "0",
                "Santa Lucia 1998": "1",
                "Owczarzy et al. 2004": "2"
            }

            # Reverse map: value to label
            reverse_salt_map = {v: k for k, v in salt_correction_form_map.items()}

            # Get numeric value ("0", "1", ...) from session_state, fallback to "0"
            salt_val = st.session_state.get("salt_correction_value", "0")

            # Get corresponding label
            current_label = reverse_salt_map.get(salt_val, "Schildkraut and Lifson 1965")

            # Selectbox stores the label in a different key!
            selected_label = st.selectbox(
                "Salt Correction Format",
                options=list(salt_correction_form_map.keys()),
                index=list(salt_correction_form_map.keys()).index(current_label),
                key="salt_correction_label",  # <- changed key here!
                help="Select the salt correction format. Default is Schildkraut and Lifson."
            )

            # Set numeric value separately
            st.session_state["salt_correction_value"] = salt_correction_form_map[selected_label]

            primer_dntp_conc = st.number_input(
                "Primer dNTP Concentration (mM)",
                min_value=0.0,
                max_value=100.0,
                key= "primer_dntp_conc",
                help="Concentration of dNTPs in millimolar (mM). Default is 0.0."
            )

            col6, col7, col8 = st.columns(3)
            with col6:
                st.checkbox("Liberal Base", key="liberal_base_checkbox")
            with col7:
                st.checkbox("Ambiguity Codes Consensus", key="ambiguity_codes_checkbox")
            with col8:
                st.checkbox("Lowercase Masking", key="lowercase_masking_checkbox")
            #might need to move     
            st.session_state["liberal_base"] = 1 if st.session_state.get("liberal_base_checkbox", False) else 0
            st.session_state["ambiguity_codes_consensus"] = 0 if st.session_state.get("ambiguity_codes_checkbox", False) else 1
            st.session_state["lowercase_masking"] = 0 if st.session_state.get("lowercase_masking_checkbox", False) else 1


    #### -> General Hyb oligo picking settings ####
    
    st.markdown("### General internal oligo picking settings")
    with st.expander("General internal oligo picking settings"):
        col1, col2 , col3 = st.columns(3)
        with col1:
            probe_min_size = st.number_input(
                "Minimum Probe Size",
                min_value=1,
                max_value=100,
                key="probe_min_size",
                help="Minimum size of the probe."
            )

            probe_min_tm = st.number_input(
                "Minimum Probe Tm",
                min_value=0.0,
                max_value=100.0,
                key="probe_min_tm",
                help="Minimum melting temperature (Tm) of the probe in degrees Celsius. Default is 57.0."
            )

            probe_min_GC = st.number_input(
                "Minimum Probe GC Content (%)",
                min_value=0.0,
                max_value=100.0,
                key= "probe_min_GC",
                help="Minimum GC content of the probe in percentage. Default is 20.0."
            )
        with col2:
            probe_opt_size = st.number_input(
                "Optimal Probe Size",
                min_value=1,
                max_value=100,
                key="probe_opt_size",
                help="Optimal size of the probe in bases. Default is 16."
            )

            probe_opt_tm = st.number_input(
                "Optimal Probe Tm",
                min_value=0.0,
                max_value=100.0,
                key = "probe_opt_tm",
                help="Optimal melting temperature (Tm) of the probe in degrees Celsius. Default is 60.0."
            )

            probe_opt_GC = st.number_input(
                "Optimal Probe GC Content (%)",
                min_value=0.0,
                max_value=100.0,
                key = "probe_opt_GC" ,
                help="Optimal GC content of the probe in percentage. Leave blank for default"
            )
        with col3:
            probe_max_size = st.number_input(
                "Maximum Probe Size",
                min_value=1,
                max_value=50,
                key ="probe_max_size",
                help="Maximum size of the probe in bases. Default is 27."
            )

            probe_max_tm = st.number_input(
                "Maximum Probe Tm",
                min_value=0.0,
                max_value=100.0,
                key = "probe_max_tm",
                help="Maximum melting temperature (Tm) of the probe in degrees Celsius. Default is 63.0."
            )


            probe_max_GC = st.number_input(
                "Maximum Probe GC Content (%)",
                min_value=0.0,
                max_value=100.0,
                key="probe_max_GC",
                help="Maximum GC content of the probe in percentage. Default is 80.0."
            )
        col4, col5 = st.columns(2)
        with col4:
            probe_max_self_comp = st.number_input(
                "Max Probe Self Complementarity",
                min_value=0.0,
                max_value=100.0,
                key = "probe_max_self_comp",
                help="Maximum self-complementarity allowed for the probe. Default is 12.00."
            )

            probe_max_Ns = st.number_input(
                "Max Ns in Probe",
                min_value=0,
                max_value=100,
                key="probe_max_Ns",
                help="Maximum number of 'N' bases allowed in the probe. Default is 0."
            )

            probe_salt_conc_monocat = st.number_input(
                "Probe Oligo Concentration (monovalent cations, mM)",
                min_value=0.0,
                max_value=100.0,
                key = "probe_salt_conc_monocat",
                help="Concentration of the probe oligo in millimolar (mM). Default is 50.0."
            )

            probe_salt_conc_divcat = st.number_input(
                "Probe Oligo Concentration (divalent cations, mM)",
                min_value=0.0,
                max_value=100.0,
                key = "probe_salt_conc_divcat",
                help="Concentration of divalent cations in millimolar (mM). Default is 0.0."
            )

            probe_min_seq_qual = st.number_input(
                "Minimum Probe Sequence Quality",
                min_value=0,
                max_value=100,
                key = "prob_min_seq_qual",
                help="Minimum sequence quality of the probe. Default is 0."
            )

            #maybe add the libraries?
        with col5:
            probe_max_3prime_self_comp = st.number_input(
                "Max Probe 3' Self Complementarity",
                min_value=0.0,
                max_value=100.0,
                key = "probe_max_3prime_self_comp",
                help="Maximum self-complementarity allowed at the 3' end of the probe. Default is 12.00."
            )
            probe_max_poly_x = st.number_input(
                "Max Probe Poly X",
                min_value=0,
                max_value=100,
                key="probe_max_poly_x",
                help="Maximum number of consecutive identical bases (poly-X) allowed in the probe. Default is 5."
            )
            probe_DNA_conc = st.number_input(
                "Probe DNA Concentration (nM)",
                min_value=0.0,
                max_value=1000.0,
                key = "probe_DNA_conc",
                help="Concentration of the probe DNA in nanomolar (nM). Default is 50.0."
            )
            probe_dntp_conc = st.number_input(
                "Probe dNTP Concentration (mM)",
                min_value=0.0,
                max_value=100.0,
                key= "probe_dntp_conc",
                help="Concentration of dNTPs in millimolar (mM). Default is 0.0."
            )

    ### check if minimum and maximum sizes are respected
    left_seq = st.session_state.get("left", "")
    right_seq = st.session_state.get("right", "")
    internal_seq = st.session_state.get("internal", "")

    min_primer = st.session_state.get("primer_min_size", 18)
    min_internal = st.session_state.get("probe_min_size", 18)
    max_primer = st.session_state.get("primer_max_size", 27)
    max_internal = st.session_state.get("probe_max_size", 27)

    if left_seq and len(left_seq) < min_primer:
        st.warning(f"Forward primer sequence is shorter ({len(left_seq)}) than the minimum set length ({min_primer}).")
    if right_seq and len(right_seq) < min_primer:
        st.warning(f"Reverse primer sequence is shorter ({len(right_seq)}) than the minimum set length ({min_primer}).")
    if internal_seq and len(internal_seq) < min_internal:
        st.warning(f"Probe sequence is shorter ({len(internal_seq)}) than the minimum set length ({min_internal}).")
    if left_seq and len(left_seq) > max_primer:
        st.warning(f"Forward primer sequence is longer ({len(left_seq)}) than the maximum set length ({max_primer}).")
    if left_seq and len(right_seq) > max_primer:
        st.warning(f"Forward primer sequence is longer ({len(right_seq)}) than the maximum set length ({max_primer}).")
    if internal_seq and len(internal_seq) > max_internal:
        st.warning(f"Probe sequence is longer ({len(internal_seq)}) than the maximum set length ({max_internal})")
                
    
    # Add option to save input file ## maybe change to a button?
    save_input_file = st.checkbox("Save input settings file after run", value=defaults["save_input_file"], key="save_input_file")
    input_save_path = ""
    if st.session_state.get("save_input_file", False):
        default_path = defaults["input_save_path"]
        st.text_input(
            "Path to save input file",
            value=default_path,
            key= "input_save_path",
            help="Full path for saving the input settings file (e.g. C:/Users/yourname/Downloads/primer3_input.txt). Defaults to working directory, and simply type a path to follow in the working directory. (e.g. foldername/primer3_input.txt)"
        )
        # check if path exists
        resolved_path, exists = resolve_and_check_path(st.session_state.get("input_save_path", ""))            
        if not exists:
            parent_dir = os.path.dirname(resolved_path)
            try:
                st.info(f"Will create settings file at the following path: {resolved_path}")
            except Exception as e:
                st.error(f"Could not create directory: {parent_dir}. Error: {e}")
        else:
            st.warning(f"Settings file path already exists: {resolved_path}. Please ensure you want to overwrite it.")


    # Run button
    tab1_run = st.button("▶️ Run Primer3", key="tab1_run")
    st.session_state["run"] =  sidebar_clicked or tab1_run
    # if st.session_state["run"]:
    #     st.toast("Running Primer3 with the provided settings...", icon="🔄")

    # Validation
    if st.session_state["run"] and not st.session_state["sequence"].strip():
        st.warning("Please enter a DNA sequence before running Primer3.")

    
    # warning for if one of the primers is not provided or set to pick:
    if (
        st.session_state["run"]
        and st.session_state["sequence"].strip()
        and not st.session_state.get("pick_left", False)
        and not st.session_state.get("pick_right", False)
        and not st.session_state.get("left", "").strip()
        and not st.session_state.get("right", "").strip()
    ):
        st.warning("You must either select to pick primers or provide sequences for the forward and/or reverse primers.")
    if (
        st.session_state["run"]
        and st.session_state["sequence"].strip()
        and (
            (
                st.session_state.get("left", "").strip()
                and not st.session_state.get("pick_right", False)
                and not st.session_state.get("right", "").strip()
            )
            or
            (
                st.session_state.get("right", "").strip()
                and not st.session_state.get("pick_left", False)
                and not st.session_state.get("left", "").strip()
            )
        )
    ):
        st.warning("You must provide both primer sequences or select to pick the missing primer.")
    ### maybe have this be less if statement dependant
    #  add additional warnings for optimum primer and probe settings
    if (
        st.session_state["primer_opt_size"] < st.session_state["primer_min_size"]
        or st.session_state["primer_opt_size"] > st.session_state["primer_max_size"]
    ):
        st.warning(f"Optimal primer size ({st.session_state['primer_opt_size']}) should be between minimum ({st.session_state['primer_min_size']}) and maximum ({st.session_state['primer_max_size']}) size.")

    if (
        st.session_state["primer_opt_tm"] < st.session_state["primer_min_tm"]
        or st.session_state["primer_opt_tm"] > st.session_state["primer_max_tm"]
    ):
        st.warning(f"Optimal primer Tm ({st.session_state['primer_opt_tm']}) should be between minimum ({st.session_state['primer_min_tm']}) and maximum ({st.session_state['primer_max_tm']}) Tm.")

    if (
        st.session_state["primer_opt_GC"] < st.session_state["primer_min_GC"]
        or st.session_state["primer_opt_GC"] > st.session_state["primer_max_GC"]
    ):
        st.warning(f"Optimal primer GC% ({st.session_state['primer_opt_GC']}) should be between minimum ({st.session_state['primer_min_GC']}) and maximum ({st.session_state['primer_max_GC']}) GC%.")
    if (
        st.session_state["probe_opt_size"] < st.session_state["probe_min_size"]
        or st.session_state["probe_opt_size"] > st.session_state["probe_max_size"]
    ):
        st.warning(f"Optimal probe size ({st.session_state['probe_opt_size']}) should be between minimum ({st.session_state['probe_min_size']}) and maximum ({st.session_state['probe_max_size']}) size.")

    if (
        st.session_state["probe_opt_tm"] < st.session_state["probe_min_tm"]
        or st.session_state["probe_opt_tm"] > st.session_state["probe_max_tm"]
    ):
        st.warning(f"Optimal probe Tm ({st.session_state['probe_opt_tm']}) should be between minimum ({st.session_state['probe_min_tm']}) and maximum ({st.session_state['probe_max_tm']}) Tm.")

    if (
        st.session_state["probe_opt_GC"] < st.session_state["probe_min_GC"]
        or st.session_state["probe_opt_GC"] > st.session_state["probe_max_GC"]
    ):
        st.warning(f"Optimal probe GC% ({st.session_state['probe_opt_GC']}) should be between minimum ({st.session_state['probe_min_GC']}) and maximum ({st.session_state['probe_max_GC']}) GC%.")
        
    # Save input file if requested
    if st.session_state.get("run") and st.session_state.get("save_input_file") and st.session_state.get("input_save_path"):
        resolved_path, exists = resolve_and_check_path(st.session_state.get("input_save_path", ""))
        if not exists:
            parent_dir = os.path.dirname(resolved_path)
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except Exception as e:
                st.error(f"Could not create directory: {parent_dir}. Error: {e}")
        #else:
            #st.info(f"Path exists: {resolved_path}")
            


# === Tab 2: Output ===
with tab2:
    st.title("📄 Primer3 Raw Output")

    if st.session_state.get("run") and st.session_state.get("sequence"):
        # Determine primer task
        primer_task = determine_primer_task(
            st.session_state["pick_left"],
            st.session_state["pick_right"],
            st.session_state["pick_internal"],
            st.session_state["left"],
            st.session_state["right"],
            st.session_state["internal"]
        )

        # Remove SEQUENCE_INTERNAL_OLIGO if not needed
        template_lines = PRIMER3_TEMPLATE.splitlines()
        filtered_lines = []
        for line in template_lines:
            sequence_cleaned = st.session_state["sequence"].replace("\n", "").replace("[", "").replace("]", "")
            if line.startswith("SEQUENCE_TEMPLATE="):
                line = f"SEQUENCE_TEMPLATE={sequence_cleaned}"
            if line.startswith("SEQUENCE_PRIMER=") and st.session_state["pick_left"]:
                continue
            if line.startswith("SEQUENCE_PRIMER_REVCOMP=") and st.session_state["pick_right"]:
                continue
            if line.startswith("SEQUENCE_INTERNAL_OLIGO="):
                # Only keep if the primer_task actually uses a probe
                if st.session_state["pick_internal"] or primer_task not in ["pick_hyb_probe_only", "pick_pcr_primers_and_hyb_probe", "pick_pcr_primers_and_hyb_oligo"
                ]:
                    continue
            filtered_lines.append(line)
        template = "\n".join(filtered_lines)


        #### -> Fill the template with session state values
        ### General settings
        settings_filled = template.format(
            seq_id=st.session_state["seq_id"],
            sequence=sequence_cleaned,
            seq_primer=st.session_state["left"],
            seq_primer_rev=st.session_state["right"],
            seq_internal=st.session_state["internal"],
            target=st.session_state["target"],
            product_size_range=st.session_state["product_size_range"],
            excluded_region=st.session_state["excluded_region"],
            num_return=st.session_state["num_return"],
            max_template_mispriming=st.session_state["max_template_mispriming"],
            pair_max_template_mispriming=st.session_state["pair_max_template_mispriming"],
            max_repeat_mispriming=st.session_state["max_repeat_mispriming"],
            max_3_prime_stability=st.session_state["max_3_prime_stability"],
            pair_max_repeat_mispriming=st.session_state["pair_max_repeat_mispriming"],
            primer_task=primer_task,

        ### General primer picking settings
            primer_min_size=st.session_state["primer_min_size"],
            primer_min_tm=st.session_state["primer_min_tm"],
            product_min_tm=st.session_state["product_min_tm"],
            primer_min_GC=st.session_state["primer_min_GC"],
            primer_opt_size=st.session_state["primer_opt_size"],
            primer_opt_tm=st.session_state["primer_opt_tm"],
            product_opt_tm=st.session_state["product_opt_tm"],
            primer_opt_GC=st.session_state["primer_opt_GC"],
            primer_max_size=st.session_state["primer_max_size"],
            primer_max_tm=st.session_state["primer_max_tm"],
            product_max_tm=st.session_state["product_max_tm"],
            primer_max_GC=st.session_state["primer_max_GC"],
            max_tm_diff=st.session_state["max_tm_diff"],
            thermo_param_value=st.session_state["thermo_param_value"],
            primer_max_self_comp=st.session_state["primer_max_self_comp"],
            max_Ns=st.session_state["max_Ns"],
            primer_inside_target_penalty=st.session_state["primer_inside_target_penalty"],
            primer_first_base_index=st.session_state["primer_first_base_index"],
            primer_salt_conc_monocat=st.session_state["primer_salt_conc_monocat"],
            primer_salt_conc_divcat=st.session_state["primer_salt_conc_divcat"],
            annealing_oligo_conc=st.session_state["annealing_oligo_conc"],
            primer_max_3prime_self_comp=st.session_state["primer_max_3prime_self_comp"],
            max_poly_x=st.session_state["max_poly_x"],
            primer_outside_target_penalty=st.session_state["primer_outside_target_penalty"],
            CG_clamp=st.session_state["CG_clamp"],
            salt_correction_value=st.session_state["salt_correction_value"],
            primer_dntp_conc=st.session_state["primer_dntp_conc"],  
            liberal_base=st.session_state["liberal_base"],


        ### General Probe picking settings
            probe_min_size=st.session_state["probe_min_size"],
            probe_min_tm=st.session_state["probe_min_tm"],
            probe_min_GC=st.session_state["probe_min_GC"],
            probe_opt_size=st.session_state["probe_opt_size"],
            probe_opt_tm=st.session_state["probe_opt_tm"],
            probe_opt_GC=st.session_state["probe_opt_GC"],
            probe_max_size=st.session_state["probe_max_size"],
            probe_max_tm=st.session_state["probe_max_tm"],
            probe_max_GC=st.session_state["probe_max_GC"],
            probe_max_self_comp=st.session_state["probe_max_self_comp"],
            probe_max_Ns=st.session_state["probe_max_Ns"],
            probe_min_seq_qual=st.session_state["probe_min_seq_qual"],
            probe_salt_conc_monocat=st.session_state["probe_salt_conc_monocat"],
            probe_salt_conc_divcat=st.session_state["probe_salt_conc_divcat"],
            probe_max_3prime_self_comp=st.session_state["probe_max_3prime_self_comp"],
            probe_max_poly_x=st.session_state["probe_max_poly_x"],
            probe_DNA_conc=st.session_state["probe_DNA_conc"],
            probe_dntp_conc=st.session_state["probe_dntp_conc"],
            ambiguity_codes_consensus=st.session_state["ambiguity_codes_consensus"],
            lowercase_masking = st.session_state["lowercase_masking"],

        )

        

        # Run Primer3 with temporary settings file
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.txt")
            
            with open(input_path, "w") as f:
                f.write(settings_filled)

            # Save input file to user path if requested
            if st.session_state.get("save_input_file") and st.session_state.get("input_save_path"):
                try:
                    with open(st.session_state["input_save_path"], "w") as f:
                        f.write(settings_filled)
                    st.success(f"Input file saved to: {st.session_state['input_save_path']}")
                except Exception as e:
                    st.error(f"Failed to save input file: {e}")



            try:
                result = subprocess.run(
                    ["primer3_core", input_path],
                    capture_output=True,
                    text=True,
                    check=True
                )
                st.success("Primer3 executed successfully.")
                st.text_area("Primer3 Output", result.stdout, height=300)
                st.session_state["raw_output"] = result.stdout

            except subprocess.CalledProcessError as e:
                st.error("Primer3 execution failed.")
                st.code(e.stderr)
    else:
        st.info("Go to the Input tab, enter your sequence and press 'Run Primer3'.")

output = st.session_state.get("raw_output", "")

# set tab for error information
with tab3:
    st.title("⚠️ Primer3 Warnings")

    minor_warning_detected = False
    error_detected = False
    result_error_detected = False
    no_primers = False


    # --- primer checks
    checks = [
        (
            st.session_state["primer_opt_size"] < st.session_state["primer_min_size"]
            or st.session_state["primer_opt_size"] > st.session_state["primer_max_size"],
            f"Optimal primer size ({st.session_state['primer_opt_size']}) should be between minimum ({st.session_state['primer_min_size']}) and maximum ({st.session_state['primer_max_size']}) size."
        ),
        (
            st.session_state["primer_opt_tm"] < st.session_state["primer_min_tm"]
            or st.session_state["primer_opt_tm"] > st.session_state["primer_max_tm"],
            f"Optimal primer Tm ({st.session_state['primer_opt_tm']}) should be between minimum ({st.session_state['primer_min_tm']}) and maximum ({st.session_state['primer_max_tm']}) Tm."
        ),
        (
            st.session_state["primer_opt_GC"] < st.session_state["primer_min_GC"]
            or st.session_state["primer_opt_GC"] > st.session_state["primer_max_GC"],
            f"Optimal primer GC% ({st.session_state['primer_opt_GC']}) should be between minimum ({st.session_state['primer_min_GC']}) and maximum ({st.session_state['primer_max_GC']}) GC%."
        ),
        (
            st.session_state["probe_opt_size"] < st.session_state["probe_min_size"]
            or st.session_state["probe_opt_size"] > st.session_state["probe_max_size"],
            f"Optimal probe size ({st.session_state['probe_opt_size']}) should be between minimum ({st.session_state['probe_min_size']}) and maximum ({st.session_state['probe_max_size']}) size."
        ),
        (
            st.session_state["probe_opt_tm"] < st.session_state["probe_min_tm"]
            or st.session_state["probe_opt_tm"] > st.session_state["probe_max_tm"],
            f"Optimal probe Tm ({st.session_state['probe_opt_tm']}) should be between minimum ({st.session_state['probe_min_tm']}) and maximum ({st.session_state['probe_max_tm']}) Tm."
        ),
        (
            st.session_state["probe_opt_GC"] < st.session_state["probe_min_GC"]
            or st.session_state["probe_opt_GC"] > st.session_state["probe_max_GC"],
            f"Optimal probe GC% ({st.session_state['probe_opt_GC']}) should be between minimum ({st.session_state['probe_min_GC']}) and maximum ({st.session_state['probe_max_GC']}) GC%."
        ),
    ]

    # loop once
    for condition, message in checks:
        if condition:
            st.warning(message)
            minor_warning_detected = True
    
    # --- set logic for different checks (missing primer seqs, warnings, errors) ---
    no_sequence = not st.session_state.get("sequence", "").strip()
    if no_sequence:
        st.error("No sequence provided. Please enter a DNA sequence in the 'Input Settings' tab.")
    no_left = not st.session_state.get("pick_left", False) and not st.session_state.get("left", "").strip()
    no_right = not st.session_state.get("pick_right", False) and not st.session_state.get("right", "").strip()
    if no_left or no_right:
        st.error("One or both primer sequences are missing and the corresponding 'Pick' option is not selected. Please provide primer sequences or select the 'Pick' option in the 'Input Settings' tab.")
        st.info("Primer3 Output is unavailable until you provide primer information.")
        no_primers = True

    elif st.warning is not None and not output:
        st.info("Run Primer3 to generate output.")
    elif "PRIMER_ERROR" in output:
        error_line = [line for line in output.splitlines() if line.startswith("PRIMER_ERROR=")]
        if error_line:
            st.error("No results generated with the provided design:  \n" +   "\n".join(err.replace("PRIMER_ERROR=", "Primer3 Error: ") for err in error_line))
            error_detected = True

    else:
        st.success("Primer3 has succesfully executed. Check below for potential warnings about the primer / probe design parameters")
        # Extract PRIMER_WARNING lines
        warning_lines = [line for line in output.splitlines() if line.startswith("PRIMER_WARNING=")]
        # Only display if sequence is provided (not picked)
        st.subheader("Problems with primer / probe design parameters with the found / picked oligos:")
        if st.session_state.get("left", "").strip():
            left_warnings = [w for w in warning_lines if "left primer" in w]
            if left_warnings:
                st.write("**Left Primer Warnings:**")
                for w in left_warnings:
                    st.write(w.replace("PRIMER_WARNING=", ""))
                    error_detected = True
        if st.session_state.get("right", "").strip():
            right_warnings = [w for w in warning_lines if "right primer" in w]
            if right_warnings:
                st.write("**Right Primer Warnings:**")
                for w in right_warnings:
                    st.write(w.replace("PRIMER_WARNING=", ""))
                    error_detected = True
        if st.session_state.get("internal", "").strip():
            internal_warnings = [w for w in warning_lines if "internal oligo" in w or "internal oligo" in w]
            if internal_warnings:
                st.write("**Internal Oligo Warnings:**")
                for w in internal_warnings:
                    st.write(w.replace("PRIMER_WARNING=", ""))
                    error_detected = True    
        
        st.write("")
        st.write("")
        st.write("")
        st.subheader("Result specific problems:")
        # check for product size
        range_line = next((line for line in output.splitlines() if line.startswith("PRIMER_PRODUCT_SIZE_RANGE=")), None)
        if range_line:
            range_str = range_line.split("=", 1)[1].strip()
            allowed_ranges = []
            for r in range_str.split():
                try:
                    start, end = map(int, r.split("-"))
                    allowed_ranges.append((start, end))
                except Exception:
                    continue

            # For each result, check product size
            for line in output.splitlines():
                if line.startswith("PRIMER_PAIR_") and "_PRODUCT_SIZE=" in line:
                    parts = line.split("_")
                    idx = int(parts[2])
                    size = int(line.split("=")[1].strip())
                    # Check if size is in any allowed range
                    in_range = any(start <= size <= end for start, end in allowed_ranges)
                    if not in_range:
                        st.write(f"**Result {idx + 1}:**")
                        st.write(f"Product size {size} is outside the allowed range(s): {range_str}")
                        result_error_detected = True
            
            #additionally, for each result, display problems
            problem_lines = [line for line in output.splitlines() if "_PROBLEMS=" in line]
            result_problems = {}
            for line in problem_lines:
                # get the problems per setting
                prefix, problems = line.split("=",1)
                # get the result number
                parts = prefix.split("_")
                if len(parts) >= 3:
                    oligo_type = parts[1].upper()  # LEFT, RIGHT, INTERNAL
                    if oligo_type == "LEFT":
                        oligo_label = "Left Primer"
                    elif oligo_type == "RIGHT":
                        oligo_label = "Right Primer"
                    elif oligo_type =="INTERNAL":
                        oligo_label = "Internal Oligo / Probe"
                    else:
                        oligo_label = oligo_type
                    result_num = int(parts[2])
                    problems = problems.strip()
                    if problems:
                        if result_num not in result_problems:
                            result_problems[result_num] = []
                        result_problems[result_num].append(f"Problem {oligo_label}: {problems}")

            #display problems
            for result_num, problems_list in result_problems.items():
                st.write(f"**Result {result_num + 1}:**")
                for problem in problems_list:
                    st.write(problem)
                    result_error_detected = True
    # red pulse warning
    if error_detected == True or no_primers == True and st.session_state.get("run"):
        st.markdown("""
            <style>
            @keyframes pulse {
                0% { background-color: rgba(255, 0, 0, 0.2); }
                50% { background-color: rgba(255, 0, 0, 0.6); }
                100% { background-color: rgba(255, 0, 0, 0.2); }
            }
            /* third tab button */
            div[data-baseweb="tab-list"] button:nth-child(3) {
                animation: pulse 1.5s infinite;
                border-radius: 5px;
            }
            </style>
        """, unsafe_allow_html=True)
    # yellow pulse warning
    if result_error_detected == True or minor_warning_detected == True and st.session_state.get("run"):
        st.markdown("""
            <style>
            @keyframes pulse {
                0%   { background-color: rgba(255, 255, 0, 0.2); }
                50%  { background-color: rgba(255, 255, 0, 0.6); }
                100% { background-color: rgba(255, 255, 0, 0.2); }
            }
            /* third tab button */
            div[data-baseweb="tab-list"] button:nth-child(3) {
                animation: pulse 1.5s infinite;
                border-radius: 5px;
            }
            </style>
        """, unsafe_allow_html=True)


with tab4:
    st.title("📊 Primer3 Output")
    # Error: No target primer sequences provided and pick is not selected
    no_sequence = not st.session_state.get("sequence", "").strip()
    if no_sequence:
        st.error("No sequence provided. Please enter a DNA sequence in the 'Input Settings' tab.")
    no_left = not st.session_state.get("pick_left", False) and not st.session_state.get("left", "").strip()
    no_right = not st.session_state.get("pick_right", False) and not st.session_state.get("right", "").strip()
    if no_left or no_right:
        st.error("One or both primer sequences are missing and the corresponding 'Pick' option is not selected. Please provide primer sequences or select the 'Pick' option in the 'Input Settings' tab.")
        st.info("Primer3 Output is unavailable until you provide primer information.")
    elif not output:
        st.info("Run Primer3 to generate output.")
    elif "PRIMER_ERROR" in output:
        st.warning("No results generated, see the Primer3 Warnings tab")   

    else:
        # save from the output starting SEQUENCE_TARGET=
        lines = output.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("SEQUENCE_TARGET="):
                lines = lines[i:] 
                break
        # # save lines to txt file
        # with open ("primer3_temp_output.txt", "w") as file:
        #     file.write("\n".join(lines))
        # Find out how many results there are
        num_results = 0
        for line in lines:
            if line.startswith("PRIMER_PAIR_") and "_PENALTY=" in line:
                idx = int(line.split("_")[2])
                num_results = max(num_results, idx + 1)

        # setup result for later export
        all_results_for_export = []        

        # For each result, extract the relevant info
        for idx in range(num_results):
            st.subheader(f"Result {idx+1}")
            row_data = []
            #only include HYB OLIGO if probe is picked or provided
            primer_rows = [
                ("LEFT PRIMER", "PRIMER_LEFT"),
                ("RIGHT PRIMER", "PRIMER_RIGHT"),
            ]
            if st.session_state.get("pick_internal") or st.session_state.get("internal", "").strip():
                primer_rows.append(("HYB OLIGO", "PRIMER_INTERNAL"))

            for label, prefix in primer_rows:
                seq = None
                start = None
                length = None
                tm = None
                gc = None
                any_ = None
                end = None

                for line in lines:
                    if line.startswith(f"{prefix}_{idx}_SEQUENCE="):
                        seq = line.split("=", 1)[1]
                    if line.startswith(f"{prefix}_{idx}="):
                        parts = line.split("=", 1)[1].split(",")
                        if len(parts) == 2:
                            start = parts[0]
                            length = parts[1]
                    if line.startswith(f"{prefix}_{idx}_TM="):
                        tm = line.split("=", 1)[1]
                    if line.startswith(f"{prefix}_{idx}_GC_PERCENT="):
                        gc = line.split("=", 1)[1]
                    if line.startswith(f"{prefix}_{idx}_SELF_ANY="):
                        any_ = line.split("=", 1)[1]
                    if line.startswith(f"{prefix}_{idx}_SELF_END="):
                        end = line.split("=", 1)[1]

                row_data.append({
                    "Type": label,
                    "Start": start,
                    "Len": length,
                    "Tm": tm,
                    "GC%": gc,
                    "Any": any_,
                    "3'": end,
                    "Seq": seq,
                })
            st.dataframe(pd.DataFrame(row_data), use_container_width=True, hide_index=True)

            # product info
            product_data = []

            product_size = None
            self_comp = None
            prime_end = None
            product_tm = None

            #st.subheader(f"Result {idx+1} product info")
            for line in lines:
                if line.startswith(f"PRIMER_PAIR_{idx}_PRODUCT_SIZE="):
                    product_size = line.split("=", 1)[1] 
                if line.startswith(f"PRIMER_PAIR_{idx}_COMPL_ANY="):
                    self_comp = line.split("=", 1)[1]             
                if line.startswith(f"PRIMER_PAIR_{idx}_COMPL_END="):
                    prime_end = line.split("=", 1)[1]
                if line.startswith(f"PRIMER_PAIR_{idx}_PRODUCT_TM"):
                    product_tm = line.split("=", 1)[1]    
                
            product_data.append({
                "Product size": product_size,
                "Product Tm": product_tm,
                "Self complementary": self_comp,
                "3' end complementary": prime_end,
                })
        

            st.dataframe(pd.DataFrame(product_data), use_container_width=True, hide_index=True)


            # Get binding info from output
            left_start, left_len = None, None
            right_start, right_len = None, None
            hyb_start, hyb_len = None, None
            target_start, target_len = None, None
            excluded_start, excluded_len = None, None
            for line in lines:
                if line.startswith(f"PRIMER_LEFT_{idx}="):
                    parts = line.split("=", 1)[1].split(",")
                    if len(parts) == 2:
                        left_start, left_len = int(parts[0]), int(parts[1])
                if line.startswith(f"PRIMER_RIGHT_{idx}="):
                    parts = line.split("=", 1)[1].split(",")
                    if len(parts) == 2:
                        right_start, right_len = int(parts[0]), int(parts[1])
                if line.startswith(f"PRIMER_INTERNAL_{idx}="):
                    parts = line.split("=", 1)[1].split(",")
                    if len(parts) == 2:
                        hyb_start, hyb_len = int(parts[0]), int(parts[1])
                if line.startswith("SEQUENCE_TARGET="):
                    parts = line.split("=", 1)[1].split(",")
                    if len(parts) ==2: 
                        target_start, target_len = int(parts[0]), int(parts[1])
                if line.startswith("EXCLUDED_REGION="):
                    parts = line.split("=", 1)[1].split(",")
                    if len(parts) == 2:
                        excluded_start, excluded_len = int(parts[0]), int(parts[1])         
            
            # prepare sequences for markings
            seq = st.session_state.get("sequence", "").replace("\n", "").replace("[", "").replace("]", "")
            seq_len = len(seq)

            # Prepare marker lines
            marker = [" "]*seq_len
            if left_start is not None and left_len is not None:
                for i in range(left_start, left_start + left_len):
                    if 0 <= i < seq_len:
                        marker[i] = ">"
            if right_start is not None and right_len is not None:
                # Right primer: position is last base, so mark backwards
                for i in range(right_start - right_len + 1, right_start + 1):
                    if 0 <= i < seq_len:
                        marker[i] = "<"
            if hyb_start is not None and hyb_len is not None:
                for i in range(hyb_start, hyb_start + hyb_len):
                    if 0 <= i < seq_len:
                        marker[i] = "^"
            if target_start is not None and target_len is not None:
                for i in range(target_start, target_start + target_len):
                    if 0 <= i < seq_len:
                        marker[i] = "*"
            if excluded_start is not None and excluded_len is not None:
                for i in range(excluded_start, excluded_start + excluded_len):
                    if 0 <= i < seq_len:
                        marker[i] = "X"

            # Split sequence and marker into 60-base rows
            rows = []
            for i in range(0, seq_len, 60):
                seq_row = seq[i:i+60]
                marker_row = "".join(marker[i:i+60])
                rows.append((seq_row, marker_row))

            for idx_row, (seq_row, marker_row) in enumerate(rows):
                # If the first character in marker_row is '>' and the previous row exists, move it to the end of the previous marker_row
                if idx_row > 0 and marker_row[0] == ">":
                    # Convert to list for mutability
                    prev_marker_row = list(rows[idx_row-1][1])
                    prev_marker_row[-1] = ">"
                    rows[idx_row-1] = (rows[idx_row-1][0], "".join(prev_marker_row))
                    # Remove the marker from the current row
                    marker_row = " " + marker_row[1:]
                    rows[idx_row] = (seq_row, marker_row)

            with st.expander("Show binding sites on sequence"):
                block = ""
                for idx_row, (seq_row, marker_row) in enumerate(rows):
                    row_start = idx_row * 60 + 1
                    if idx_row == 0:
                        block += f"\n   {row_start:>3}  {seq_row}\n       {marker_row}\n\n"
                    else:
                        block += f"{row_start:>6}  {seq_row}\n       {marker_row}\n\n"
                block_lines = block.splitlines()
                if block_lines:
                    # Use zero-width space (U+200B) to pad the first line
                    invisible_pad = "\u200B" * 18  # Adjust the number for desired width
                    block_lines[0] = invisible_pad + block_lines[0][2:]  # Remove filler and pad
                block = "\n".join(block_lines)
                st.code(block, language="text")
                
                # add a legend
                legend = (
                    "**Legend:**\n\n"
                    "Forward Primer: `>`\n\n"
                    "Reverse Primer: `<`\n\n"
                    "Probe/Internal Oligo: `^`\n\n"
                    "Target Region: `*`\n\n"
                    "Excluded Region: `X`"
                )
                st.markdown(legend)

            # Add results into variable for later saving
            all_results_for_export.append({
                "primer_table": pd.DataFrame(row_data),
                "product_table": pd.DataFrame(product_data),     
                "sequence_block": rows                      
            })

        
        explain_data = { 
            "LEFT": {},
            "RIGHT": {}, 
            "INTERNAL": {}
        }
        for line in lines:
            if line.startswith("PRIMER_LEFT_EXPLAIN="):
                explain_items = line.split("=", 1)[1].split(", ")
                for item in explain_items:
                    k, v = item.rsplit(" ", 1)
                    explain_data["LEFT"][k] = int(v)
            elif line.startswith("PRIMER_RIGHT_EXPLAIN="):
                explain_items = line.split("=", 1)[1].split(", ")
                for item in explain_items:
                    k, v = item.rsplit(" ", 1)
                    explain_data["RIGHT"][k] = int(v)
            elif line.startswith("PRIMER_INTERNAL_EXPLAIN="):
                explain_items = line.split("=", 1)[1].split(", ")
                for item in explain_items:
                    k, v = item.rsplit(" ", 1)
                    explain_data["INTERNAL"][k] = int(v)

        # 🧾 Build table
        ordered_keys = [
            "considered",
            "too many Ns",
            "in target",
            "in excl region",            
            "GC content failed",
            "no GC clamp",
            "low tm",
            "high tm",
            "high any compl" ,           
            "high end compl",
            "long poly-x seq",
            "high 3' stability",
            "ok",

        ]

        df_explain = pd.DataFrame(index=ordered_keys)
        columns_to_include = [
            ("LEFT", "pick_left", "left"),
            ("RIGHT", "pick_right", "right"),
        ]

        # Only add INTERNAL if probe is picked or provided
        if st.session_state.get("pick_internal") or st.session_state.get("internal", "").strip():
            columns_to_include.append(("INTERNAL", "pick_internal", "internal"))

        for col, pick_key, seq_key in columns_to_include:
            # If not picked but sequence is provided, fill with text string like "provided"
            if not st.session_state.get(pick_key) and st.session_state.get(seq_key, "").strip():
                df_explain[col] = ["provided"] * len(ordered_keys)
            else:
                df_explain[col] = [explain_data[col].get(k, 0) for k in ordered_keys]

        explanation_summary_df = df_explain

        # 📊 Show table
        st.subheader("Oligo Explanation Summary")
        st.table(explanation_summary_df)

        pair_explain_text = ""
        for line in lines:
            if line.startswith("PRIMER_PAIR_EXPLAIN="):
                pair_explain_text = line.replace("PRIMER_PAIR_EXPLAIN=", "")
                break

        if pair_explain_text:
            st.markdown(f"**Primer Pair Statistics:** {pair_explain_text}")


        st.subheader("📥 Export Primer3 Results")
        format_option = st.selectbox("Choose download format:", ["Select format", "HTML", "PDF"], key="export_format")

        if format_option != "Select format" and all_results_for_export:
            #set file name
            file_name_input = st.text_input("Enter file name (without extentions like .pdf or .html)", value = "primer3_results")
            #generate html report contents
            html_report = generate_full_html_report(all_results_for_export, explanation_summary_df=explanation_summary_df, pair_explain_text=pair_explain_text, seq_id=seq_id)
            # handle html and pdf download
            if format_option == "HTML":
                st.download_button(
                    label="Download as HTML",
                    data=html_report.encode("utf-8"),
                    file_name=f"{file_name_input.strip() or 'primer3_results'}.html",
                    mime="text/html"
                )
            elif format_option == "PDF":
                pdf_bytes = generate_pdf_reportlab(all_results_for_export, explanation_summary_df, pair_explain_text)
                if pdf_bytes:
                    st.download_button(
                        label="Download as PDF",
                        data=pdf_bytes,
                        file_name=f"{file_name_input.strip() or 'primer3_results'}.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.error("Failed to generate PDF.")

