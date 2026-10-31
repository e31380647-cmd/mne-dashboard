import os
import json
import html
import requests
import streamlit as st
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import datetime

# ==========================================
# 設定・初期化
# ==========================================
st.set_page_config(page_title="メタ認知航行エンジン", layout="wide")

# StreamlitのSecretsまたは環境変数から安全に取得する（キーの直書きを完全に排除）
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
MODEL_NAME = "gemini-2.5-flash"

# セッションステートの初期化
if "messages" not in st.session_state:
    st.session_state.messages = []
    # 初回起動時の挨拶・問いかけを自動追加
    initial_prompt = "こんにちは。不確実性の高い社会におけるビジネス課題を整理・構造化する「メタ認知航行エンジン」へようこそ。まずは今回のテーマや、現在直面している課題の核心について教えてください。"
    st.session_state.messages.append({"role": "assistant", "content": initial_prompt})

if "turn_count" not in st.session_state:
    st.session_state.turn_count = 0

if "max_turns" not in st.session_state:
    st.session_state.max_turns = 5

# ==========================================
# Gemini API 呼び出し関数
# ==========================================
def call_gemini_api(prompt_text):
    if not GEMINI_API_KEY:
        return "エラー: GEMINI_API_KEY が設定されていません。Streamlit CloudのSecretsまたは環境変数を確認してください。"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            res_json = response.json()
            return res_json["candidates"][0]["content"]["parts"][0]["text"]
        else:
            return f"APIエラー (ステータスコード: {response.status_code}): {response.text}"
    except Exception as e:
        return f"通信エラーが発生しました: {str(e)}"

# ==========================================
# メイン UI 構成
# ==========================================
st.title("🧭 メタ認知航行エンジン")
st.markdown("不確実性の高いビジネス課題を構造化し、実行可能な戦略へと昇華させるための対話型ダッシュボードです。")

# サイドバー設定
with st.sidebar:
    st.header("セッション管理")
    if st.button("対話をリセットする"):
        st.session_state.messages = []
        st.session_state.turn_count = 0
        st.session_state.messages.append({
            "role": "assistant", 
            "content": "対話をリセットしました。新たに整理したい課題について教えてください。"
        })
        st.rerun()
    
    st.info(f"現在のターン数: {st.session_state.turn_count} / {st.session_state.max_turns}")

# 履歴の描画
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ユーザーからの入力を受け付け
if user_input := st.chat_input("ここに回答や課題を入力してください..."):
    # ユーザーメッセージを追加・表示
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    
    st.session_state.turn_count += 1

    # アシスタント側の応答生成
    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            # プロンプトの組み立て（簡易版）
            conversation_history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
            full_prompt = f"以下の対話履歴を元に、ユーザーの課題を深掘りする次の質問や構造化されたフィードバックを行ってください。\n\n{conversation_history}"
            
            ai_response = call_gemini_api(full_prompt)
            st.markdown(ai_response)
            
    # アシスタントの応答を履歴に追加
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    
    # ターン制限のチェック
    # 辞書型への安全な変換・取得の考慮（KeyError防止）
    decision = {"status": "CONTINUE"} 
    status = decision.get("status", "CONTINUE") if isinstance(decision, dict) else "CONTINUE"

    if status == "CONTINUE" and st.session_state.turn_count < st.session_state.max_turns:
        pass
    elif st.session_state.turn_count >= st.session_state.max_turns:
        st.info("ヒアリングの最大ターン数に達しました。右側のサイドバー等から結果のまとめやエクスポートを行ってください。")