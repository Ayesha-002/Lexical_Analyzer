import streamlit as st
import pandas as pd
import re
from streamlit_ace import st_ace

# Page config
st.set_page_config(page_title="Lexical Analyzer", layout="wide")

# Styling for main heading, containers and footer section
st.markdown("""
<style>
.main-title {
    text-align: center;
    font-size: 50px;
    font-weight: bold;
}
.stApp {
    text-align: left;
}
.footer-container {
    text-align: center;
    font-size: 17px;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">Lexical Analyzer</div>', unsafe_allow_html=True)

# Tokens definition
KEYWORDS = {"int", "float", "double", "char", "if", "else", "for", "while", "return", "void"}
DATA_TYPE_KEYWORDS = {"int", "float", "double", "char", "void"}
OPERATORS = {"+", "-", "*", "/", "%", "=", "<", ">", "==", "!=", "<=", ">="}
SEPARATORS = {";", ",", "(", ")", "{", "}", "[", "]"}

# Default code in code section
DEFAULT_CODE = """// Sample program for lexical analysis

int main() {
    int a = 10;
    float b = 20.5;
    char c@ = 'x';
}
"""

# Initialize session state for source code input if not already present
if "source_code_input" not in st.session_state:
    st.session_state["source_code_input"] = DEFAULT_CODE

# Unique counter for st_ace component key to force reset on clear
if "editor_counter" not in st.session_state:
    st.session_state["editor_counter"] = 0


def clear_text():
    st.session_state["source_code_input"] = ""
    st.session_state["editor_counter"] += 1


def strip_inline_comment(line):
    in_string = False
    in_char = False
    i = 0
    while i < len(line) - 1:
        ch = line[i]
        if ch == '"' and not in_char:
            in_string = not in_string
        elif ch == "'" and not in_string:
            in_char = not in_char
        elif ch == "/" and line[i + 1] == "/" and not in_string and not in_char:
            return line[:i]
        i += 1
    return line

# Lexical analyzer Engine
def lexical_analyzer(code):

    tokens = []
    symbol_table = []
    errors = []

    symbol_lookup = {}  
    pending_type = None

    # Regular expression patterns for defining token boundaries and lexical rules
    pattern = r'''
        (?P<UNCLOSED_STRING>"[^"\n]*) |
        (?P<STRING>"[^"]*") |
        (?P<INVALID_CHAR_LITERAL>'[^'\n]{2,}') |
        (?P<CHARACTER>'[^'\n]') |
        (?P<MALFORMED_FLOAT>\d+\.\d+\.\d+[.\d]*) |
        (?P<FLOAT>\d+\.\d+) |
        (?P<INTEGER>\d+) |
        (?P<OPERATOR>==|!=|<=|>=|[+\-*/%=<>]) |
        (?P<SEPARATOR>[;,(){}\[\]]) |
        (?P<INVALID_ID>[A-Za-z_][A-Za-z0-9_]*[@#$%!^&~`]+[A-Za-z0-9_@#$%!^&~`]*|[A-Za-z0-9_]*[@#$%!^&~`]+[A-Za-z0-9_@#$%!^&~`]*|[0-9]+[A-Za-z_]+[A-Za-z0-9_]*) |
        (?P<VALID_ID>[A-Za-z_][A-Za-z0-9_]*) |
        (?P<UNKNOWN>[^\s])
    '''

    # Split code into individual lines for analysis
    lines = code.split('\n')

    for line_idx, raw_line in enumerate(lines, start=1):
        # Remove inline comments before processing the line content
        line_content = strip_inline_comment(raw_line)

        stripped = line_content.strip()
        if not stripped:
            continue

        # Find all regex matches within the current line
        matches = re.finditer(pattern, line_content, re.VERBOSE)

        for match in matches:
            kind = match.lastgroup
            value = match.group(kind)

            if value is None or value.isspace():
                continue

            # Process matched token type and handle classification
            if kind == "UNCLOSED_STRING":
                errors.append([value, "Unterminated String", line_idx])

            elif kind == "STRING":
                tokens.append([line_idx, "STRING", value])

            elif kind == "INVALID_CHAR_LITERAL":
                errors.append([value, "Invalid Character Literal", line_idx])

            elif kind == "CHARACTER":
                tokens.append([line_idx, "CHARACTER_LITERAL", value])

            elif kind == "MALFORMED_FLOAT":
                errors.append([value, "Malformed Number", line_idx])

            elif kind == "FLOAT":
                tokens.append([line_idx, "FLOAT", value])

            elif kind == "INTEGER":
                tokens.append([line_idx, "INTEGER", value])

            elif kind == "OPERATOR":
                tokens.append([line_idx, "OPERATOR", value])

            elif kind == "SEPARATOR":
                tokens.append([line_idx, "SEPARATOR", value])
                # End of a statement -> stop associating identifiers with pending_type
                if value == ";":
                    pending_type = None

            elif kind == "INVALID_ID":
                errors.append([value, "Invalid Identifier", line_idx])

            elif kind == "VALID_ID":
                # Check if the identifier is a reserved keyword
                if value in KEYWORDS:
                    tokens.append([line_idx, "KEYWORD", value])
                    if value in DATA_TYPE_KEYWORDS:
                        pending_type = value
                else:
                    # Treat as a regular identifier and add to symbol table if new
                    tokens.append([line_idx, "IDENTIFIER", value])
                    if value not in symbol_lookup:
                        symbol_lookup[value] = len(symbol_table)
                        symbol_table.append([
                            value,
                            pending_type if pending_type else "Unknown",
                            line_idx
                        ])
            elif kind == "UNKNOWN":
                errors.append([value, "Unknown Token", line_idx])

    return tokens, symbol_table, errors

# File-based input section
st.subheader("Source Code Input:")
uploaded_file = st.file_uploader(
    "Upload a source file:",
    type=["c", "cpp", "txt"]
)

# Handle uploaded file stream and extract code text
if uploaded_file is not None:
    try:
        file_text = uploaded_file.read().decode("utf-8")
        st.session_state["source_code_input"] = file_text
        st.success(f"Loaded '{uploaded_file.name}' into the editor below.")
    except UnicodeDecodeError:
        st.error("Could not read the file. Please upload a plain text source file.")

# Text editor configuration using Streamlit Ace with dynamic combined key string
code = st_ace(
    value=st.session_state["source_code_input"],
    language="c_cpp",
    theme="monokai",
    show_gutter=True,
    auto_update=True,
    key=f"editor_{st.session_state['editor_counter']}"
)

st.session_state["source_code_input"] = code

# Action control alignment layout for buttons
b1, b2, _ = st.columns([1.2, 1.2, 6])

with b1:
    run = st.button("Analyze Code", type="primary", use_container_width=True)

with b2:
    st.button("Clear Code", on_click=clear_text, use_container_width=True)

# Output Dashboard Execution Block
if run and code and code.strip():

    # Execute lexical analysis on current editor code
    tokens, symbols, errors = lexical_analyzer(code)
    st.success("Analysis Completed Successfully")
    st.markdown("---")

    # Metrics Summary Widgets for dashboard overview
    c1, c2, c3 = st.columns(3)
    c1.metric("Tokens Passed", len(tokens))
    c2.metric("Identifiers Tracked", len(symbols))
    c3.metric("Errors Intercepted", len(errors))
    st.markdown("---")

    col_out1, col_out2 = st.columns([1.2, 1])

    # Display Token Table and Token Stream output
    with col_out1:
        st.subheader("Token Table")
        if tokens:
            st.dataframe(pd.DataFrame(tokens, columns=["Line", "Type", "Token"]), use_container_width=True, height=300)
        else:
            st.info("No valid tokens processed.")

        st.subheader("Token Stream")
        if tokens:
            st.code(" ".join([f"<{t[1]}, {t[2]}>" for t in tokens]), wrap_lines=True)
        else:
            st.info("Empty token stream matrix.")

    # Display Symbol Table and Error Table output
    with col_out2:
        st.subheader("Symbol Table")
        if symbols:
            st.dataframe(
                pd.DataFrame(symbols, columns=["Identifier", "Data Type", "Line"]),
                use_container_width=True,
                height=230
            )
        else:
            st.info("Symbol Table is clear.")

        st.subheader("Error Table")
        if errors:
            st.dataframe(pd.DataFrame(errors, columns=["Lexeme", "Error Type", "Line"]), use_container_width=True, height=200)
        else:
            st.success("No Errors Found!")

    # Internal working documentation section
    st.markdown("---")
    st.subheader("Internal Working")
    st.markdown("""
    1. The user enters code or uploads a file.
    2. The system reads the source code.
    3. The code is broken into small parts called tokens.
    4. Each token is identified (keyword, number, operator, etc.).
    5. Variables are stored in the symbol table along with their declared data type and line number.
    6. Invalid characters are detected and shown as errors.
    7. The final result is displayed in the GUI.
    """)
    st.code("""
    Input → Tokenization → Classification → Symbol Table → Error Detection → Output GUI
    """)
elif run:
    st.warning("Input window is currently empty! Please type or paste your source snippets first.")

# Footer section
st.markdown("---")
st.markdown("""
<div class="footer-container">
    <h4 style='margin-bottom: 2px;'>Project Developed By</h4>
    <p style='margin:2px;'><b>Malaika Faiz</b> (FA22-BSCS-0178)</p>
    <p style='margin:2px;'><b>Ayesha Rauf</b> (FA22-BSCS-0206)</p>
</div>
""", unsafe_allow_html=True)