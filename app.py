import streamlit as st
from google import genai
import trafilatura
from tenacity import retry, stop_after_attempt, wait_exponential

# 429エラーが出た時に、間隔をあけて最大3回まで再試行する設定
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def generate_summary_with_retry(prompt):
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )
    return response

# アプリのレイアウト設定
st.set_page_config(page_title="News Summarizer", page_icon="📰")
st.title("📰 ニュース3行まとめ")
st.caption("URLを貼るだけでGeminiがサクッと要約します。")

# サイドバーでAPIキーを設定（またはStreamlit Secretsから読み込み）
# 開発時はサイドバーに入力、公開時はSecretsに保存するのが一般的です
api_key = st.sidebar.text_input("Gemini API Key", type="password")
if not api_key:
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
    else:
        st.warning("サイドバーに Gemini API Key を入力してください。")
        st.stop()

client = genai.Client(api_key=api_key)

# URL入力
url = st.text_input("ニュース記事のURLを入力:", placeholder="https://news.example.com/article...")

if url:
    with st.spinner('記事を読み込んで要約中...'):
        # 1. ニュース記事から本文を抽出
        downloaded = trafilatura.fetch_url(url)
        content = trafilatura.extract(downloaded)

        if content:
            # 2. Geminiに要約を依頼
            prompt = f"""
            以下のニュース記事の内容を、正確に3行（3つの箇条書き）で要約してください。
            余計な挨拶や解説は省き、要約結果のみを出力してください。

            記事内容:
            {content}
            """
            
            try:
                response = generate_summary_with_retry(prompt)
                
                # 3. 結果の表示
                st.subheader("✅ 3行要約")
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"AI処理中にエラーが発生しました: {e}")
        else:
            st.error("記事の内容をうまく取得できませんでした。URLが正しいか確認してください。")