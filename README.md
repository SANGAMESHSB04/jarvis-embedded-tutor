# JARVIS — Embedded Systems Tutor

A beginner-friendly local website for daily lessons, AI tutoring, web research, assignments, notes, and progress tracking.

## Requirements
- Python 3.10+
- An OpenAI API key with API billing enabled

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL shown in the terminal (usually http://localhost:8501).

## API key
Enter your key in the sidebar while the app is running, or set `OPENAI_API_KEY` as an environment variable. Never commit the key to GitHub or share it.

Optional model override:
- macOS/Linux: `export OPENAI_MODEL="gpt-5.5"`
- Windows PowerShell: `$env:OPENAI_MODEL="gpt-5.5"`

If that model is not available to your API account, choose an available model in the sidebar.

## Storage and privacy
The app stores chats, assignments, and notes in `jarvis_tutor.db` beside `app.py`. Back up this file. This starter app has no user authentication and is intended for local use. Before public deployment, add login, HTTPS, persistent storage, rate limits, and appropriate data protection.

The OpenAI API is billed separately from a ChatGPT subscription. API model names and availability can change.
