"""Certificate Maker - ek hi file. Run:  streamlit run app.py"""
import io
import re
import zipfile
from datetime import date

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

W, H = 1600, 1131  # A4 landscape ratio

DEFAULTS = dict(
    org="Your Organisation",
    title="Certificate of Achievement",
    pre="This certificate is proudly presented to",
    body="for successfully completing the {Course} programme with dedication and excellence.",
    date=date.today().strftime("%d %B %Y"),
    signer="Authorised Signatory",
    role="Director",
    main="#1f5f5b",
    accent="#b8892b",
)

# Put your own .ttf files in a "fonts" folder to override (e.g. fonts/regular.ttf)
FONT_CANDIDATES = {
    "regular": ["fonts/regular.ttf", "Georgia.ttf", "DejaVuSerif.ttf", "LiberationSerif-Regular.ttf", "times.ttf"],
    "bold": ["fonts/bold.ttf", "Georgia Bold.ttf", "DejaVuSerif-Bold.ttf", "LiberationSerif-Bold.ttf", "timesbd.ttf"],
    "italic": ["fonts/italic.ttf", "Georgia Italic.ttf", "DejaVuSerif-Italic.ttf", "LiberationSerif-Italic.ttf", "timesi.ttf"],
}


def font(kind, size):
    for name in FONT_CANDIDATES[kind]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def read_names(file):
    """Read .xlsx/.xls/.csv (path or uploaded file). Needs a 'Name' column."""
    name = getattr(file, "name", str(file)).lower()
    df = pd.read_csv(file) if name.endswith(".csv") else pd.read_excel(file)
    df.columns = [str(c).strip() for c in df.columns]
    col = next((c for c in df.columns if c.lower() == "name"), None)
    if col is None:
        raise ValueError("Excel me 'Name' naam ka column hona chahiye (pehli row me header).")
    if col != "Name":
        df = df.rename(columns={col: "Name"})
    df = df.fillna("")
    df = df[df["Name"].astype(str).str.strip() != ""]
    return df.reset_index(drop=True)


def fill(text, row):
    lower = {str(k).lower(): v for k, v in row.items()}
    return re.sub(r"\{([^}]+)\}", lambda m: str(lower.get(m.group(1).strip().lower(), "")), text)


def wrap(draw, text, fnt, max_w):
    lines, cur = [], ""
    for word in text.split():
        t = f"{cur} {word}".strip()
        if draw.textlength(t, font=fnt) > max_w and cur:
            lines.append(cur)
            cur = word
        else:
            cur = t
    return lines + ([cur] if cur else [])


def make_certificate(row, **opts):
    o = {**DEFAULTS, **opts}
    img = Image.new("RGB", (W, H), "#fffdf7")
    d = ImageDraw.Draw(img)
    cx = W // 2

    d.rectangle([40, 40, W - 40, H - 40], outline=o["main"], width=18)
    d.rectangle([75, 75, W - 75, H - 75], outline=o["accent"], width=4)

    d.text((cx, 185), o["org"].upper(), font=font("bold", 30), fill=o["accent"], anchor="ms")
    d.text((cx, 300), o["title"], font=font("bold", 80), fill=o["main"], anchor="ms")
    d.line([cx - 140, 335, cx + 140, 335], fill=o["accent"], width=3)
    d.text((cx, 420), o["pre"], font=font("italic", 32), fill="#444444", anchor="ms")

    # Name (auto-shrinks if long)
    name, size = str(row["Name"]).strip(), 100
    f = font("italic", size)
    while d.textlength(name, font=f) > W - 300 and size > 40:
        size -= 6
        f = font("italic", size)
    d.text((cx, 550), name, font=f, fill="#111111", anchor="ms")
    d.line([cx - 380, 580, cx + 380, 580], fill="#999999", width=2)

    bf = font("regular", 34)
    for i, line in enumerate(wrap(d, fill(o["body"], row), bf, W - 420)[:4]):
        d.text((cx, 670 + i * 50), line, font=bf, fill="#333333", anchor="ms")

    # Date + signer
    d.line([180, 930, 500, 930], fill="#666666", width=2)
    d.text((340, 917), o["date"], font=font("regular", 28), fill="#333333", anchor="ms")
    d.text((340, 968), "Date", font=font("regular", 24), fill="#333333", anchor="ms")
    d.line([W - 500, 930, W - 180, 930], fill="#666666", width=2)
    d.text((W - 340, 965), o["signer"], font=font("bold", 28), fill="#333333", anchor="ms")
    d.text((W - 340, 998), o["role"], font=font("regular", 24), fill="#333333", anchor="ms")

    # Seal
    d.ellipse([cx - 62, 873, cx + 62, 997], fill=o["accent"])
    d.ellipse([cx - 50, 885, cx + 50, 985], outline="#fffdf7", width=3)
    d.text((cx, 935), "CERTIFIED", font=font("bold", 15), fill="#fffdf7", anchor="mm")
    return img


def safe(s):
    return re.sub(r"[^\w\- ]+", "", str(s)).strip()[:60] or "certificate"


def build_all(df, **opts):
    """Returns (pdf_bytes, zip_bytes) for every row in df."""
    imgs = [make_certificate(r, **opts) for r in df.to_dict("records")]
    pdf = io.BytesIO()
    imgs[0].save(pdf, format="PDF", save_all=True, append_images=imgs[1:], resolution=150)
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        for i, (im, n) in enumerate(zip(imgs, df["Name"]), 1):
            b = io.BytesIO()
            im.save(b, format="PNG")
            z.writestr(f"{i:03d}-{safe(n)}.png", b.getvalue())
    return pdf.getvalue(), zbuf.getvalue()


def sample_excel_bytes():
    b = io.BytesIO()
    pd.DataFrame({"Name": ["Aarav Sharma", "Priya Verma", "Rohan Patel"],
                  "Course": ["Web Development", "Data Analysis", "Digital Marketing"]}).to_excel(b, index=False)
    return b.getvalue()


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
