import streamlit as st
from google import genai
from google.genai import errors
import trafilatura
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# --- 初期設定 ---
st.set_page_config(page_title="News Summarizer Pro", page_icon="📰")
st.title("📰 ニュース3行まとめ (安定版)")

# APIキーの取得
api_key = st.sidebar.text_input("Gemini API Key", type="password")
if not api_key:
    api_key = st.secrets.get("GEMINI_API_KEY")

# --- 要約ロジック (キャッシュ付き) ---
@st.cache_data(show_spinner=False, ttl=3600)
def get_summary_safe(url, _api_key):
    # 1. 本文抽出
    downloaded = trafilatura.fetch_url(url)
    content = trafilatura.extract(downloaded)
    if not content:
        return "エラー: 記事の内容を抽出できませんでした。"

    # 2. Gemini クライアント初期化
    client = genai.Client(api_key=_api_key)
    
    # 3. リトライ付きの生成処理
    @retry(
        stop=stop_after_attempt(3), 
        wait=wait_exponential(multiplier=2, min=5, max=15),
        retry=retry_if_exception_type(errors.ClientError) # APIエラー時にリトライ
    )
    def call_gemini():
        prompt = f"以下の記事を3行の箇条書きで要約してください。\n\n{content}"
        return client.models.generate_content(
            model="gemini-1.5-flash", # 制限の緩いFlashモデルを推奨
            contents=prompt
        )

    response = call_gemini()
    return response.text

# --- UI部分 ---
if not api_key:
    st.warning("APIキーを設定してください。")
    st.stop()

url = st.text_input("要約したいURL:")

if url:
    try:
        with st.spinner("Geminiが考え中... (制限回避のため少し時間がかかる場合があります)"):
            result = get_summary_safe(url, api_key)
            st.subheader("✅ 要約結果")
            st.write(result)
    except Exception as e:
        if "429" in str(e):
            st.error("🚨 レート制限に達しました。1〜2分待ってから再度お試しください。")
            st.info("💡 対策: Google AI Studioで支払い情報を登録すると、無料のままでも制限が大幅に緩和されます。")
        else:
            st.error(f"予期せぬエラーが発生しました: {e}")