# profile_manager.py
import json
import os

DATA_FILE = "data/profiles.json"

# NEW - handles empty file too
def load_profiles():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            return {}
        return json.loads(content)

def save_profiles(profiles):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=4, ensure_ascii=False)

def add_person(name, relation, age, gender, language, default_tone, special_habits="", special_days=""):
    profiles = load_profiles()
    profiles[name] = {
        "relation": relation,          # friend, boss, parent, crush, client
        "age": age,
        "gender": gender,
        "language": language,          # Hindi, English, Hinglish
        "default_tone": default_tone,  # casual, formal, emotional, humorous
        "special_habits": special_habits,
        "special_days": special_days,
        "chat_history": []             # will store past conversations
    }
    save_profiles(profiles)
    print(f"✅ Profile for '{name}' saved!")

def get_person(name):
    profiles = load_profiles()
    if name in profiles:
        return profiles[name]
    else:
        print(f"❌ No profile found for '{name}'")
        return None

def list_people():
    profiles = load_profiles()
    if not profiles:
        print("No profiles yet.")
    else:
        print("📋 Saved profiles:")
        for name in profiles:
            p = profiles[name]
            print(f"  → {name} | {p['relation']} | {p['language']} | {p['default_tone']} tone")

# add these at the bottom of profile_manager.py

def delete_person(name):
    profiles = load_profiles()
    if name in profiles:
        del profiles[name]
        save_profiles(profiles)
        print(f"🗑️ Profile for '{name}' deleted!")
    else:
        print(f"❌ No profile found for '{name}'")

def update_person(name, field, new_value):
    profiles = load_profiles()
    if name not in profiles:
        print(f"❌ No profile found for '{name}'")
        return
    profiles[name][field] = new_value
    save_profiles(profiles)
    print(f"✅ Updated {field} for '{name}'")