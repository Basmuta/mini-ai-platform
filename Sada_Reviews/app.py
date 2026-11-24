Warning: fs was declared with const; use let for reassignable variables.
import re
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline

BASE = Path(__file__).parent
DATA_PATH = BASE / "data" / "sample_reviews.csv"
CATEGORY_NAMES = {"login_issue":"تسجيل الدخول", "crash":"أعطال التطبيق", "performance":"الأداء والسرعة", "payment":"الدفع والفواتير", "usability":"سهولة الاستخدام", "feature_request":"اقتراح ميزة", "positive_experience":"تجربة إيجابية"}
SENTIMENT_NAMES = {"negative":"سلبي", "neutral":"محايد", "positive":"إيجابي"}

def normalize_text(text):
    text = str(text).lower().strip()
    text = re.sub(r"[إأآا]", "ا", text)
    text = re.sub(r"ى", "ي", text)
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", " [EMAIL] ", text)
    text = re.sub(r"(?<!\d)(?:05\d{8}|\+9665\d{8})(?!\d)", " [PHONE] ", text)
    return re.sub(r"\s+", " ", text)

@st.cache_data
def load_data():
    return pd.read_csv(DATA_PATH)

@st.cache_resource
def train_models(data):
    x_train, x_test, y_cat_train, y_cat_test, y_sent_train, y_sent_test = train_test_split(
        data["review"], data["category"], data["sentiment"], test_size=0.25, random_state=42, stratify=data["category"])
    def build_model():
        return make_pipeline(TfidfVectorizer(preprocessor=normalize_text, analyzer="char_wb", ngram_range=(2, 5)), LogisticRegression(max_iter=1500, class_weight="balanced"))
    category_model = build_model().fit(x_train, y_cat_train)
    sentiment_model = build_model().fit(x_train, y_sent_train)
    category_pred = category_model.predict(x_test)
    sentiment_pred = sentiment_model.predict(x_test)
    metrics = {"category_accuracy":accuracy_score(y_cat_test, category_pred), "category_macro_f1":f1_score(y_cat_test, category_pred, average="macro"), "sentiment_macro_f1":f1_score(y_sent_test, sentiment_pred, average="macro")}
    return category_model, sentiment_model, metrics

st.set_page_config(page_title="صدى | Sada Reviews", page_icon="📊", layout="wide")
st.title("صدى | Sada Reviews")
st.caption("تحليل مراجعات التطبيقات العربية والإنجليزية لاكتشاف أكثر ما يواجه المستخدمين.")
sample = load_data()
category_model, sentiment_model, metrics = train_models(sample)
uploaded_file = st.file_uploader("ارفع CSV يحتوي عمود review لتحليله", type=["csv"])
dashboard_data = sample.copy()
if uploaded_file is not None:
    try:
        uploaded = pd.read_csv(uploaded_file)
        if "review" not in uploaded.columns:
            st.warning("ملف CSV يحتاج عمودًا باسم review. نعرض العينة التجريبية حاليًا.")
        else:
            dashboard_data = uploaded.copy()
            dashboard_data["review"] = dashboard_data["review"].fillna("").astype(str)
            dashboard_data["category"] = category_model.predict(dashboard_data["review"])
            dashboard_data["sentiment"] = sentiment_model.predict(dashboard_data["review"])
    except Exception as exc:
        st.error(f"تعذر قراءة الملف: {exc}")
with st.sidebar:
    st.header("جرّب التحليل")
    user_review = st.text_area("اكتب مراجعة", placeholder="مثال: التطبيق يعلق كل ما حاولت أسجل الدخول")
    analyze = st.button("حلّل المراجعة", type="primary", use_container_width=True)
    st.divider()
    st.caption("تعمل النسخة محليًا على عينة تعليمية. لا تُرسل المراجعات إلى خدمة خارجية.")
if analyze and user_review.strip():
    cat = category_model.predict([user_review])[0]
    sent = sentiment_model.predict([user_review])[0]
    confidence = max(category_model.predict_proba([user_review])[0])
    st.subheader("نتيجة المراجعة")
    c1,c2,c3 = st.columns(3)
    c1.metric("الموضوع", CATEGORY_NAMES.get(cat, cat))
    c2.metric("المشاعر", SENTIMENT_NAMES.get(sent, sent))
    c3.metric("ثقة التصنيف", f"{confidence:.0%}")
    st.caption("الثقة تقدير داخلي للنموذج وليست ضمانًا لصحة التصنيف.")
st.divider()
st.subheader("لوحة تحليل المراجعات")
if uploaded_file is None:
    st.info("البيانات المرفقة أمثلة مصطنعة لأغراض العرض، ولا تمثل مراجعات حقيقية أو أداءً إنتاجيًا.")
left,right = st.columns(2)
category_counts = dashboard_data["category"].map(CATEGORY_NAMES).value_counts().rename_axis("الموضوع").reset_index(name="عدد المراجعات")
sentiment_counts = dashboard_data["sentiment"].map(SENTIMENT_NAMES).value_counts().rename_axis("المشاعر").reset_index(name="عدد المراجعات")
with left:
    fig = px.bar(category_counts, x="عدد المراجعات", y="الموضوع", orientation="h", color="عدد المراجعات", color_continuous_scale="Blues", title="المراجعات حسب الموضوع")
    fig.update_layout(showlegend=False, coloraxis_showscale=False, yaxis={"categoryorder":"total ascending"})
    st.plotly_chart(fig, use_container_width=True)
with right:
    fig = px.pie(sentiment_counts, names="المشاعر", values="عدد المراجعات", hole=0.55, color="المشاعر", color_discrete_map={"سلبي":"#D95F59", "محايد":"#E6B655", "إيجابي":"#4C9A75"}, title="توزيع المشاعر في العينة")
    st.plotly_chart(fig, use_container_width=True)
m1,m2,m3 = st.columns(3)
m1.metric("حجم العينة", f"{len(dashboard_data)} مراجعة")
m2.metric("دقة تصنيف الموضوع", f"{metrics['category_accuracy']:.0%}")
m3.metric("Macro-F1 للموضوع", f"{metrics['category_macro_f1']:.2f}")
st.caption(f"Macro-F1 للمشاعر على تقسيم تجريبي: {metrics['sentiment_macro_f1']:.2f}. هذه النتائج للتوضيح على بيانات مصطنعة ولا تقيس الأداء على مراجعات حقيقية.")
with st.expander("عرض بيانات العينة"):
    view = dashboard_data.copy()
    view["category"] = view["category"].map(CATEGORY_NAMES)
    view["sentiment"] = view["sentiment"].map(SENTIMENT_NAMES)
    st.dataframe(view, use_container_width=True, hide_index=True)
