"""Web UI. Run:  streamlit run app.py"""
import streamlit as st
from generator import DEFAULTS, build_all, make_certificate, read_names, sample_excel_bytes

@st.cache_data(show_spinner="Certificates ban rahe hain...")
def cached_build(df, opts):
    return build_all(df, **opts)


st.set_page_config(page_title="Certificate Maker", page_icon="🎓", layout="wide")
st.title("Certificate Maker")
st.caption("Excel upload karo, har naam ka certificate download karo.")

left, right = st.columns([1, 1.6])
with left:
    up = st.file_uploader("Excel / CSV (Name column zaroori)", type=["xlsx", "xls", "csv"])
    st.download_button("Sample Excel download karo", sample_excel_bytes(), "sample-names.xlsx")
    opts = dict(
        org=st.text_input("Organisation", DEFAULTS["org"]),
        title=st.text_input("Title", DEFAULTS["title"]),
        pre=st.text_input("Naam ke upar ka text", DEFAULTS["pre"]),
        body=st.text_area("Naam ke neeche ka text ({Column} use kar sakte ho)", DEFAULTS["body"]),
        date=st.text_input("Date", DEFAULTS["date"]),
        signer=st.text_input("Signer", DEFAULTS["signer"]),
        role=st.text_input("Designation", DEFAULTS["role"]),
        main=st.color_picker("Main colour", DEFAULTS["main"]),
        accent=st.color_picker("Accent colour", DEFAULTS["accent"]),
    )

df = None
if up:
    try:
        df = read_names(up)
    except Exception as e:
        st.error(str(e))

with right:
    if df is not None and len(df):
        st.success(f"{len(df)} naam mile")
        i = st.number_input("Preview number", 1, len(df), 1) - 1
        st.image(make_certificate(df.iloc[i].to_dict(), **opts), use_container_width=True)
        pdf, zp = cached_build(df, opts)
        st.download_button("PDF download (sab ek file me)", pdf, "certificates.pdf", "application/pdf")
        st.download_button("ZIP download (PNG images)", zp, "certificates.zip", "application/zip")
    else:
        st.info("Preview ke liye pehle Excel upload karo.")
        st.image(make_certificate({"Name": "Aarav Sharma", "Course": "Web Development"}, **opts),
                 use_container_width=True)
