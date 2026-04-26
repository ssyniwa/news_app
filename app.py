import streamlit as st
from google import genai
from google.genai import errors
import trafilatura
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

st.set_page_config(page_title="News Summarizer Pro", page_icon="📰")
st.title("📰 ニュース3行まとめ")

# APIキー設定
api_key = st.sidebar.text_input("Gemini API Key", type="password")
if not api_key:
    api_key = st.secrets.get("GEMINI_API_KEY")

# --- 要約ロジック ---
@st.cache_data(show_spinner=False, ttl=3600)
def get_summary_safe(url, _api_key):
    # 1. 本文抽出
    downloaded = trafilatura.fetch_url(url)
    content = trafilatura.extract(downloaded)
    if not content:
        return "ERROR: 記事の内容を抽出できませんでした。"

    # 2. クライアント初期化
    client = genai.Client(api_key=_api_key)
    
    # 3. リトライ設定
    # 429 (Rate Limit) の場合のみリトライするように設定
    @retry(
        stop=stop_after_attempt(3), 
        wait=wait_exponential(multiplier=2, min=5, max=15)
    )
    def call_gemini():
        try:
            prompt = f"以下の記事を3行の箇条書きで要約してください。日本語で回答してください。\n\n{content}"
            return client.models.generate_content(
                model="gemini-1.5-flash", 
                contents=prompt
            )
        except Exception as e:
            # ここで生のエラーをキャッチして中身を確認
            raise e

    return call_gemini().text

# --- UI ---
if not api_key:
    st.warning("APIキーを入力してください。")
    st.stop()

url = st.text_input("URLを貼り付けてください:")

if url:
    try:
        with st.spinner("要約中..."):
            result = get_summary_safe(url, api_key)
            st.subheader("✅ 要約結果")
            st.write(result)
    except Exception as e:
        # RetryErrorの奥にある本当の原因を表示
        error_msg = str(e)
        if "429" in error_msg:
            st.error("🚨 混み合っています。APIの無料枠制限にかかりました。少し待ってから再試行してください。")
        elif "API_KEY_INVALID" in error_msg or "403" in error_msg:
            st.error("🔑 APIキーが正しくありません。設定を確認してください。")
        else:
            st.error(f"AI処理中にエラーが発生しました: {error_msg}")