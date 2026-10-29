# LearnBot: Chat-Learning AI Agent

## Features
- Persistent conversation history using SQLite.
- Candidate memory extraction from simple messages such as "I like Python" and "I am studying BCA".
- User approval before saving candidate memories.
- Corrections saved as question-answer examples.
- TF-IDF + cosine similarity retrieval for similar future questions.
- Streamlit dashboard, memory review/deletion, and history.

## Run on Windows
Install Python 3.10+, extract the ZIP, open the folder in VS Code, and run:

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
streamlit run app.py
```

## Test
1. In Chat, type `I like Python` and approve the suggested memory.
2. In Learning, save a question `What is Python?` with its answer.
3. In Chat, ask `Define Python`.
4. Correct an answer and ask a similar question again.

## Honest technical note
This is a learning prototype, not a fully autonomous generative AI. It learns through persistent approved memories and question-answer examples, then retrieves answers using word-based similarity. It does not independently verify facts or retrain a neural network after every chat. Avoid storing sensitive personal data.
