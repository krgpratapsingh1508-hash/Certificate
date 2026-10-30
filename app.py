"""Certificate Maker - apna certificate upload karo, Excel ke naam uspar likho.
Run:  streamlit run app.py
"""
import io
import re
import zipfile

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

FONTS = ["DejaVuSerif-Bold.ttf", "DejaVuSerif.ttf", "LiberationSerif-Bold.ttf", "Georgia Bold.ttf", "timesbd.ttf"]


def get_font(size, font_bytes=None):
    size = max(int(size), 8)
    if font_bytes:
        try:
            return ImageFont.truetype(io.BytesIO(font_bytes), size)
        except OSError:
            pass
    for name in FONTS:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def default_template():
    """Jab tak apna certificate upload nahi hota, ye plain design dikhta hai."""
    img = Image.new("RGB", (1600, 1131), "#fffdf7")
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, 1560, 1091], outline="#1f5f5b", width=16)
    d.rectangle([75, 75, 1525, 1056], outline="#b8892b", width=4)
    d.text((800, 260), "Certificate of Achievement", font=get_font(80), fill="#1f5f5b", anchor="mm")
    d.text((800, 400), "Yahan apna certificate upload karo", font=get_font(36), fill="#777777", anchor="mm")
    return img


def read_names(file):
    name = getattr(file, "name", "").lower()
    df = pd.read_csv(file) if name.endswith(".csv") else pd.read_excel(file)
    df.columns = [str(c).strip() for c in df.columns]
    col = next((c for c in df.columns if c.lower() == "name"), None)
    if col is None:
        raise ValueError("Excel me 'Name' naam ka column hona chahiye (pehli row me header).")
    if col != "Name":
        df = df.rename(columns={col: "Name"})
    df = df.fillna("")
    return df[df["Name"].astype(str).str.strip() != ""].reset_index(drop=True)


def fill(text, row):
    lower = {str(k).lower(): v for k, v in row.items()}
    return re.sub(r"\{([^}]+)\}", lambda m: str(lower.get(m.group(1).strip().lower(), "")), text)


def put_text(img, text, x_pct, y_pct, size_pct, color, font_bytes):
    """Text ko (x%, y%) par beech me likhta hai. Lamba ho to khud chhota ho jata hai."""
    w, h = img.size
    d = ImageDraw.Draw(img)
    size = size_pct / 100 * h
    f = get_font(size, font_bytes)
    while d.textlength(text, font=f) > w * 0.9 and size > 12:
        size -= 4
        f = get_font(size, font_bytes)
    d.text((w * x_pct / 100, h * y_pct / 100), text, font=f, fill=color, anchor="mm")


def make_certificate(template, row, cfg):
    img = template.copy()
    put_text(img, str(row["Name"]).strip(), cfg["nx"], cfg["ny"], cfg["ns"], cfg["nc"], cfg["font"])
    extra = fill(cfg["extra"], row).strip()
    if extra:
        put_text(img, extra, cfg["ex"], cfg["ey"], cfg["es"], cfg["ec"], cfg["font"])
    return img


def safe(s):
    return re.sub(r"[^\w\- ]+", "", str(s)).strip()[:60] or "certificate"


@st.cache_data(show_spinner="Certificates ban rahe hain...")
def build_all(template_bytes, df, cfg):
    template = Image.open(io.BytesIO(template_bytes)).convert("RGB")
    imgs = [make_certificate(template, r, cfg) for r in df.to_dict("records")]
    pdf = io.BytesIO()
    imgs[0].save(pdf, format="PDF", save_all=True, append_images=imgs[1:], resolution=150)
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        for i, (im, n) in enumerate(zip(imgs, df["Name"]), 1):
            b = io.BytesIO()
            im.save(b, format="PNG")
            z.writestr(f"{i:03d}-{safe(n)}.png", b.getvalue())
    return pdf.getvalue(), zbuf.getvalue()


def sample_excel():
    b = io.BytesIO()
    pd.DataFrame({"Name": ["Aarav Sharma", "Priya Verma", "Rohan Patel"],
                  "Course": ["Web Development", "Data Analysis", "Digital Marketing"]}).to_excel(b, index=False)
    return b.getvalue()


# ---------------------------- Web page ----------------------------
st.set_page_config(page_title="Certificate Maker", page_icon="🎓", layout="wide")
st.title("Certificate Maker")
st.caption("Apna certificate aur Excel upload karo. Har naam certificate par likh kar mil jayega.")

left, right = st.columns([1, 1.5])
with left:
    tpl = st.file_uploader("1. Apna certificate (PNG / JPG)", type=["png", "jpg", "jpeg"])
    up = st.file_uploader("2. Excel / CSV (Name column zaroori)", type=["xlsx", "xls", "csv"])
    st.download_button("Sample Excel download karo", sample_excel(), "sample-names.xlsx")

    st.subheader("3. Naam kahan likhna hai")
    nx = st.slider("Left-Right", 0, 100, 50, help="0 = sabse left, 100 = sabse right")
    ny = st.slider("Upar-Neeche", 0, 100, 50, help="0 = sabse upar, 100 = sabse neeche")
    ns = st.slider("Naam ka size", 2.0, 20.0, 8.0, 0.5)
    nc = st.color_picker("Naam ka colour", "#111111")

    with st.expander("Extra text (jaise course ya date) - optional"):
        extra = st.text_input("Text ({Course} jaise Excel column use kar sakte ho)", "")
        ex = st.slider("Extra: Left-Right", 0, 100, 50)
        ey = st.slider("Extra: Upar-Neeche", 0, 100, 62)
        es = st.slider("Extra: size", 1.0, 10.0, 3.5, 0.5)
        ec = st.color_picker("Extra: colour", "#333333")

    font_file = st.file_uploader("Apna font (.ttf) - optional, Hindi naam ke liye zaroori", type=["ttf", "otf"])

cfg = dict(nx=nx, ny=ny, ns=ns, nc=nc, extra=extra, ex=ex, ey=ey, es=es, ec=ec,
           font=font_file.getvalue() if font_file else None)

if tpl:
    tpl_bytes = tpl.getvalue()
    template = Image.open(io.BytesIO(tpl_bytes)).convert("RGB")
else:
    template = default_template()
    buf = io.BytesIO()
    template.save(buf, format="PNG")
    tpl_bytes = buf.getvalue()

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
        st.image(make_certificate(template, df.iloc[i].to_dict(), cfg), use_container_width=True)
        pdf, zp = build_all(tpl_bytes, df, cfg)
        st.download_button("PDF download (sab ek file me)", pdf, "certificates.pdf", "application/pdf")
        st.download_button("ZIP download (PNG images)", zp, "certificates.zip", "application/zip")
    else:
        st.info("Preview dekhne ke liye Excel upload karo. Neeche sample naam se dikh raha hai.")
        st.image(make_certificate(template, {"Name": "Aarav Sharma", "Course": "Web Development"}, cfg),
                 use_container_width=True)
