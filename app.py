import streamlit as st
from database import register_user, login_user, add_person, get_person, load_profiles, get_memory_summary, clear_memory, save_chat, update_person, delete_person
from prompt_engine import generate_message
from datetime import datetime
from database import (add_person, get_person, load_profiles, get_memory_summary,
                      clear_memory, save_chat, update_person, delete_person,
                      get_todos, add_todo, toggle_todo, delete_todo,
                      get_todays_special_people, get_all_special_days)


# ── Persistent login using query params ────────────────────
def get_user_id():
    # check session state first
    if "user_id" in st.session_state:
        return st.session_state["user_id"], st.session_state.get("username", "")
    return None, None

def save_login(user_id, username):
    st.session_state["user_id"] = user_id
    st.session_state["username"] = username

def logout():
    st.session_state.clear()
    st.rerun()

# ── Auth page ──────────────────────────────────────────────
def auth_page():
    st.set_page_config(page_title="Chat Assistant", page_icon="💬")
    st.title("💬 Chat Assistant")
    st.caption("Say the right thing, every time.")

    tab1, tab2 = st.tabs(["🔑 Login", "📝 Register"])

    with tab1:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login", type="primary"):
            if username and password:
                success, result = login_user(username, password)
                if success:
                    save_login(result, username)
                    st.rerun()
                else:
                    st.error(result)
            else:
                st.warning("Please fill all fields!")

    with tab2:
        new_username = st.text_input("Choose Username", key="reg_user")
        new_password = st.text_input("Choose Password", type="password", key="reg_pass")
        confirm_pass = st.text_input("Confirm Password", type="password", key="reg_confirm")
        if st.button("Register", type="primary"):
            if new_username and new_password and confirm_pass:
                if new_password != confirm_pass:
                    st.error("Passwords don't match!")
                else:
                    success, msg = register_user(new_username, new_password)
                    if success:
                        st.success("✅ Account created! Please login.")
                    else:
                        st.error(msg)
            else:
                st.warning("Please fill all fields!")

# ── Check login ────────────────────────────────────────────
user_id, username = get_user_id()

if not user_id:
    auth_page()
    st.stop()

# ── Page config (only after login) ────────────────────────
st.set_page_config(page_title="Chat Assistant", page_icon="💬", layout="centered")
st.title("💬 Chat Assistant")
st.caption("Say the right thing, every time.")

# ── Sidebar logout ─────────────────────────────────────────
st.sidebar.caption(f"👤 Logged in as: **{username}**")
if st.sidebar.button("🚪 Logout"):
    logout()

# ── Special Day Checker ────────────────────────────────────
# def check_special_days(profiles):
#     today = datetime.now().strftime("%d %B").lstrip("0")
#     alerts = []
#     for name, data in profiles.items():
#         special = data.get("special_days", "")
#         if special:
#             day_part = today.split()[0]
#             month_part = today.split()[1]
#             if day_part in special and month_part.lower() in special.lower():
#                 alerts.append((name, special))
#     return alerts

# ── Load profiles ──────────────────────────────────────────
profiles = load_profiles(user_id)

# # ── Special Day Banner ─────────────────────────────────────
# alerts = check_special_days(profiles)
# if alerts:
#     for name, event in alerts:
#         st.balloons()
#         st.success(f"🎉 Today is special for **{name}** → {event}")
#         if st.button(f"✨ Generate wish for {name}"):
#             with st.spinner("Generating wish..."):
#                 result = generate_message(
#                     user_id=user_id,
#                     name=name,
#                     user_input=f"Today is their special day: {event}. Generate a warm wish.",
#                     extra_context="This is an automatic special day wish."
#                 )
#             st.markdown(result)

# ── Special Day Planner Section ────────────────────────────
todays_specials = get_todays_special_people(user_id)
todos_today = get_todos(user_id)
pending = [t for t in todos_today if not t["completed"]]
completed = [t for t in todos_today if t["completed"]]

# only show planner if there are special people OR pending todos
if todays_specials or pending:
    st.markdown("---")
    st.markdown("## 🎉 Today's Special Day Planner")

    # ── Show who has special day ───────────────────────────
    if todays_specials:
        for name, event in todays_specials:
            st.info(f"🎂 **{name}** — {event}")

    col_left, col_right = st.columns([2, 1])

    with col_left:
        # ── Pending todos ──────────────────────────────────
        if pending:
            st.markdown("### 📋 To-Do")
            for todo in pending:
                col1, col2, col3 = st.columns([0.1, 0.7, 0.2])
                with col1:
                    if st.checkbox("", key=f"check_{todo['_id']}"):
                        toggle_todo(todo["_id"])
                        st.rerun()
                with col2:
                    person_tag = f"**[{todo['person_name']}]** " if todo["person_name"] else ""
                    st.markdown(f"{person_tag}{todo['task']}")
                with col3:
                    if st.button("🗑️", key=f"del_{todo['_id']}"):
                        delete_todo(todo["_id"])
                        st.rerun()

        # ── Completed todos ────────────────────────────────
        if completed:
            with st.expander(f"✅ Completed ({len(completed)})"):
                for todo in completed:
                    col1, col2, col3 = st.columns([0.1, 0.7, 0.2])
                    with col1:
                        if st.checkbox("", value=True, key=f"check_{todo['_id']}"):
                            pass
                        else:
                            toggle_todo(todo["_id"])
                            st.rerun()
                    with col2:
                        person_tag = f"**[{todo['person_name']}]** " if todo["person_name"] else ""
                        st.markdown(f"~~{person_tag}{todo['task']}~~")
                    with col3:
                        if st.button("🗑️", key=f"del_{todo['_id']}"):
                            delete_todo(todo["_id"])
                            st.rerun()

    with col_right:
        # ── Add new todo ───────────────────────────────────
        st.markdown("### ➕ Add Task")
        new_task = st.text_input("Task", placeholder="e.g. Send birthday cake")

        # person tag optional
        person_options = ["None"] + list(profiles.keys())
        tag_person = st.selectbox("Tag a person (optional)", person_options)
        tag_person = "" if tag_person == "None" else tag_person

        if st.button("Add Task", type="primary"):
            if new_task.strip():
                add_todo(
                    user_id=user_id,
                    task=new_task,
                    person_name=tag_person
                )
                st.success("✅ Task added!")
                st.rerun()
            else:
                st.warning("Please enter a task!")

        # ── Quick wish button ──────────────────────────────
        if todays_specials:
            st.markdown("---")
            st.markdown("### 💌 Quick Wish")
            wish_person = st.selectbox(
                "Generate wish for:",
                [n for n, _ in todays_specials]
            )
            if st.button("✨ Generate Wish"):
                event = dict(todays_specials)[wish_person]
                with st.spinner("Generating..."):
                    result = generate_message(
                        user_id=user_id,
                        name=wish_person,
                        user_input=f"Today is their special day: {event}. Generate a warm wish.",
                        extra_context="Automatic special day wish."
                    )
                st.markdown(result)

    st.markdown("---")



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
    new_days = st.text_input(
    "Special Days",
    placeholder="e.g. Birthday: 12 April, Anniversary: 5 June, Joining: 13 April"
)

    if st.button("Save Profile"):
        if new_name.strip():
            add_person(user_id, new_name, new_relation, new_age,
                      new_gender, new_language, new_tone, new_habits, new_days)
            st.success(f"✅ Profile for {new_name} saved!")
            st.rerun()  # ← rerun instead of manual refresh
        else:
            st.warning("Please enter a name.")

# ── Sidebar: Update person ─────────────────────────────────
with st.sidebar.expander("✏️ Update Person"):
    if people:
        upd_name  = st.selectbox("Select person", people, key="update_select")
        upd_field = st.selectbox("Field to update", [
            "relation", "age", "gender", "language",
            "default_tone", "special_habits", "special_days"
        ])
        upd_value = st.text_input(
            "New value",
            placeholder="e.g. Birthday: 12 April, Anniversary: 5 June"
        )
        
        if st.button("Update"):
            if upd_value.strip():
                update_person(user_id, upd_name, upd_field, upd_value)
                st.success(f"✅ Updated!")
                st.rerun()
            else:
                st.warning("Please enter a value.")
    else:
        st.info("No profiles yet.")

# ── Sidebar: Delete person ─────────────────────────────────
with st.sidebar.expander("🗑️ Delete Person"):
    if people:
        del_name = st.selectbox("Select person", people, key="delete_select")
        st.warning(f"This will permanently delete {del_name}!")
        if st.button("🗑️ Confirm Delete"):
            delete_person(user_id, del_name)
            st.success(f"✅ {del_name} deleted!")
            st.rerun()
    else:
        st.info("No profiles yet.")

# ── Sidebar: All Special Days ──────────────────────────────
with st.sidebar.expander("🗓️ All Special Days"):
    all_special = get_all_special_days(user_id)
    if all_special:
        # group by person
        grouped = {}
        for item in all_special:
            if item["name"] not in grouped:
                grouped[item["name"]] = []
            grouped[item["name"]].append(item["event"])

        for name, events in grouped.items():
            st.markdown(f"**{name}**")
            for event in events:
                st.markdown(f"  • {event}")
            st.markdown("")
    else:
        st.info("No special days added yet.")

# ── Main: Chat section ─────────────────────────────────────
if selected_person:
    person = get_person(user_id, selected_person)
    st.subheader(f"Chatting context → {selected_person}")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Relation:** {person['relation']}")
        st.markdown(f"**Language:** {person['language']}")
    with col2:
        st.markdown(f"**Tone:** {person['default_tone']}")
        st.markdown(f"**Age:** {person['age']}")

    st.divider()

    st.markdown("### ✍️ What do you want to say?")
    user_input    = st.text_area("Your message (any language, any tone)",
                                  placeholder="e.g. yaar kal milte hai kya?")
    extra_context = st.text_input("📎 Extra context (optional)",
                                   placeholder="e.g. we had a fight yesterday")

    if st.button("✨ Generate Messages", type="primary"):
        if user_input.strip():
            with st.spinner("Thinking..."):
                result = generate_message(
                    user_id=user_id,
                    name=selected_person,
                    user_input=user_input,
                    extra_context=extra_context
                )
            st.session_state["last_result"] = result
            st.session_state["last_input"]  = user_input
        else:
            st.warning("Please type what you want to say!")

    if "last_result" in st.session_state:
        st.subheader("📩 Suggestions")
        st.markdown(st.session_state["last_result"])
        st.divider()

        st.markdown("### 📥 What did they reply?")
        their_reply   = st.text_area("Paste their reply",
                                      placeholder="e.g. haan yaar kal milte hai!")
        you_tone      = st.text_input("Your tone (optional)",
                                       placeholder="e.g. casual, urgent, emotional")
        they_tone     = st.text_input("Their tone (optional)",
                                       placeholder="e.g. happy, cold, excited")
        chosen_option = st.text_input("Which option did you send?",
                                       placeholder="e.g. Option 2")

        if st.button("💾 Save this exchange to memory"):
            save_chat(
                user_id=user_id,
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

        with st.expander("🧠 View Memory (past chats)"):
            mem = get_memory_summary(user_id, selected_person, last_n=10)
            st.text(mem)
            if st.button("🗑️ Clear Memory"):
                clear_memory(user_id, selected_person)
                st.success("Memory cleared!")
                st.rerun()