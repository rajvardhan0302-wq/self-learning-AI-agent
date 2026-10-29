import sqlite3
import re
from pathlib import Path
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DB_PATH = Path(__file__).with_name("learnbot.db")

class LearnBot:
    def __init__(self, db_path=str(DB_PATH), threshold=0.24):
        self.db_path, self.threshold = db_path, threshold
        with self._connect() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT, fact TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL)""")
            con.execute("""CREATE TABLE IF NOT EXISTS examples (
                id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT NOT NULL,
                answer TEXT NOT NULL, source TEXT NOT NULL, created_at TEXT NOT NULL)""")
            con.execute("""CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_message TEXT NOT NULL,
                bot_reply TEXT NOT NULL, feedback TEXT, correction TEXT,
                created_at TEXT NOT NULL)""")

    def _connect(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def _now(self):
        return datetime.now().isoformat(timespec="seconds")

    def save_memory(self, fact):
        with self._connect() as con:
            con.execute("INSERT OR IGNORE INTO memories(fact, created_at) VALUES (?, ?)",
                        (fact.strip(), self._now()))

    def memories(self):
        with self._connect() as con:
            return [dict(r) for r in con.execute(
                "SELECT id, fact, created_at FROM memories ORDER BY id DESC").fetchall()]

    def delete_memory(self, memory_id):
        with self._connect() as con:
            con.execute("DELETE FROM memories WHERE id=?", (memory_id,))

    def examples(self):
        with self._connect() as con:
            return [dict(r) for r in con.execute(
                "SELECT question, answer FROM examples ORDER BY id DESC").fetchall()]

    def teach_example(self, question, answer, source="manual_teaching"):
        if not question.strip() or not answer.strip():
            raise ValueError("Question and answer are required.")
        with self._connect() as con:
            con.execute("INSERT INTO examples(question, answer, source, created_at) VALUES (?, ?, ?, ?)",
                        (question.strip(), answer.strip(), source, self._now()))

    def extract_candidate_memory(self, message):
        patterns = [
            (r"^my name is\s+(.{1,80})$", "User's name is "),
            (r"^i am studying\s+(.{1,120})$", "User studies "),
            (r"^i study\s+(.{1,120})$", "User studies "),
            (r"^i like\s+(.{1,120})$", "User likes "),
            (r"^i prefer\s+(.{1,120})$", "User prefers "),
            (r"^remember that\s+(.{1,180})$", ""),
        ]
        msg = message.strip().rstrip(".!?")
        for pattern, prefix in patterns:
            match = re.match(pattern, msg, re.IGNORECASE)
            if match and match.group(1).strip():
                return prefix + match.group(1).strip()
        return None

    def _best_answer(self, question):
        examples = self.examples()
        if not examples:
            return None, 0.0
        try:
            vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
            matrix = vectorizer.fit_transform([e["question"] for e in examples] + [question])
            scores = cosine_similarity(matrix[-1], matrix[:-1]).ravel()
            idx = int(scores.argmax())
            score = float(scores[idx])
            return (examples[idx]["answer"], score) if score >= self.threshold else (None, score)
        except ValueError:
            return None, 0.0

    def reply(self, message):
        message = message.strip()
        if not message:
            return {"id": None, "answer": "Please type a message.", "candidate_memory": None}
        candidate = self.extract_candidate_memory(message)
        answer, score = self._best_answer(message)
        if answer:
            reply = answer
        elif candidate:
            reply = "Thanks for telling me. I found a possible memory; approve it below if you'd like me to remember it."
        else:
            reply = ("I don't have a reliable saved answer for that yet. You can teach me in the Learning tab "
                     "or correct my answer so I can use it as an example later.")
        with self._connect() as con:
            cur = con.execute("INSERT INTO chats(user_message, bot_reply, created_at) VALUES (?, ?, ?)",
                              (message, reply, self._now()))
            chat_id = cur.lastrowid
        return {"id": chat_id, "answer": reply, "candidate_memory": candidate, "score": score}

    def feedback(self, chat_id, rating, correction=""):
        if rating not in {"helpful", "not_helpful"}:
            raise ValueError("Invalid rating.")
        correction = correction.strip()
        with self._connect() as con:
            row = con.execute("SELECT user_message FROM chats WHERE id=?", (chat_id,)).fetchone()
            if not row:
                raise ValueError("Chat not found.")
            con.execute("UPDATE chats SET feedback=?, correction=? WHERE id=?",
                        (rating, correction or None, chat_id))
            if correction:
                con.execute("INSERT INTO examples(question, answer, source, created_at) VALUES (?, ?, ?, ?)",
                            (row["user_message"], correction, "user_correction", self._now()))

    def stats(self):
        with self._connect() as con:
            return {
                "chats": con.execute("SELECT COUNT(*) FROM chats").fetchone()[0],
                "memories": con.execute("SELECT COUNT(*) FROM memories").fetchone()[0],
                "examples": con.execute("SELECT COUNT(*) FROM examples").fetchone()[0],
                "helpful": con.execute("SELECT COUNT(*) FROM chats WHERE feedback='helpful'").fetchone()[0]
            }

    def history(self):
        with self._connect() as con:
            return [dict(r) for r in con.execute(
                "SELECT user_message, bot_reply, feedback, created_at FROM chats ORDER BY id DESC LIMIT 100"
            ).fetchall()]
