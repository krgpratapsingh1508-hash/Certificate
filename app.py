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


DESIGNS = {
    "Modern Indigo": dict(bg="#ffffff", main="#232670", accent="#f2a900"),
    "Classic Gold": dict(bg="#fffdf6", main="#6b4e0f", accent="#c9a227"),
    "Fresh Green": dict(bg="#f8fbf8", main="#14532d", accent="#2f9e5b"),
}


def make_template(style, W=1600, H=1131):
    """Built-in certificate. Naam wali jagah (beech me) khali chhodi gayi hai."""
    c = DESIGNS[style]
    img = Image.new("RGB", (W, H), c["bg"])
    d = ImageDraw.Draw(img)
    cx = W // 2
    if style == "Modern Indigo":
        d.rectangle([0, 0, 70, H], fill=c["main"])
        d.rectangle([70, 0, 82, H], fill=c["accent"])
        d.rectangle([W - 24, 0, W, H], fill=c["main"])
    elif style == "Classic Gold":
        d.rectangle([40, 40, W - 40, H - 40], outline=c["main"], width=14)
        d.rectangle([72, 72, W - 72, H - 72], outline=c["accent"], width=4)
        for x, y in [(72, 72), (W - 72, 72), (72, H - 72), (W - 72, H - 72)]:
            d.regular_polygon((x, y, 26), 4, rotation=45, fill=c["accent"])
    else:
        d.rectangle([0, 0, W, 56], fill=c["main"])
        d.rectangle([0, H - 56, W, H], fill=c["main"])
        d.rectangle([110, 110, W - 110, H - 100], outline=c["accent"], width=3)
    d.text((cx, 230), "CERTIFICATE", font=get_font(104), fill=c["main"], anchor="mm")
    d.text((cx, 322), "O F   A C H I E V E M E N T", font=get_font(30), fill=c["accent"], anchor="mm")
    d.line([cx - 90, 375, cx + 90, 375], fill=c["accent"], width=4)
    d.text((cx, 450), "This certificate is proudly awarded to", font=get_font(34), fill="#555555", anchor="mm")
    d.line([cx - 420, 640, cx + 420, 640], fill=c["main"], width=3)
    d.text((cx, 705), "for outstanding performance, dedication and excellence.", font=get_font(32), fill="#555555", anchor="mm")
    d.line([220, 940, 520, 940], fill="#777777", width=2)
    d.text((370, 975), "Date", font=get_font(26), fill="#555555", anchor="mm")
    d.line([W - 520, 940, W - 220, 940], fill="#777777", width=2)
    d.text((W - 370, 975), "Signature", font=get_font(26), fill="#555555", anchor="mm")
    d.ellipse([cx - 68, 868, cx + 68, 1004], fill=c["accent"])
    d.ellipse([cx - 54, 882, cx + 54, 990], outline=c["bg"], width=4)
    d.regular_polygon((cx, 936, 30), 5, rotation=0, fill=c["bg"])
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
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap');
html, body, .stApp, .stApp button, .stApp input, .stApp textarea { font-family:'Plus Jakarta Sans',sans-serif; }
.stApp { background:#f4f5fa; color:#1d2040; }
.stApp label, .stApp p, .stApp li, .stApp h2, .stApp h3 { color:#1d2040; }
header[data-testid="stHeader"] { background:transparent; }
.block-container { padding-top:1.2rem; max-width:1200px; }
.hero { background:#232670; border-bottom:6px solid #f2a900; border-radius:16px; padding:26px 28px; margin-bottom:18px; }
.hero h1 { margin:0; padding:0; font-size:2rem; font-weight:800; color:#fff !important; }
.hero p { margin:6px 0 0; font-size:1.02rem; color:#dfe1ff !important; }
[data-testid="stVerticalBlockBorderWrapper"] { background:#fff; border-radius:14px; border-color:#e1e3f0; }
.step { display:flex; align-items:center; gap:10px; font-weight:800; font-size:1.05rem; margin:2px 0 8px; color:#232670; }
.step b { background:#232670; color:#fff; width:28px; height:28px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-size:.9rem; }
[data-testid="stImage"] img { border-radius:8px; box-shadow:0 6px 24px rgba(35,38,112,.18); }
.stDownloadButton button { background:#f2a900; color:#1d2040; border:0; border-radius:10px; font-weight:800; padding:.6rem 1rem; width:100%; }
.stDownloadButton button:hover { background:#ffbc1f; color:#1d2040; }
.stDownloadButton button p { color:#1d2040 !important; }
</style>
<div class="hero"><h1>Certificate Maker</h1>
<p>Excel me naam daalo. Har naam ka certificate ek click me PDF ya images me.</p></div>
""", unsafe_allow_html=True)


def step(n, text):
    st.markdown(f'<div class="step"><b>{n}</b>{text}</div>', unsafe_allow_html=True)


left, right = st.columns([1, 1.5], gap="large")
with left:
    with st.container(border=True):
        step(1, "Certificate chuno")
        style = st.selectbox("Taiyaar design", list(DESIGNS))
        tpl = st.file_uploader("Ya apna certificate upload karo (PNG / JPG)", type=["png", "jpg", "jpeg"])
    with st.container(border=True):
        step(2, "Naam wali Excel")
        up = st.file_uploader("Excel / CSV, pehla column header 'Name'", type=["xlsx", "xls", "csv"])
        st.download_button("Sample Excel download karo", sample_excel(), "sample-names.xlsx")
    with st.container(border=True):
        step(3, "Naam ki jagah set karo")
        nx = st.slider("Left - Right", 0, 100, 50, help="0 = sabse left, 100 = sabse right")
        ny = st.slider("Upar - Neeche", 0, 100, 50, help="0 = sabse upar, 100 = sabse neeche")
        ns = st.slider("Naam ka size", 2.0, 20.0, 8.0, 0.5)
        nc = st.color_picker("Naam ka colour", "#111111")
        with st.expander("Extra text (course, date) - optional"):
            extra = st.text_input("Text ({Course} jaise Excel column use kar sakte ho)", "")
            ex = st.slider("Extra: Left - Right", 0, 100, 50)
            ey = st.slider("Extra: Upar - Neeche", 0, 100, 74)
            es = st.slider("Extra: size", 1.0, 10.0, 3.5, 0.5)
            ec = st.color_picker("Extra: colour", "#333333")
        font_file = st.file_uploader("Apna font (.ttf), Hindi naam ke liye", type=["ttf", "otf"])

cfg = dict(nx=nx, ny=ny, ns=ns, nc=nc, extra=extra, ex=ex, ey=ey, es=es, ec=ec,
           font=font_file.getvalue() if font_file else None)

if tpl:
    template = Image.open(io.BytesIO(tpl.getvalue())).convert("RGB")
else:
    template = make_template(style)
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
    with st.container(border=True):
        step(4, "Preview aur download")
        if df is not None and len(df):
            st.success(f"{len(df)} naam mile")
            i = st.number_input("Kaun sa certificate dekhna hai", 1, len(df), 1) - 1
            st.image(make_certificate(template, df.iloc[i].to_dict(), cfg), use_container_width=True)
            pdf, zp = build_all(tpl_bytes, df, cfg)
            c1, c2 = st.columns(2)
            c1.download_button("PDF download", pdf, "certificates.pdf", "application/pdf")
            c2.download_button("ZIP download (PNG)", zp, "certificates.zip", "application/zip")
        else:
            st.info("Excel upload karo. Abhi sample naam se preview dikh raha hai.")
            st.image(make_certificate(template, {"Name": "Aarav Sharma", "Course": "Web Development"}, cfg),
                     use_container_width=True)
