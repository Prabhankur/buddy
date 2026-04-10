# database.py
from dotenv import load_dotenv
import os
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

load_dotenv()

client = MongoClient(os.environ.get("MONGO_URI"), server_api=ServerApi('1'))
db = client["buddy_db"]
profiles_collection = db["profiles"]

# ── Profile functions ──────────────────────────────────────
def load_profiles():
    profiles = {}
    for doc in profiles_collection.find():
        name = doc["name"]
        doc.pop("_id")
        doc.pop("name")
        profiles[name] = doc
    return profiles

def save_profile(name, data):
    data["name"] = name
    profiles_collection.update_one(
        {"name": name},
        {"$set": data},
        upsert=True
    )

def get_person(name):
    doc = profiles_collection.find_one({"name": name})
    if doc:
        doc.pop("_id")
        doc.pop("name")
        return doc
    return None

def add_person(name, relation, age, gender, language,
               default_tone, special_habits="", special_days=""):
    data = {
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
        {"name": name},
        {"$set": data},
        upsert=True
    )
    print(f"✅ Profile for '{name}' saved to MongoDB!")

def delete_person(name):
    profiles_collection.delete_one({"name": name})
    print(f"🗑️ Profile for '{name}' deleted!")

def update_person(name, field, new_value):
    profiles_collection.update_one(
        {"name": name},
        {"$set": {field: new_value}}
    )
    print(f"✅ Updated {field} for '{name}'")

# ── Memory functions ───────────────────────────────────────
def save_chat(name, user_input, generated_options,
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
        "outcome": ""
    }
    profiles_collection.update_one(
        {"name": name},
        {"$push": {"chat_history": entry}}
    )

    # auto summarize if too long
    doc = profiles_collection.find_one({"name": name})
    if doc and len(doc.get("chat_history", [])) > 20:
        _auto_summarize(name, doc)

    print(f"💾 Chat saved for {name} in MongoDB!")

def _auto_summarize(name, doc):
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
        {"name": name},
        {"$set": {
            "chat_history": recent,
            "old_summary": new_summary.strip()
        }}
    )
    print("📚 Auto-summarized old chats!")

def get_memory_summary(name, last_n=5):
    from datetime import datetime
    doc = profiles_collection.find_one({"name": name})
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
            entry_time = datetime.strptime(entry["timestamp"], "%Y-%m-%d %H:%M")
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
        memory_lines.append("🗂️ Older conversations:")
        for e in older[-3:]:
            memory_lines.append(
                f"  [{e['timestamp']}] You: \"{e['you_said']}\" | "
                f"They: \"{e['they_said']}\""
            )

    if last_7_days:
        memory_lines.append("\n📅 Last 7 days:")
        for e in last_7_days[-5:]:
            memory_lines.append(
                f"  [{e['timestamp']}]\n"
                f"  YOU: \"{e['you_said']}\" (tone: {e.get('you_tone','?')})\n"
                f"  THEY: \"{e['they_said']}\" (tone: {e.get('they_tone','?')})"
            )

    if today:
        memory_lines.append("\n🔥 Today (highest priority):")
        for e in today:
            memory_lines.append(
                f"  [{e['timestamp']}]\n"
                f"  Phase: {e.get('phase','?')}\n"
                f"  YOU: \"{e['you_said']}\"\n"
                f"  THEY: \"{e['they_said']}\"\n"
                f"  Chosen: {e.get('chosen_option','?')}"
            )

    return "\n".join(memory_lines) if memory_lines else "No past conversations yet."

def clear_memory(name):
    profiles_collection.update_one(
        {"name": name},
        {"$set": {"chat_history": [], "old_summary": ""}}
    )
    print(f"🗑️ Memory cleared for {name}")

def list_people():
    profiles = load_profiles()
    for name, p in profiles.items():
        print(f"→ {name} | {p['relation']} | {p['language']} | {p['default_tone']} tone")