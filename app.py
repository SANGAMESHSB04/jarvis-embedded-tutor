import os
import sqlite3
from datetime import date, datetime
from pathlib import Path

import streamlit as st
from openai import OpenAI

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "jarvis_tutor.db"
MODEL_DEFAULT = os.getenv("OPENAI_MODEL", "gpt-5.5")

ROADMAP = [
    ("Stage 1 — Foundations", "C programming, number systems, digital logic, voltage/current, components, schematics", "Months 1–2"),
    ("Stage 2 — Microcontrollers", "GPIO, buttons, LEDs, timers, interrupts, ADC, PWM, registers, Arduino/STM32", "Months 3–4"),
    ("Stage 3 — Communication", "UART, SPI, I²C, CAN, USB basics, Bluetooth, Wi-Fi, logic analysis", "Months 5–6"),
    ("Stage 4 — Advanced Embedded C/C++", "Pointers, bit manipulation, memory layout, state machines, debugging, Git", "Months 7–9"),
    ("Stage 5 — RTOS", "Tasks, scheduling, priorities, queues, semaphores, mutexes, FreeRTOS", "Months 7–9"),
    ("Stage 6 — Embedded Linux & specialization", "Linux, device drivers, bootloaders, automotive, IoT, security, TinyML", "Months 10–12"),
]

SYSTEM_PROMPT = """
You are JARVIS, a patient personal tutor and research assistant for a beginner learning
Embedded Systems and Embedded C. Teach step by step, using simple English, practical
examples, small exercises, and short quizzes. Do not assume the student already knows
the basics. Encourage the student to attempt answers before revealing solutions when
appropriate. Explain jargon the first time it appears.

The learning roadmap is: (1) C and electronics fundamentals; (2) microcontrollers and
GPIO/timers/interrupts/ADC/PWM; (3) UART/SPI/I2C/CAN and wireless; (4) advanced embedded
C/C++, memory, debugging and Git; (5) RTOS/FreeRTOS; (6) Embedded Linux and a
specialization. The learner wants a daily lesson, assignments, progress tracking, and
research-backed answers.

For research requests, use web search when available, prioritize official documentation,
universities, standards bodies, and reputable technical sources, and include clickable
source links/citations in the answer. Clearly separate sourced facts from your explanation.
Never invent citations or claim to have searched if web search was not used.
When asked for a daily lesson, structure it as: lesson goal, explanation, worked example,
hands-on task, 3–5 question quiz, and homework. Adapt to the learner's saved notes and
completed assignments. Keep the answer accessible but technically accurate.
"""

def connect_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day INTEGER NOT NULL,
        title TEXT NOT NULL,
        task TEXT NOT NULL,
        answer TEXT DEFAULT '',
        completed INTEGER DEFAULT 0,
        updated_at TEXT NOT NULL,
        UNIQUE(day, title)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")
    conn.commit()
    return conn

def get_messages(conn, limit=60):
    rows = conn.execute(
        "SELECT role, content FROM messages ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [{"role": role, "content": content} for role, content in reversed(rows)]

def add_message(conn, role, content):
    conn.execute(
        "INSERT INTO messages(role, content, created_at) VALUES (?, ?, ?)",
        (role, content, datetime.now().isoformat(timespec="seconds"))
    )
    conn.commit()

def get_notes_context(conn):
    rows = conn.execute("SELECT title, content FROM notes ORDER BY id DESC LIMIT 10").fetchall()
    return "\n\n".join(f"NOTE — {title}\n{content}" for title, content in rows)

def get_assignments(conn):
    return conn.execute(
        "SELECT day, title, task, answer, completed, updated_at FROM assignments ORDER BY day"
    ).fetchall()

def upsert_assignment(conn, day, title, task, answer, completed):
    conn.execute("""
        INSERT INTO assignments(day, title, task, answer, completed, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(day, title) DO UPDATE SET
          task=excluded.task, answer=excluded.answer,
          completed=excluded.completed, updated_at=excluded.updated_at
    """, (day, title, task, answer, int(completed), datetime.now().isoformat(timespec="seconds")))
    conn.commit()

st.set_page_config(page_title="JARVIS | Embedded Tutor", page_icon="🤖", layout="wide")
conn = connect_db()

st.markdown("""
<style>
.main .block-container {max-width: 1180px; padding-top: 1.5rem;}
.hero {padding: 1.4rem; border-radius: 18px; background: linear-gradient(120deg,#10233f,#174b63); color: white;}
.small-muted {color: #8a8a8a; font-size: .9rem;}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🤖 JARVIS")
    st.caption("Your personal Embedded Systems learning assistant")
    api_key = st.text_input(
        "OpenAI API key",
        type="password",
        value=os.getenv("OPENAI_API_KEY", ""),
        help="Used only for this running session unless you configure an environment variable or Streamlit secret."
    )
    model = st.text_input("Model", value=MODEL_DEFAULT, help="Change this if your API account uses a different available model.")
    st.divider()
    st.subheader("Roadmap")
    for stage, topics, timing in ROADMAP:
        with st.expander(f"{stage} · {timing}"):
            st.write(topics)
    st.divider()
    st.caption("Your assignments, notes and chat are saved in a local SQLite database on this app's machine.")

st.markdown("""
<div class="hero">
  <h1>JARVIS — Learn. Build. Become an Engineer.</h1>
  <p>Your daily tutor, research helper, assignment notebook and progress tracker.</p>
</div>
""", unsafe_allow_html=True)

tab_home, tab_chat, tab_assign, tab_notes, tab_setup = st.tabs(
    ["🏠 Dashboard", "💬 Ask JARVIS", "📝 Daily assignments", "📚 My notes", "⚙️ Setup"]
)

with tab_home:
    assignments = get_assignments(conn)
    completed_count = sum(1 for row in assignments if row[4])
    total_count = len(assignments)
    col1, col2, col3 = st.columns(3)
    col1.metric("Saved assignments", total_count)
    col2.metric("Completed", completed_count)
    col3.metric("Completion", f"{round(completed_count / total_count * 100) if total_count else 0}%")
    st.subheader("Start today's learning")
    st.write("Start with the basics. You can ask for a lesson, attempt the task, and save your answer in Daily assignments.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Teach me Day 1", type="primary", use_container_width=True):
            st.session_state["prefill_prompt"] = (
                "Teach me Day 1 of my Embedded Systems course from absolute zero. "
                "Topic: what an embedded system is, its inputs-processing-outputs, and examples. "
                "Give a simple lesson, one real-world example, a hands-on task, a 5-question quiz, and homework."
            )
            st.toast("Day 1 lesson prepared. Open Ask JARVIS.")
    with c2:
        if st.button("Plan my next lesson", use_container_width=True):
            st.session_state["prefill_prompt"] = (
                "Look at my saved assignments and notes. Decide the next appropriate lesson in my Embedded Systems roadmap. "
                "Teach it step by step and give a practical task and quiz."
            )
            st.toast("Next lesson prepared. Open Ask JARVIS.")
    st.subheader("Your progress")
    if assignments:
        for row in assignments:
            day, title, task, answer, completed, updated = row
            st.write(("✅" if completed else "⬜") + f" **Day {day}: {title}**")
    else:
        st.info("Your learning tracker is empty. Save your first task in Daily assignments after today's lesson.")

with tab_chat:
    st.subheader("Talk to your tutor")
    st.caption("Ask for explanations, code reviews, debugging help, study plans or research with sources.")
    if "prefill_prompt" in st.session_state and st.session_state["prefill_prompt"]:
        st.info("Suggested prompt ready below. You can edit it before sending.")
    history = get_messages(conn)
    for item in history:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])

    default_prompt = st.session_state.pop("prefill_prompt", "") if "prefill_prompt" in st.session_state else ""
    prompt = st.chat_input("Ask JARVIS anything about embedded systems…")
    if default_prompt and not prompt:
        st.session_state["draft_prompt"] = default_prompt
    draft = st.session_state.get("draft_prompt", "")
    if draft:
        with st.form("suggested_prompt_form"):
            edited_draft = st.text_area("Suggested prompt", value=draft, height=100)
            send_draft = st.form_submit_button("Send to JARVIS", type="primary")
        if send_draft:
            prompt = edited_draft
            st.session_state.pop("draft_prompt", None)

    if prompt:
        if not api_key:
            st.error("Add your OpenAI API key in the sidebar first. Your ChatGPT subscription and API billing are separate.")
        else:
            user_content = prompt.strip()
            add_message(conn, "user", user_content)
            notes_context = get_notes_context(conn)
            assignment_rows = get_assignments(conn)
            progress_context = "\n".join(
                f"Day {r[0]} — {r[1]} — {'completed' if r[4] else 'in progress'}"
                for r in assignment_rows
            ) or "No saved assignments yet."
            input_messages = [{"role": "system", "content": SYSTEM_PROMPT + "\n\nSTUDENT NOTES:\n" + (notes_context or "No saved notes.") + "\n\nPROGRESS:\n" + progress_context}]
            input_messages += get_messages(conn, limit=40)
            client = OpenAI(api_key=api_key)
            with st.chat_message("user"):
                st.markdown(user_content)
            with st.chat_message("assistant"):
                with st.spinner("JARVIS is thinking and researching…"):
                    try:
                        use_research = any(word in user_content.lower() for word in [
                            "research", "latest", "current", "sources", "cite", "compare", "search the web", "recent"
                        ])
                        kwargs = {
                            "model": model.strip(),
                            "input": input_messages,
                        }
                        if use_research:
                            kwargs["tools"] = [{"type": "web_search"}]
                        response = client.responses.create(**kwargs)
                        answer = response.output_text or "I couldn't generate a text response. Please try again."
                        st.markdown(answer)
                        add_message(conn, "assistant", answer)
                    except Exception as exc:
                        error_text = f"Sorry, the request failed: {exc}\n\nCheck your API key, model name, internet connection and API billing, then try again."
                        st.error(error_text)
            st.rerun()

    if st.button("Clear chat history", type="secondary"):
        conn.execute("DELETE FROM messages")
        conn.commit()
        st.rerun()

with tab_assign:
    st.subheader("Daily assignment tracker")
    st.write("Save your task, your own answer, and whether you've completed it. The data is stored in the app's SQLite database.")
    with st.form("assignment_form"):
        day_num = st.number_input("Day number", min_value=1, max_value=365, value=1, step=1)
        title = st.text_input("Assignment title", value="Day 1 — Embedded systems basics")
        task = st.text_area(
            "Task / questions",
            value="1. Explain an embedded system in your own words.\\n2. Give two real-world examples.\\n3. For a smart traffic light, identify input, processing and output.",
            height=120
        )
        answer = st.text_area("My answer / work", height=180, placeholder="Write your answer, code, observations or what you learned…")
        completed = st.checkbox("Mark this assignment as completed")
        save_assignment = st.form_submit_button("Save assignment", type="primary")
    if save_assignment:
        upsert_assignment(conn, int(day_num), title.strip() or f"Day {int(day_num)}", task, answer, completed)
        st.success("Assignment saved.")
        st.rerun()

    st.subheader("Saved assignments")
    saved = get_assignments(conn)
    if not saved:
        st.info("No assignments saved yet.")
    else:
        for row in saved:
            day, title, task, answer, completed, updated = row
            with st.expander(f"{'✅' if completed else '📝'} Day {day}: {title}"):
                st.markdown("**Task**")
                st.write(task)
                st.markdown("**Your work**")
                st.write(answer or "No answer saved yet.")
                st.caption(f"Last saved: {updated}")

with tab_notes:
    st.subheader("Knowledge vault")
    st.write("Store your own notes, useful code snippets, links and explanations. JARVIS can use these notes as context.")
    with st.form("note_form"):
        note_title = st.text_input("Note title")
        note_content = st.text_area("Note content", height=180, placeholder="Paste your notes or code here…")
        save_note = st.form_submit_button("Save note", type="primary")
    if save_note:
        if note_title.strip() and note_content.strip():
            conn.execute(
                "INSERT INTO notes(title, content, created_at) VALUES (?, ?, ?)",
                (note_title.strip(), note_content.strip(), datetime.now().isoformat(timespec="seconds"))
            )
            conn.commit()
            st.success("Note saved.")
            st.rerun()
        else:
            st.warning("Enter both a title and note content.")
    notes = conn.execute("SELECT id, title, content, created_at FROM notes ORDER BY id DESC").fetchall()
    if notes:
        for note_id, note_title, note_content, created_at in notes:
            with st.expander(note_title):
                st.write(note_content)
                st.caption(created_at)
                if st.button("Delete this note", key=f"delete_note_{note_id}"):
                    conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
                    conn.commit()
                    st.rerun()

with tab_setup:
    st.subheader("How to run your JARVIS website")
    st.markdown("""
1. Install **Python 3.10 or newer** on your computer.
2. Extract the downloaded ZIP folder.
3. Open Terminal / Command Prompt inside the extracted folder.
4. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Start the website:

   ```bash
   streamlit run app.py
   ```

6. Your browser should open the local website, usually at `http://localhost:8501`.
7. Add your OpenAI API key in the sidebar to enable AI responses.

**Important:** An API key and API usage billing are separate from a ChatGPT subscription. Keep your key private. Do not paste it into public code or upload it to GitHub.

**Storage note:** Assignments, notes and chat are stored in `jarvis_tutor.db` on the machine running the app. Back up this file. If you deploy publicly, add authentication and persistent database storage before using it with private information.
""")
    st.markdown("**Research behavior:** JARVIS automatically enables web search for prompts that look like research/current-information requests. You can also explicitly say “research this and cite sources.”")
    st.markdown("**Next upgrades:** secure login, cloud database, PDF upload/search, voice interaction, daily reminders, and deployment to a public URL.")

st.divider()
st.caption("JARVIS is a personal learning project. Verify important technical information and test generated code before connecting it to real hardware.")
