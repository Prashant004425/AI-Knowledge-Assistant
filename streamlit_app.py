import json
import streamlit as st
from pathlib import Path
from datetime import datetime
from typing import Optional

from core.embeddings.embed import main as embed_pipeline
from core.ingestion.ingest import ingest_directory
from core.profile import change_password, get_profile, logout_profile, update_profile
from core.security import redact_sensitive


# ── Cached resources ──────────────────────────────────────────────────────────

@st.cache_resource
def load_retrieval_module():
    from core.retrieval.retrieve import search
    return search


@st.cache_resource
def get_vectorstore_client():
    import chromadb
    vectorstore_dir = Path.cwd() / "data" / "vectorstore"
    if not vectorstore_dir.exists():
        raise FileNotFoundError(f"Vectorstore not found at {vectorstore_dir}")
    return chromadb.PersistentClient(path=str(vectorstore_dir))


def semantic_search(query: str, n_results: int = 5) -> dict:
    search_func = load_retrieval_module()
    return search_func(query, n_results=n_results)


def check_ollama(ollama_tags_url: str = "http://localhost:11434/api/tags") -> tuple[bool, str]:
    try:
        import requests
        r = requests.get(ollama_tags_url, timeout=2)
        if r.status_code == 200:
            return True, "Ollama is running"
        return False, f"Ollama returned status {r.status_code}"
    except Exception as exc:
        return False, str(exc)


def get_index_status() -> dict:
    chunks_file = Path.cwd() / "data" / "processed" / "chunks.json"
    raw_dir = Path.cwd() / "data" / "raw"
    vectorstore_dir = Path.cwd() / "data" / "vectorstore"

    raw_files = 0
    if raw_dir.exists():
        raw_files = sum(1 for path in raw_dir.iterdir() if path.is_file())

    chunk_count = 0
    last_indexed = None
    if chunks_file.exists():
        try:
            with chunks_file.open("r", encoding="utf-8") as handle:
                chunks = json.load(handle)
            chunk_count = len(chunks)
            last_indexed = datetime.fromtimestamp(chunks_file.stat().st_mtime)
        except Exception:
            chunk_count = 0
    elif vectorstore_dir.exists():
        sqlite = vectorstore_dir / "chroma.sqlite3"
        if sqlite.exists():
            last_indexed = datetime.fromtimestamp(sqlite.stat().st_mtime)

    return {"raw_files": raw_files, "chunk_count": chunk_count, "last_indexed": last_indexed}


def format_index_time(timestamp: Optional[datetime]) -> str:
    if not timestamp:
        return "Not indexed yet"
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def handle_file_upload():
    raw_dir = Path.cwd() / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    uploaded_files = st.file_uploader(
        "Upload documents",
        type=["md", "pdf", "docx", "csv", "txt", "text"],
        accept_multiple_files=True,
        key="file_uploader",
    )

    if uploaded_files:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write(f"**{len(uploaded_files)} file(s) selected**")
            for file in uploaded_files:
                st.write(f"• {file.name}")
        with col2:
            upload_btn = st.button("📤 Upload & Index", key="upload_btn")

        if upload_btn:
            with st.spinner("Uploading and indexing documents..."):
                try:
                    saved_count = 0
                    new_filenames = []
                    for uploaded_file in uploaded_files:
                        file_path = raw_dir / uploaded_file.name
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        saved_count += 1
                        new_filenames.append(uploaded_file.name)

                    st.info(f"✅ Saved {saved_count} file(s). Indexing new documents...")
                    chunks = ingest_directory(raw_dir)
                    embed_pipeline(incremental=True)
                    st.success(f"✅ Uploaded {saved_count} file(s) and indexed successfully!")
                    st.balloons()
                except Exception as exc:
                    st.error(f"❌ Upload failed: {exc}")


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AI Knowledge Assistant",
    page_icon="🤖",
    layout="wide",
)

# ── Session state defaults ────────────────────────────────────────────────────

for key, default in {
    "show_profile": False,
    "profile_dropdown_open": False,
    "profile_edit_mode": False,
    "show_password_form": False,
    "chat_history": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
body { background-color: #020617; }
.stApp, .block-container { background: rgba(4, 10, 25, 0.88) !important; }
.hero-card {
    border-radius: 28px;
    background: rgba(15, 23, 42, 0.88);
    border: 1px solid rgba(148, 163, 184, 0.15);
    padding: 32px;
    box-shadow: 0 28px 80px rgba(15, 23, 42, 0.35);
    backdrop-filter: blur(18px);
    margin-bottom: 24px;
}
.hero-card h1 { color: #f8fafc; letter-spacing: 0.04em; margin-bottom: 12px; }
.hero-card p  { color: #cbd5e1; font-size: 1.05rem; line-height: 1.8; }
.section-card {
    border-radius: 20px;
    background: rgba(15, 23, 42, 0.82);
    border: 1px solid rgba(148, 163, 184, 0.12);
    padding: 22px 24px;
    box-shadow: 0 18px 40px rgba(15, 23, 42, 0.22);
    margin-bottom: 20px;
    backdrop-filter: blur(14px);
}
.footer {
    width: 100%;
    padding: 18px 24px;
    margin-top: 36px;
    border-radius: 20px;
    background: rgba(15, 23, 42, 0.78);
    border: 1px solid rgba(148, 163, 184, 0.12);
    text-align: center;
    color: #cbd5e1;
    font-size: 0.95rem;
    backdrop-filter: blur(14px);
}
.chat-bubble-user {
    background: linear-gradient(135deg, #3b82f6, #9333ea);
    color: #fff;
    border-radius: 18px 18px 4px 18px;
    padding: 12px 18px;
    margin: 6px 0 6px 15%;
    font-size: 0.97rem;
    line-height: 1.6;
    box-shadow: 0 4px 16px rgba(59,130,246,0.22);
}
.chat-bubble-ai {
    background: rgba(15, 23, 42, 0.92);
    color: #e2e8f0;
    border: 1px solid rgba(148,163,184,0.18);
    border-radius: 18px 18px 18px 4px;
    padding: 12px 18px;
    margin: 6px 15% 6px 0;
    font-size: 0.97rem;
    line-height: 1.6;
    box-shadow: 0 4px 16px rgba(15,23,42,0.22);
}
.chat-source-tag {
    display: inline-block;
    background: rgba(59,130,246,0.12);
    border: 1px solid rgba(59,130,246,0.25);
    color: #93c5fd;
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 0.78rem;
    margin: 4px 4px 0 0;
}
.stTextInput>div>div>input,
.stTextArea>div>div>textarea {
    background: rgba(15, 23, 42, 0.94) !important;
    border: 1px solid rgba(79, 70, 229, 0.35) !important;
    color: #e2e8f0 !important;
}
.stButton>button {
    border-radius: 999px !important;
    background: linear-gradient(135deg, #3b82f6, #9333ea) !important;
    color: white !important;
    border: none !important;
    box-shadow: 0 8px 20px rgba(59, 130, 246, 0.22) !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease !important;
}
.stButton>button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 14px 28px rgba(59, 130, 246, 0.32) !important;
}
.stSlider>div>div>div>div {
    background: linear-gradient(135deg, #6366f1, #ec4899) !important;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────

sidebar = st.sidebar
sidebar.header("Workspace Controls")

with sidebar.expander("📤 Upload Documents", expanded=False):
    handle_file_upload()

sidebar.divider()

index_status = get_index_status()
with sidebar.expander("🔍 Knowledge base status", expanded=True):
    st.metric("Uploaded files", index_status["raw_files"])
    st.metric("Indexed chunks", index_status["chunk_count"])
    st.metric("Last indexed", format_index_time(index_status["last_indexed"]))

sidebar.divider()

mode = sidebar.radio("Mode", ["💬 Chat", "🔍 Search", "👤 Profile", "🔧 Rebuild Knowledge Base"])

n_results = sidebar.slider("Retrieval chunks", 1, 10, 5)
sidebar.caption("How many document chunks to retrieve per query.")

# Fixed: was "llama3.1", must be "llama3.1:latest" to match Ollama's installed model name
model = sidebar.selectbox("LLM model", ["llama3.1:latest"], index=0)
temperature = sidebar.slider("Temperature", 0.0, 1.0, 0.3, 0.1)
show_sources = sidebar.checkbox("Show source text snippets", value=True)

sidebar.divider()
ollama_ok, ollama_msg = check_ollama()
if ollama_ok:
    sidebar.success(f"✅ {ollama_msg}")
else:
    sidebar.error(f"❌ Ollama offline: {ollama_msg}")
    sidebar.caption("Run `ollama serve` in a terminal to start it.")

sidebar.markdown("---")
sidebar.markdown(
    "**Tips**\n"
    "- Upload & Index before searching\n"
    "- Rebuild after bulk uploads\n"
    "- Ollama must be running for Chat\n"
)

# ── Page: Chat ────────────────────────────────────────────────────────────────

def render_chat() -> None:
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.subheader("💬 Chat with your documents")

    ollama_ok, _ = check_ollama()
    if not ollama_ok:
        st.warning("⚠️ Ollama is not running. Start it with `ollama serve` in your terminal.")

    col_title, col_clear = st.columns([4, 1])
    with col_clear:
        if st.button("🗑️ Clear chat", key="clear_chat"):
            st.session_state["chat_history"] = []
            st.rerun()

    if not st.session_state["chat_history"]:
        st.markdown(
            "<p style='color:#64748b; text-align:center; padding:32px 0;'>"
            "Ask anything about your uploaded documents…</p>",
            unsafe_allow_html=True,
        )
    else:
        for msg in st.session_state["chat_history"]:
            if msg["role"] == "user":
                st.markdown(
                    f"<div class='chat-bubble-user'>🧑 {msg['content']}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div class='chat-bubble-ai'>🤖 {msg['content']}</div>",
                    unsafe_allow_html=True,
                )
                if msg.get("sources"):
                    source_tags = "".join(
                        f"<span class='chat-source-tag'>📄 {s['source']} ({s['relevance']:.0%})</span>"
                        for s in msg["sources"]
                    )
                    st.markdown(source_tags, unsafe_allow_html=True)
                    if show_sources and msg.get("chunks"):
                        with st.expander("📖 Retrieved context", expanded=False):
                            for chunk in msg["chunks"]:
                                st.markdown(
                                    f"**{chunk.get('source','?')}** "
                                    f"(similarity: {chunk.get('similarity',0):.2f})"
                                )
                                st.write(redact_sensitive(chunk.get("text", "")))
                                st.divider()

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    col_input, col_send = st.columns([5, 1])
    with col_input:
        user_question = st.text_input(
            "Ask a question",
            placeholder="e.g. Who is Prashant? What is WarmUp Task D2 about?",
            key="chat_input",
            label_visibility="collapsed",
        )
    with col_send:
        send_btn = st.button("Send ➤", key="send_btn")

    if send_btn and user_question.strip():
        st.session_state["chat_history"].append({
            "role": "user",
            "content": user_question.strip(),
            "sources": [],
            "chunks": [],
        })

        with st.spinner("Thinking…"):
            try:
                from core.rag.generate import generate_answer

                previous_answers = [
                    m["content"]
                    for m in st.session_state["chat_history"]
                    if m["role"] == "assistant"
                ]

                result = generate_answer(
                    question=user_question.strip(),
                    model=model,
                    n_retrieve=n_results,
                    temperature=temperature,
                    previous_answers=previous_answers or None,
                )

                if result:
                    st.session_state["chat_history"].append({
                        "role": "assistant",
                        "content": result["answer"],
                        "sources": result.get("sources", []),
                        "chunks": result.get("retrieved_chunks", []),
                    })
                else:
                    st.session_state["chat_history"].append({
                        "role": "assistant",
                        "content": "❌ Could not generate an answer. Check that Ollama is running and the knowledge base is indexed.",
                        "sources": [],
                        "chunks": [],
                    })

            except Exception as exc:
                st.session_state["chat_history"].append({
                    "role": "assistant",
                    "content": f"❌ Error: {exc}",
                    "sources": [],
                    "chunks": [],
                })

        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ── Page: Search ──────────────────────────────────────────────────────────────

def render_search() -> None:
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.subheader("🔍 Semantic search")
    st.caption("Raw chunk retrieval — no AI generation, just the closest matching passages.")

    query = st.text_input(
        "Search your documents",
        placeholder="Type a keyword or phrase…",
        key="search_input",
    )

    if st.button("Search", key="search_button"):
        if not query.strip():
            st.warning("Please enter a search query.")
        else:
            with st.spinner("Searching knowledge base…"):
                try:
                    results = semantic_search(query, n_results=n_results)
                except Exception as exc:
                    st.error(f"Search failed: {exc}")
                    st.markdown("</div>", unsafe_allow_html=True)
                    return

            num = results.get("num_results", 0)
            if num == 0:
                st.info("No matching documents found. Try a broader query or rebuild the knowledge base.")
            else:
                st.success(f"Found {num} result(s)")
                for idx, item in enumerate(results.get("results", []), start=1):
                    source = item.get("source", "unknown")
                    similarity = item.get("similarity", 0.0)
                    text_snippet = redact_sensitive(item.get("text", ""))
                    with st.expander(f"**{idx}. {source}** — similarity: {similarity:.2f}", expanded=idx == 1):
                        st.write(text_snippet)

    st.markdown("</div>", unsafe_allow_html=True)


# ── Page: Profile ─────────────────────────────────────────────────────────────

def render_profile() -> None:
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.subheader("👤 Profile")
    profile = get_profile()

    top_col, detail_col = st.columns([1, 2])
    with top_col:
        if profile.get("avatar_url"):
            st.image(profile["avatar_url"], width=180)
        st.markdown(f"### {profile.get('name', 'Your name')}")
        st.write(f"**Role:** {profile.get('role', 'User')}")
        st.write(f"**Department:** {profile.get('department', 'N/A')}")
        st.write(f"**Joined:** {profile.get('joining_date', 'N/A')}")
    with detail_col:
        st.write(profile.get("about_me", ""))
        st.write("---")
        if st.button("Edit profile", key="toggle_profile_edit"):
            st.session_state["profile_edit_mode"] = not st.session_state["profile_edit_mode"]

    if st.session_state["profile_edit_mode"]:
        with st.form("profile_form"):
            updated_avatar       = st.text_input("Profile picture URL",  value=profile.get("avatar_url", ""))
            updated_name         = st.text_input("Full name",             value=profile.get("name", ""))
            updated_employee_id  = st.text_input("Employee ID",           value=profile.get("employee_id", ""))
            updated_department   = st.text_input("Department",            value=profile.get("department", ""))
            updated_email        = st.text_input("Email",                 value=profile.get("email", ""))
            role_options = ["Engineer", "Admin", "User"]
            current_role = profile.get("role", "Engineer")
            updated_role = st.selectbox(
                "Role", role_options,
                index=role_options.index(current_role) if current_role in role_options else 0,
            )
            updated_joining_date = st.text_input("Joining date", value=profile.get("joining_date", "YYYY-MM-DD"))
            updated_about_me     = st.text_area("About me", value=profile.get("about_me", ""), height=140)

            if st.form_submit_button("Save profile"):
                try:
                    update_profile({
                        "avatar_url": updated_avatar,
                        "name": updated_name,
                        "employee_id": updated_employee_id,
                        "department": updated_department,
                        "email": updated_email,
                        "role": updated_role,
                        "joining_date": updated_joining_date,
                        "about_me": updated_about_me,
                    })
                    st.success("Profile updated successfully.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Failed to update profile: {exc}")

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.subheader("🔐 Security & session")
    with st.expander("Change password", expanded=st.session_state.get("show_password_form", False)):
        current_password = st.text_input("Current password",     type="password", key="current_password")
        new_password     = st.text_input("New password",         type="password", key="new_password")
        confirm_password = st.text_input("Confirm new password", type="password", key="confirm_password")
        if st.button("Change password", key="change_password"):
            if new_password != confirm_password:
                st.warning("Passwords do not match.")
            else:
                try:
                    change_password(current_password, new_password)
                    st.success("Password updated successfully.")
                    st.session_state["show_password_form"] = False
                except Exception as exc:
                    st.error(f"Password update failed: {exc}")

    if st.button("🚪 Logout", key="logout_button"):
        logout_profile()
        st.info("Logged out. Refresh the page to continue.")
    st.markdown("</div>", unsafe_allow_html=True)


# ── Page: Rebuild ─────────────────────────────────────────────────────────────

def render_rebuild() -> None:
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.subheader("🔧 Rebuild knowledge base")
    st.write("Use this after adding or updating documents in `data/raw/`.")

    if st.button("⚙️ Ingest documents and rebuild embeddings", key="rebuild_button"):
        with st.spinner("Ingesting and rebuilding vector store…"):
            try:
                chunks = ingest_directory()
                embed_pipeline(incremental=False)  # full wipe and rebuild
                st.success(f"✅ Knowledge base rebuilt — {len(chunks)} chunks indexed.")
            except Exception as exc:
                st.error(f"Failed to rebuild: {exc}")
    st.markdown("</div>", unsafe_allow_html=True)


# ── Hero card ─────────────────────────────────────────────────────────────────

def render_hero() -> None:
    st.markdown("""
    <div class='hero-card'>
        <h1>🤖 AI Knowledge Assistant</h1>
        <p>Ask questions about your documents and get AI-powered answers grounded in your knowledge base.</p>
        <div style='display:flex; flex-wrap:wrap; gap:16px; margin-top:24px;'>
            <div style='flex:1 1 200px; border-radius:14px; padding:14px; background:rgba(30,41,59,0.92);'>
                <strong style='color:#fff;'>💬 Smart answers</strong><br>
                <span style='color:#94a3b8;'>RAG pipeline with local Ollama LLM.</span>
            </div>
            <div style='flex:1 1 200px; border-radius:14px; padding:14px; background:rgba(30,41,59,0.92);'>
                <strong style='color:#fff;'>🔍 Semantic search</strong><br>
                <span style='color:#94a3b8;'>Instantly surface relevant chunks.</span>
            </div>
            <div style='flex:1 1 200px; border-radius:14px; padding:14px; background:rgba(30,41,59,0.92);'>
                <strong style='color:#fff;'>📄 Any format</strong><br>
                <span style='color:#94a3b8;'>PDF, DOCX, CSV, Markdown, TXT.</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Router ────────────────────────────────────────────────────────────────────

if st.session_state.get("show_profile", False):
    render_profile()
    if st.button("← Back", key="back_from_profile"):
        st.session_state["show_profile"] = False
        st.rerun()

elif mode == "💬 Chat":
    render_hero()
    render_chat()

elif mode == "🔍 Search":
    render_search()

elif mode == "👤 Profile":
    render_profile()

else:
    render_rebuild()


# ── Footer ────────────────────────────────────────────────────────────────────

st.markdown("""
<div class='footer'>
    Powered by local embeddings · ChromaDB · Ollama · Streamlit
</div>
""", unsafe_allow_html=True)