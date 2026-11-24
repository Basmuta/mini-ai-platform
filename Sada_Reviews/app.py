from pathlib import Path
import re
import torch
import pandas as pd
import plotly.express as px
import streamlit as st
from transformers import AutoTokenizer, AutoModelForSequenceClassification

BASE = Path(__file__).parent
DATA_PATH = BASE / "data" / "sample_reviews.csv"
MODEL_DIR = BASE / "models" / "sada_camelbert_finetuned"
CATEGORY_NAMES = {
    "login_issue": "تسجيل الدخول", "crash": "أعطال التطبيق",
    "performance": "الأداء والسرعة", "payment": "الدفع والفواتير",
    "usability": "سهولة الاستخدام", "feature_request": "اقتراح ميزة",
    "positive_experience": "تجربة إيجابية",
}

def normalize_text(text):
    text = str(text).strip()
    text = re.sub(r"[إأآا]", "ا", text)
    text = re.sub(r"ى", "ي", text)
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", " [EMAIL] ", text)
    text = re.sub(r"(?<!\d)(?:05\d{8}|\+9665\d{8})(?!\d)", " [PHONE] ", text)
    return re.sub(r"\s+", " ", text).strip()

@st.cache_data
def load_data():
    return pd.read_csv(DATA_PATH)

@st.cache_resource
def load_camelbert():
    tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR))
    model = AutoModelForSequenceClassification.from_pretrained(str(MODEL_DIR))
    model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    return tokenizer, model, device

def classify_reviews(reviews, tokenizer, model, device, batch_size=16):
    labels, confidences = [], []
    for start in range(0, len(reviews), batch_size):
        batch = [normalize_text(x) for x in reviews[start:start + batch_size]]
        inputs = tokenizer(batch, padding=True, truncation=True, max_length=128, return_tensors="pt")
        inputs = {key: value.to(device) for key, value in inputs.items()}
        with torch.no_grad():
            probs = torch.softmax(model(**inputs).logits, dim=-1)
        scores, ids = probs.max(dim=-1)
        for idx, score in zip(ids.cpu().tolist(), scores.cpu().tolist()):
            labels.append(model.config.id2label.get(idx, model.config.id2label.get(str(idx), str(idx))))
            confidences.append(score)
    return labels, confidences

st.set_page_config(page_title="صدى | Sada Reviews", page_icon="📊", layout="wide")
st.title("صدى | Sada Reviews")
st.caption("CAMeLBERT مصقول لتصنيف مراجعات التطبيقات العربية واللهجات والإنجليزية.")
sample = load_data()

if MODEL_DIR.exists():
    tokenizer, model, device = load_camelbert()
    st.success("النموذج الأساسي: CAMeLBERT-Mix مضبوط دقيقًا على فئات المشروع.")
else:
    tokenizer = model = device = None
    st.warning("أوزان CAMeLBERT المصقولة غير موجودة بعد. شغّل دفتر Colab notebooks/camelbert_finetuning.ipynb ثم فك ضغط النموذج داخل models/sada_camelbert_finetuned.")

with st.sidebar:
    st.header("تحليل مراجعة")
    user_review = st.text_area("اكتب مراجعة", placeholder="التطبيق ما يخليني اسجل دخول")
    analyze = st.button("حلّل المراجعة", type="primary", use_container_width=True)
    st.divider()
    uploaded_file = st.file_uploader("أو ارفع CSV فيه عمود review", type=["csv"])
    st.caption("المعالجة محلية؛ لا تُرسل النصوص إلى خدمة خارجية.")

if analyze and user_review.strip():
    if model is None:
        st.info("درّب CAMeLBERT من دفتر Colab أولًا لتفعيل التصنيف.")
    else:
        labels, scores = classify_reviews([user_review], tokenizer, model, device)
        st.subheader("نتيجة CAMeLBERT")
        c1, c2 = st.columns(2)
        c1.metric("موضوع المراجعة", CATEGORY_NAMES.get(labels[0], labels[0]))
        c2.metric("ثقة النموذج", f"{scores[0]:.0%}")

analysis = sample.copy()
if uploaded_file is not None:
    try:
        uploaded = pd.read_csv(uploaded_file)
        if "review" not in uploaded.columns:
            st.error("أضف عمودًا باسم review في ملف CSV.")
        elif model is None:
            st.info("ارفع الملف بعد تجهيز أوزان CAMeLBERT لتصنيف مراجعاته.")
        else:
            analysis = uploaded.copy()
            analysis["review"] = analysis["review"].fillna("").astype(str)
            analysis["category"], analysis["confidence"] = classify_reviews(analysis["review"].tolist(), tokenizer, model, device)
            analysis["category_ar"] = analysis["category"].map(CATEGORY_NAMES).fillna(analysis["category"])
    except Exception as exc:
        st.error(f"تعذر قراءة الملف: {exc}")

st.divider()
st.subheader("لوحة توزيع الموضوعات")
if uploaded_file is None:
    st.info("العينة المرفقة مصطنعة للتجربة؛ أرقامها لا تمثل مراجعات مستخدمين حقيقيين.")
if "category_ar" not in analysis.columns:
    analysis["category_ar"] = analysis["category"].map(CATEGORY_NAMES).fillna(analysis["category"])
left, right = st.columns(2)
counts = analysis["category_ar"].value_counts().rename_axis("موضوع المراجعة").reset_index(name="عدد المراجعات")
with left:
    fig = px.bar(counts, x="عدد المراجعات", y="موضوع المراجعة", orientation="h", color="عدد المراجعات", color_continuous_scale="Blues", title="المراجعات حسب الموضوع")
    fig.update_layout(showlegend=False, coloraxis_showscale=False, yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)
with right:
    if "dialect" in analysis.columns:
        slice_col = "dialect"
    elif "language" in analysis.columns:
        slice_col = "language"
    else:
        slice_col = None
    if slice_col:
        by_slice = analysis.groupby([slice_col, "category_ar"]).size().reset_index(name="عدد المراجعات")
        fig = px.bar(by_slice, x=slice_col, y="عدد المراجعات", color="category_ar", title="الموضوعات حسب اللهجة / اللغة", barmode="stack")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.metric("عدد المراجعات", len(analysis))

st.caption(f"عدد السجلات المعروضة: {len(analysis):,}")
with st.expander("عرض البيانات المصنفة"):
    columns = [c for c in ["review", "category_ar", "confidence", "language", "dialect"] if c in analysis.columns]
    st.dataframe(analysis[columns], use_container_width=True, hide_index=True)
