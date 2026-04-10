# memory_manager.py - IMPROVED VERSION
import json
import os
from datetime import datetime, timedelta

DATA_FILE = "data/profiles.json"

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

# ── Save chat with full detail ─────────────────────────────
def save_chat(name, user_input, generated_options, chosen_option=None,
              they_said="", phase="main_purpose", you_tone="", they_tone=""):
    profiles = load_profiles()
    if name not in profiles:
        print(f"❌ No profile for {name}")
        return

    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "phase": phase,                          # greeting/warmup/main_purpose/followup
        "you_said": user_input,                  # what YOU wanted to say
        "you_tone": you_tone or "not recorded",  # your tone
        "they_said": they_said or "not recorded",# what THEY replied
        "they_tone": they_tone or "not recorded",# their tone
        "chosen_option": chosen_option or "not recorded",
        "outcome": ""                            # filled later if needed
    }

    profiles[name]["chat_history"].append(entry)

    # ── Auto summarize if history too long ─────────────────
    if len(profiles[name]["chat_history"]) > 20:
        profiles[name] = auto_summarize(profiles[name])

    save_profiles(profiles)
    print(f"💾 Chat saved for {name}!")

# ── Get memory with priority system ───────────────────────
def get_memory_summary(name, last_n=5):
    profiles = load_profiles()
    if name not in profiles:
        return "No memory found."

    history = profiles[name].get("chat_history", [])
    old_summary = profiles[name].get("old_summary", "")

    if not history and not old_summary:
        return "No past conversations yet."

    now = datetime.now()
    today = []
    last_7_days = []
    older = []

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

    # ── Build memory context ───────────────────────────────
    memory_lines = []

    # Old summary first (background context)
    if old_summary:
        memory_lines.append(f"📚 Overall relationship context:\n{old_summary}\n")

    # Older chats — just key points
    if older:
        memory_lines.append("🗂️ Older conversations (summary):")
        for e in older[-3:]:  # last 3 older ones
            memory_lines.append(
                f"  [{e['timestamp']}] Phase: {e.get('phase','?')} | "
                f"You said: \"{e['you_said']}\" | "
                f"They replied: \"{e['they_said']}\""
            )

    # Last 7 days — good detail
    if last_7_days:
        memory_lines.append("\n📅 Last 7 days:")
        for e in last_7_days[-5:]:
            memory_lines.append(
                f"  [{e['timestamp']}]\n"
                f"  Phase: {e.get('phase','?')}\n"
                f"  YOU said: \"{e['you_said']}\" (tone: {e.get('you_tone','?')})\n"
                f"  THEY replied: \"{e['they_said']}\" (tone: {e.get('they_tone','?')})"
            )

    # Today — full detail, highest priority
    if today:
        memory_lines.append("\n🔥 Today's conversation (highest priority):")
        for e in today:
            memory_lines.append(
                f"  [{e['timestamp']}]\n"
                f"  Phase: {e.get('phase','?')}\n"
                f"  YOU said: \"{e['you_said']}\" (tone: {e.get('you_tone','?')})\n"
                f"  THEY replied: \"{e['they_said']}\" (tone: {e.get('they_tone','?')})\n"
                f"  Chosen: {e.get('chosen_option','?')}"
            )

    return "\n".join(memory_lines) if memory_lines else "No past conversations yet."

# ── Auto summarize old chats ───────────────────────────────
def auto_summarize(person_data):
    history = person_data.get("chat_history", [])
    if len(history) <= 20:
        return person_data

    # keep last 10 in full detail
    recent = history[-10:]
    to_summarize = history[:-10]

    # build simple summary from old entries
    summary_lines = []
    for e in to_summarize:
        summary_lines.append(
            f"[{e['timestamp']}] You said: '{e['you_said']}' | "
            f"They said: '{e['they_said']}'"
        )

    old_summary = person_data.get("old_summary", "")
    new_summary = old_summary + "\n" + "\n".join(summary_lines)

    person_data["chat_history"] = recent
    person_data["old_summary"] = new_summary.strip()

    print("📚 Auto-summarized old chats to save space!")
    return person_data

# ── Detect conversation phase ──────────────────────────────
def detect_phase(user_input):
    user_input_lower = user_input.lower()

    greetings = ["hi", "hello", "hii", "hey", "helo", "namaste", "namaskar", "kya haal", "kaise ho", "wassup"]
    warmup = ["kya chal raha", "kya kar rahe", "sab theek", "kaisa hai", "how are you", "what's up"]

    for word in greetings:
        if word in user_input_lower:
            return "greeting"

    for word in warmup:
        if word in user_input_lower:
            return "warmup"

    if len(user_input.split()) < 5:
        return "greeting"

    return "main_purpose"

# ── Clear memory ───────────────────────────────────────────
def clear_memory(name):
    profiles = load_profiles()
    if name in profiles:
        profiles[name]["chat_history"] = []
        profiles[name]["old_summary"] = ""
        save_profiles(profiles)
        print(f"🗑️ Memory cleared for {name}")