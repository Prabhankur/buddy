# database.py
from dotenv import load_dotenv
import os
import hashlib
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

load_dotenv()

# ── Connect to MongoDB FIRST ───────────────────────────────
client = MongoClient(os.environ.get("MONGO_URI"), server_api=ServerApi('1'))
db = client["buddy_db"]
profiles_collection = db["profiles"]
users_collection = db["users"]  # ✅ now db exists
# ── Special Day Todo functions ─────────────────────────────
todos_collection = db["todos"]

# ── User account functions ─────────────────────────────────
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    existing = users_collection.find_one({"username": username})
    if existing:
        return False, "Username already exists!"
    users_collection.insert_one({
        "username": username,
        "password": hash_password(password),
    })
    return True, "Account created!"

def login_user(username, password):
    user = users_collection.find_one({
        "username": username,
        "password": hash_password(password)
    })
    if user:
        return True, str(user["_id"])
    return False, "Wrong username or password!"


# ── All functions now take user_id ─────────────────────────

def load_profiles(user_id):
    profiles = {}
    for doc in profiles_collection.find({"user_id": str(user_id)}):
        name = doc["name"]
        doc.pop("_id")
        doc.pop("name")
        doc.pop("user_id")
        profiles[name] = doc
    return profiles

def get_person(user_id, name):
    doc = profiles_collection.find_one({
        "user_id": str(user_id),
        "name": name
    })
    if doc:
        doc.pop("_id")
        doc.pop("name")
        doc.pop("user_id")
        return doc
    return None

def add_person(user_id, name, relation, age, gender, language,
               default_tone, special_habits="", special_days=""):
    data = {
        "user_id": str(user_id),
        "name": name,
        "relation": relation,
        "age": age,
        "gender": gender,
        "language": language,
        "default_tone": default_tone,
        "special_habits": special_habits,
        "special_days": special_days,
        "chat_history": [],
        "old_summary": ""
    }
    profiles_collection.update_one(
        {"user_id": str(user_id), "name": name},
        {"$set": data},
        upsert=True
    )
    print(f"✅ Profile for '{name}' saved!")

def delete_person(user_id, name):
    profiles_collection.delete_one({
        "user_id": str(user_id),
        "name": name
    })
    print(f"🗑️ '{name}' deleted!")

def update_person(user_id, name, field, new_value):
    profiles_collection.update_one(
        {"user_id": str(user_id), "name": name},
        {"$set": {field: new_value}}
    )
    print(f"✅ Updated {field} for '{name}'")

def save_chat(user_id, name, user_input, generated_options,
              chosen_option=None, they_said="",
              phase="main_purpose", you_tone="", they_tone=""):
    from datetime import datetime
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "phase": phase,
        "you_said": user_input,
        "you_tone": you_tone or "not recorded",
        "they_said": they_said or "not recorded",
        "they_tone": they_tone or "not recorded",
        "chosen_option": chosen_option or "not recorded",
    }
    profiles_collection.update_one(
        {"user_id": str(user_id), "name": name},
        {"$push": {"chat_history": entry}}
    )

    doc = profiles_collection.find_one({
        "user_id": str(user_id),
        "name": name
    })
    if doc and len(doc.get("chat_history", [])) > 20:
        _auto_summarize(user_id, name, doc)

    print(f"💾 Chat saved for {name}!")

def _auto_summarize(user_id, name, doc):
    history = doc.get("chat_history", [])
    recent = history[-10:]
    to_summarize = history[:-10]

    lines = []
    for e in to_summarize:
        lines.append(
            f"[{e['timestamp']}] You: '{e['you_said']}' | "
            f"They: '{e['they_said']}'"
        )

    old_summary = doc.get("old_summary", "")
    new_summary = old_summary + "\n" + "\n".join(lines)

    profiles_collection.update_one(
        {"user_id": str(user_id), "name": name},
        {"$set": {
            "chat_history": recent,
            "old_summary": new_summary.strip()
        }}
    )

def get_memory_summary(user_id, name, last_n=5):
    from datetime import datetime
    doc = profiles_collection.find_one({
        "user_id": str(user_id),
        "name": name
    })
    if not doc:
        return "No memory found."

    history = doc.get("chat_history", [])
    old_summary = doc.get("old_summary", "")

    if not history and not old_summary:
        return "No past conversations yet."

    now = datetime.now()
    today, last_7_days, older = [], [], []

    for entry in history:
        try:
            entry_time = datetime.strptime(
                entry["timestamp"], "%Y-%m-%d %H:%M"
            )
            days_ago = (now - entry_time).days
            if days_ago == 0:
                today.append(entry)
            elif days_ago <= 7:
                last_7_days.append(entry)
            else:
                older.append(entry)
        except:
            older.append(entry)

    memory_lines = []

    if old_summary:
        memory_lines.append(f"📚 Overall context:\n{old_summary}\n")

    if older:
        memory_lines.append("🗂️ Older:")
        for e in older[-3:]:
            memory_lines.append(
                f"  [{e['timestamp']}] "
                f"You: \"{e['you_said']}\" | "
                f"They: \"{e['they_said']}\""
            )

    if last_7_days:
        memory_lines.append("\n📅 Last 7 days:")
        for e in last_7_days[-5:]:
            memory_lines.append(
                f"  [{e['timestamp']}]\n"
                f"  YOU: \"{e['you_said']}\"\n"
                f"  THEY: \"{e['they_said']}\""
            )

    if today:
        memory_lines.append("\n🔥 Today:")
        for e in today:
            memory_lines.append(
                f"  [{e['timestamp']}]\n"
                f"  YOU: \"{e['you_said']}\"\n"
                f"  THEY: \"{e['they_said']}\""
            )

    return "\n".join(memory_lines)

def clear_memory(user_id, name):
    profiles_collection.update_one(
        {"user_id": str(user_id), "name": name},
        {"$set": {"chat_history": [], "old_summary": ""}}
    )
    print(f"🗑️ Memory cleared for {name}")

# ── Todo functions ─────────────────────────────────────────
todos_collection = db["todos"]

def get_todos(user_id, date=None):
    from datetime import datetime
    from bson import ObjectId
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    todos = list(todos_collection.find({
        "user_id": str(user_id),
        "date": date
    }))
    for t in todos:
        t["_id"] = str(t["_id"])
    return todos

def add_todo(user_id, task, person_name="", date=None):
    from datetime import datetime
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    todos_collection.insert_one({
        "user_id": str(user_id),
        "task": task,
        "person_name": person_name,
        "date": date,
        "completed": False,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    })

def toggle_todo(todo_id):
    from bson import ObjectId
    try:
        obj_id = ObjectId(todo_id)
        todo = todos_collection.find_one({"_id": obj_id})
        if todo:
            todos_collection.update_one(
                {"_id": obj_id},
                {"$set": {"completed": not todo["completed"]}}
            )
    except Exception as e:
        print(f"toggle error: {e}")

def delete_todo(todo_id):
    from bson import ObjectId
    try:
        todos_collection.delete_one({"_id": ObjectId(todo_id)})
    except Exception as e:
        print(f"delete error: {e}")

def get_todays_special_people(user_id):
    from datetime import datetime
    profiles = load_profiles(user_id)
    today = datetime.now().strftime("%d %B").lstrip("0")
    day_part = today.split()[0]
    month_part = today.split()[1]
    specials = []
    for name, data in profiles.items():
        special = data.get("special_days", "")
        if not special:
            continue
        # split by comma to handle multiple special days
        events = [e.strip() for e in special.split(",")]
        for event in events:
            if day_part in event and month_part.lower() in event.lower():
                specials.append((name, event))  # each event separately
    return specials

def get_all_special_days(user_id):
    from datetime import datetime
    profiles = load_profiles(user_id)
    today = datetime.now().strftime("%d %B").lstrip("0")
    all_days = []
    for name, data in profiles.items():
        special = data.get("special_days", "")
        if not special:
            continue
        events = [e.strip() for e in special.split(",")]
        for event in events:
            all_days.append({
                "name": name,
                "event": event,
                "relation": data.get("relation", ""),
            })
    return all_days

