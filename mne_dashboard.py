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
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL_NAME = "gemini-2.5-flash"

# セッションステートの初期化
if "step" not in st.session_state:
    st.session_state.step = "input_initial"  # "input_initial", "qa_loop", "completed"
if "initial_idea" not in st.session_state:
    st.session_state.initial_idea = ""
if "qa_history" not in st.session_state:
    st.session_state.qa_history = []  # [{"q": "...", "a": "..."}, ...]
if "current_question" not in st.session_state:
    st.session_state.current_question = ""
if "turn_count" not in st.session_state:
    st.session_state.turn_count = 0
if "max_turns" not in st.session_state:
    st.session_state.max_turns = 3  # 最大動的ターン数
if "final_proposal" not in st.session_state:
    st.session_state.final_proposal = ""
if "svg_content" not in st.session_state:
    st.session_state.svg_content = ""

# ==========================================
# API呼び出し関数 (Gemini)
# ==========================================
def call_gemini(prompt):
    if not GEMINI_API_KEY:
        return "ERROR: GEMINI_API_KEY is not set."
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            return text.replace("```json", "").replace("```markdown", "").replace("```", "").strip()
        else:
            return f"API Error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Exception: {str(e)}"

# ==========================================
# 動的Q&A制御ロジック
# ==========================================
def get_next_question_or_decision(idea, history):
    """
    これまでの対話履歴を元に、次に聞くべき「最も重要な1問」を生成するか、
    あるいは「十分な情報が集まったので生成フェーズに進むべきか」を判定する。
    """
    history_str = json.dumps(history, ensure_ascii=False, indent=2)
    prompt = f"""
あなたは優秀なビジネスアーキテクトです。
初期アイデアとこれまでのQ&A履歴を分析し、高品質な企画書作成のために【追加で必要な情報がまだあるか】を判断してください。

【初期アイデア】
{idea}

【これまでのQ&A履歴】
{history_str}

判断基準：
- まだ本質的課題、ターゲット、制約、リソース等に不明確な点があり、情報不足であれば、**次に解き明かすべき最も重要な1つの質問**を出力してください。
- すでに十分な情報が集まっており、企画書作成に移行できると判断した場合は、質問の代わりに "COMPLETE" という文字列のみを出力してください。

出力は以下のJSONフォーマットのみで行ってください：
{{
  "status": "CONTINUE" または "COMPLETE",
  "next_question": "次に投げかける1つの具体的な質問（CONTINUEの場合のみ）"
}}
"""
    res_text = call_gemini(prompt)
    try:
        start_idx = res_text.find("{")
        end_idx = res_text.rfind("}")
        if start_idx != -1 and end_idx != -1:
            data = json.loads(res_text[start_idx:end_idx+1])
            return data
    except:
        pass
    
    return {"status": "COMPLETE", "next_question": ""}

def generate_proposal_and_svg(idea, history):
    """集まったすべての情報を元に最終提案書とSVG見出しを生成"""
    history_str = json.dumps(history, ensure_ascii=False, indent=2)
    
    prompt = f"""
以下の初期アイデアと対話履歴を統合し、VUCA時代に耐えうる完成された「事業企画書・提案書」をMarkdown形式で作成してください。

【初期アイデア】
{idea}

【Q&A履歴（ユーザーとの対話）】
{history_str}

【構成要件】
1. タイトル（洗練されたビジネス名）
2. エグゼクティブサマリー
3. 背景と構造的課題（第一原理分析）
4. 提案内容・システムモデル
5. 差別化要因とレジリエンス戦略
6. 実行ロードマップ & 必要なリソース

冒頭にYAMLフロントマターを付けてください：
---
title: "企画書タイトル"
category: "事業企画 / 構造改革"
tags: ["AI", "レジリエンス", "構造改革"]
---
"""
    proposal = call_gemini(prompt)
    
    # SVG見出し画像の生成
    safe_idea = html.escape(idea[:30])
    svg = f"""<svg xmlns="[http://www.w3.org/2000/svg](http://www.w3.org/2000/svg)" width="800" height="400" viewBox="0 0 800 400">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f172a"/>
      <stop offset="100%" stop-color="#1e293b"/>
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#bg)"/>
  <text x="50" y="100" fill="#38bdf8" font-family="sans-serif" font-size="24" font-weight="bold">META-COGNITIVE NAVIGATION ENGINE</text>
  <text x="50" y="180" fill="#f8fafc" font-family="sans-serif" font-size="36" font-weight="bold">{safe_idea}</text>
  <text x="50" y="240" fill="#94a3b8" font-family="sans-serif" font-size="18">VUCA Resilience & Structural Architecture</text>
  <circle cx="720" cy="80" r="30" fill="#38bdf8" opacity="0.2"/>
</svg>"""
    return proposal, svg

# ==========================================
# UI 構築 (Streamlit)
# ==========================================
st.title("🧭 メタ認知航行エンジン (動的対話型・自動生成システム)")
st.markdown("初期アイデアを入力すると、システムが最適な質問を**1問ずつ動的に生成**し、対話を通じて高精度な企画書を構築します。")

# --- ステップ1: 初期アイデア入力 ---
if st.session_state.step == "input_initial":
    st.subheader("1. 企画・アイデアの初期入力")
    idea_input = st.text_area("ざっくりとしたアイデアや解決したい課題を入力してください", 
                             placeholder="例: 企業地方IT向けに、手書きコーディング脱却とAI活用支援サービスを立ち上げたい")
    
    if st.button("対話を開始する", type="primary"):
        if idea_input.strip():
            st.session_state.initial_idea = idea_input
            st.session_state.qa_history = []
            st.session_state.turn_count = 1
            
            # 初回の質問を取得
            with st.spinner("初期構造を分析し、最初の質問を生成中..."):
                res = get_next_question_or_decision(st.session_state.initial_idea, st.session_state.qa_history)
                st.session_state.current_question = res.get("next_question", "ターゲットや具体的な課題について教えてください。")
            st.session_state.step = "qa_loop"
            st.rerun()
        else:
            st.warning("アイデアを入力してください。")

# --- ステップ2: 1問ずつの動的Q&Aループ ---
elif st.session_state.step == "qa_loop":
    st.subheader(f"2. ヒアリング対話 (第 {st.session_state.turn_count} ターン)")
    
    # これまでの履歴表示
    if st.session_state.qa_history:
        with st.expander("これまでの対話履歴", expanded=False):
            for i, qa in enumerate(st.session_state.qa_history, 1):
                st.markdown(f"**Q{i}:** {qa['q']}")
                st.markdown(f"**A{i}:** {qa['a']}")
                st.markdown("---")
                
    # 現在の質問表示
    st.info(f"**💡 システムからの問い:**\n\n{st.session_state.current_question}")
    
    user_answer = st.text_area("あなたの回答を入力してください", key=f"ans_{st.session_state.turn_count}")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("回答を送信する", type="primary"):
            if user_answer.strip():
                # 履歴に追加
                st.session_state.qa_history.append({
                    "q": st.session_state.current_question,
                    "a": user_answer
                })
                
                # 次のステップを動的判定 (さらに質問するか、生成に進むか)
                with st.spinner("文脈を分析し、次工程を判定中..."):
                    decision = get_next_question_or_decision(st.session_state.initial_idea, st.session_state.qa_history)
                    
                    if decision["status"] == "CONTINUE" and st.session_state.turn_count < st.session_state.max_turns:
                        st.session_state.turn_count += 1
                        st.session_state.current_question = decision["next_question"]
                        st.rerun()
                    else:
                        # 情報十分と判断 -> 最終生成フェーズへ
                        st.session_state.step = "completed"
                        prop, svg = generate_proposal_and_svg(st.session_state.initial_idea, st.session_state.qa_history)
                        st.session_state.final_proposal = prop
                        st.session_state.svg_content = svg
                        st.rerun()
            else:
                st.warning("回答を入力してください。")

# --- ステップ3: 最終結果・プレビュー & エクスポート ---
elif st.session_state.step == "completed":
    st.subheader("3. 構造化提案書・アセット生成完了")
    st.success("対話による構造抽出が完了し、提案書が生成されました。")
    
    # タブによるビュー切り替え
    tab_md, tab_svg, tab_export = st.tabs(["📝 企画書プレビュー", "🎨 SVGアイキャッチ", "💾 エクスポート"])
    
    with tab_md:
        st.markdown(st.session_state.final_proposal)
        
    with tab_svg:
        st.markdown("### 生成されたSVGアセット")
        st.image(io.BytesIO(st.session_state.svg_content.encode("utf-8")), use_container_width=True)
        
    with tab_export:
        st.markdown("### ローカルアセット出力")
        
        # 出力ディレクトリ作成
        out_dir = "generated_output"
        os.makedirs(out_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # ファイルパス
        md_path = os.path.join(out_dir, f"proposal_{timestamp}.md")
        svg_path = os.path.join(out_dir, f"eyecatch_{timestamp}.svg")
        docx_path = os.path.join(out_dir, f"proposal_{timestamp}.docx")
        
        # 保存実行
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(st.session_state.final_proposal)
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(st.session_state.svg_content)
            
        # Word生成
        doc = Document()
        doc.add_heading("事業企画・提案書", 0)
        for line in st.session_state.final_proposal.split("\n"):
            if line.startswith("# "):
                doc.add_heading(line.replace("# ", ""), level=1)
            elif line.startswith("## "):
                doc.add_heading(line.replace("## ", ""), level=2)
            elif line.strip():
                doc.add_paragraph(line)
        doc.save(docx_path)
        
        st.info(f"すべてのファイルが `{out_dir}/` に同期保存されました。")
        
        # ダウンロードボタン
        st.download_button("Markdownをダウンロード (.md)", st.session_state.final_proposal, file_name=f"proposal_{timestamp}.md")
        st.download_button("SVG画像をダウンロード (.svg)", st.session_state.svg_content, file_name=f"eyecatch_{timestamp}.svg", mime="image/svg+xml")
        
        if st.button("最初からやり直す"):
            st.session_state.step = "input_initial"
            st.session_state.qa_history = []
            st.session_state.turn_count = 0
            st.rerun()