# app.py
import streamlit as st
from datetime import datetime
from profile_manager import add_person, get_person, load_profiles
from prompt_engine import generate_message
from memory_manager import get_memory_summary, clear_memory, save_chat

# ── Special Day Checker ────────────────────────────────────
def check_special_days(profiles):
    today = datetime.now().strftime("%d %B").lstrip("0")  # e.g. "15 August"
    alerts = []
    for name, data in profiles.items():
        special = data.get("special_days", "")
        if special:
            # check if today's date appears in special_days string
            day_part = today.split()[0]   # "15"
            month_part = today.split()[1] # "August"
            if day_part in special and month_part.lower() in special.lower():
                alerts.append((name, special))
    return alerts

# ── Page config ────────────────────────────────────────────
st.set_page_config(page_title="Chat Assistant", page_icon="💬", layout="centered")
st.title("💬 Chat Assistant")
st.caption("Say the right thing, every time.")

# ── Special Day Banner ─────────────────────────────────────
profiles = load_profiles()
alerts = check_special_days(profiles)
if alerts:
    for name, event in alerts:
        st.balloons()
        st.success(f"🎉 Today is special for **{name}** → {event}")
        if st.button(f"✨ Generate wish for {name}"):
            with st.spinner("Generating wish..."):
                result = generate_message(
                    name=name,
                    user_input=f"Today is their special day: {event}. Generate a warm wish.",
                    extra_context="This is an automatic special day wish."
                )
            st.markdown(result)

# ── Sidebar: Person selection ──────────────────────────────
st.sidebar.header("👤 Select Person")
people = list(profiles.keys())

if people:
    selected_person = st.sidebar.selectbox("Who are you chatting with?", people)
else:
    selected_person = None
    st.sidebar.info("No profiles yet. Add one below!")

# ── Sidebar: Add new person ────────────────────────────────
with st.sidebar.expander("➕ Add New Person"):
    new_name     = st.text_input("Name")
    new_relation = st.selectbox("Relation", ["friend", "close friend", "boss", "parent", "sibling", "crush", "client", "colleague"])
    new_age      = st.number_input("Age", min_value=1, max_value=100, value=22)
    new_gender   = st.selectbox("Gender", ["male", "female", "other"])
    new_language = st.selectbox("Language", ["Hinglish", "Hindi", "English"])
    new_tone     = st.selectbox("Default Tone", ["casual", "formal", "emotional", "humorous"])
    new_habits   = st.text_input("Special Habits / Personality")
    new_days     = st.text_input("Special Days (e.g. Birthday: 5 April)")

    if st.button("Save Profile"):
        if new_name.strip():
            add_person(new_name, new_relation, new_age, new_gender,
                       new_language, new_tone, new_habits, new_days)
            st.success(f"✅ Profile for {new_name} saved! Please refresh.")
        else:
            st.warning("Please enter a name.")

# ── Sidebar: Update person ─────────────────────────────────
with st.sidebar.expander("✏️ Update Person"):
    if people:
        update_name = st.selectbox("Select person to update", people, key="update_select")
        update_field = st.selectbox("Which field to update?", [
            "relation", "age", "gender", "language", "default_tone", "special_habits", "special_days"
        ])
        update_value = st.text_input("New value")
        if st.button("Update"):
            if update_value.strip():
                from profile_manager import update_person
                update_person(update_name, update_field, update_value)
                st.success(f"✅ {update_name}'s {update_field} updated! Please refresh.")
            else:
                st.warning("Please enter a new value.")
    else:
        st.info("No profiles yet.")

# ── Sidebar: Delete person ─────────────────────────────────
with st.sidebar.expander("🗑️ Delete Person"):
    if people:
        delete_name = st.selectbox("Select person to delete", people, key="delete_select")
        st.warning(f"This will permanently delete {delete_name} and all their memory!")
        if st.button("🗑️ Confirm Delete"):
            from profile_manager import delete_person
            delete_person(delete_name)
            st.success(f"✅ {delete_name} deleted! Please refresh.")
    else:
        st.info("No profiles yet.")
        
# ── Main: Chat section ─────────────────────────────────────
if selected_person:
    person = get_person(selected_person)
    st.subheader(f"Chatting context → {selected_person}")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Relation:** {person['relation']}")
        st.markdown(f"**Language:** {person['language']}")
    with col2:
        st.markdown(f"**Tone:** {person['default_tone']}")
        st.markdown(f"**Age:** {person['age']}")

    st.divider()

    # ── Message generator ──────────────────────────────────
    st.markdown("### ✍️ What do you want to say?")
    user_input    = st.text_area("Your message (any language, any tone)", placeholder="e.g. yaar kal milte hai kya?")
    extra_context = st.text_input("📎 Extra context (optional)", placeholder="e.g. we had a fight yesterday")

    if st.button("✨ Generate Messages", type="primary"):
        if user_input.strip():
            with st.spinner("Thinking..."):
                result = generate_message(
                    name=selected_person,
                    user_input=user_input,
                    extra_context=extra_context
                )
            st.session_state["last_result"] = result
            st.session_state["last_input"] = user_input
        else:
            st.warning("Please type what you want to say!")

    # ── Show results ───────────────────────────────────────
    if "last_result" in st.session_state:
        st.subheader("📩 Suggestions")
        st.markdown(st.session_state["last_result"])

        st.divider()

        # ── Their reply recorder ───────────────────────────
        # ── Their reply recorder ───────────────────────────────────
st.markdown("### 📥 What did they reply?")
their_reply   = st.text_area("Paste their reply", placeholder="e.g. haan yaar kal milte hai!")
you_tone      = st.text_input("Your tone (optional)", placeholder="e.g. casual, urgent, emotional")
they_tone     = st.text_input("Their tone (optional)", placeholder="e.g. happy, cold, excited")
chosen_option = st.text_input("Which option did you send?", placeholder="e.g. Option 2")

if st.button("💾 Save this exchange to memory"):
    save_chat(
        name=selected_person,
        user_input=st.session_state["last_input"],
        generated_options=st.session_state["last_result"],
        chosen_option=chosen_option,
        they_said=their_reply,
        you_tone=you_tone,
        they_tone=they_tone
    )
    st.success("💾 Exchange saved to memory!")

    st.divider()

    # ── Memory viewer ──────────────────────────────────────
    with st.expander("🧠 View Memory (past chats)"):
        memory = get_memory_summary(selected_person, last_n=10)
        st.text(memory)
        if st.button("🗑️ Clear Memory"):
            clear_memory(selected_person)
            st.success("Memory cleared!")