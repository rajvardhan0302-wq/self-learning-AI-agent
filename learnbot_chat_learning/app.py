import streamlit as st
import pandas as pd
from agent import LearnBot

st.set_page_config(page_title="LearnBot AI", page_icon="🧠", layout="wide")
bot = LearnBot()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_result" not in st.session_state:
    st.session_state.last_result = None

st.title("🧠 LearnBot — Chat-Learning AI Agent")
st.caption("BCA project prototype: persistent memory, retrieval learning, and user feedback.")

with st.sidebar:
    st.subheader("Learning dashboard")
    stats = bot.stats()
    st.metric("Chat messages", stats["chats"])
    st.metric("Approved memories", stats["memories"])
    st.metric("Learned Q&A examples", stats["examples"])
    st.metric("Helpful ratings", stats["helpful"])
    st.caption("Candidate facts are saved only after you approve them.")

chat_tab, learning_tab, memory_tab, history_tab = st.tabs(
    ["💬 Chat", "🎓 Learning", "🧠 Memory", "📜 History"])

with chat_tab:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    prompt = st.chat_input("Talk to LearnBot...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        result = bot.reply(prompt)
        st.session_state.last_result = result
        st.session_state.messages.append({"role": "assistant", "content": result["answer"]})
        st.rerun()

    result = st.session_state.last_result
    if result and result.get("id"):
        st.divider()
        if result.get("candidate_memory"):
            st.write("**Possible memory detected**")
            st.info(result["candidate_memory"])
            if st.button("Approve and remember this", key=f"remember_{result['id']}"):
                bot.save_memory(result["candidate_memory"])
                st.success("Memory saved.")
                st.session_state.last_result = None
                st.rerun()
        c1, c2 = st.columns(2)
        if c1.button("👍 Helpful", key=f"helpful_{result['id']}", use_container_width=True):
            bot.feedback(result["id"], "helpful")
            st.session_state.last_result = None
            st.rerun()
        if c2.button("👎 Improve answer", key=f"improve_{result['id']}", use_container_width=True):
            st.session_state.show_correction = True
        if st.session_state.get("show_correction", False):
            correction = st.text_area("What should the answer be?", key="correction")
            if st.button("Save correction"):
                if correction.strip():
                    bot.feedback(result["id"], "not_helpful", correction)
                    st.session_state.messages.append({"role": "assistant",
                        "content": "Correction saved as an example for future similar questions."})
                    st.session_state.last_result = None
                    st.session_state.show_correction = False
                    st.rerun()
                else:
                    st.warning("Please enter a correction.")

with learning_tab:
    st.subheader("Teach a question and answer")
    with st.form("teach"):
        q = st.text_input("Question", placeholder="What is Python?")
        a = st.text_area("Correct answer", placeholder="Python is a high-level programming language.")
        submit = st.form_submit_button("Save learning example")
    if submit:
        if q.strip() and a.strip():
            bot.teach_example(q, a)
            st.success("Example saved.")
        else:
            st.error("Fill in both fields.")

with memory_tab:
    st.subheader("Approved memories")
    st.write("Try saying `I like Python` in Chat, then approve the suggested memory.")
    memories = bot.memories()
    if memories:
        for memory in memories:
            c1, c2 = st.columns([5, 1])
            c1.write(memory["fact"])
            if c2.button("Delete", key=f"delete_{memory['id']}"):
                bot.delete_memory(memory["id"])
                st.rerun()
    else:
        st.info("No memories saved yet.")

with history_tab:
    st.subheader("Recent chat history")
    rows = bot.history()
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("Start chatting to create history.")
