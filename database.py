import os
import hashlib
from datetime import datetime
from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# Load environment variables
load_dotenv()

# ── Database Initialization ────────────────────────────────
client = MongoClient(os.environ.get("MONGO_URI"), server_api=ServerApi('1'))
db = client["buddy_db"]

# Define collections AFTER db is initialized
users_collection = db["users"]
profiles_collection = db["profiles"]

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
        return True, str(user["_id"])  # returns their unique user_id
    return False, "Wrong username or password!"


# ── All functions now take user_id ─────────────────────────

def load_profiles(user_id):
    profiles = {}
    for doc in profiles_collection.find({"user_id": str(user_id)}):
        name = doc.get("name")
        doc.pop("_id", None)
        doc.pop("name", None)
        doc.pop("user_id", None)
        profiles[name] = doc
    return profiles

def get_person(user_id, name):
    doc = profiles_collection.find_one({
        "user_id": str(user_id),
        "name": name
    })
    if doc:
        doc.pop("_id", None)
        doc.pop("name", None)
        doc.pop("user_id", None)
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
            f"[{e.get('timestamp', 'unknown')}] You: '{e.get('you_said', '')}' | "
            f"They: '{e.get('they_said', '')}'"
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
                entry.get("timestamp", ""), "%Y-%m-%d %H:%M"
            )
            days_ago = (now - entry_time).days
            if days_ago == 0:
                today.append(entry)
            elif days_ago <= 7:
                last_7_days.append(entry)
            else:
                older.append(entry)
        except ValueError:
            # Fallback if timestamp format is wrong or missing
            older.append(entry)

    memory_lines = []

    if old_summary:
        memory_lines.append(f"📚 Overall context:\n{old_summary}\n")

    if older:
        memory_lines.append("🗂️ Older:")
        for e in older[-3:]:
            memory_lines.append(
                f"  [{e.get('timestamp', '')}] "
                f"You: \"{e.get('you_said', '')}\" | "
                f"They: \"{e.get('they_said', '')}\""
            )

    if last_7_days:
        memory_lines.append("\n📅 Last 7 days:")
        for e in last_7_days[-5:]:
            memory_lines.append(
                f"  [{e.get('timestamp', '')}]\n"
                f"  YOU: \"{e.get('you_said', '')}\"\n"
                f"  THEY: \"{e.get('they_said', '')}\""
            )

    if today:
        memory_lines.append("\n🔥 Today:")
        for e in today:
            memory_lines.append(
                f"  [{e.get('timestamp', '')}]\n"
                f"  YOU: \"{e.get('you_said', '')}\"\n"
                f"  THEY: \"{e.get('they_said', '')}\""
            )

    return "\n".join(memory_lines)

def clear_memory(user_id, name):
    profiles_collection.update_one(
        {"user_id": str(user_id), "name": name},
        {"$set": {"chat_history": [], "old_summary": ""}}
    )
    print(f"🗑️ Memory cleared for {name}")