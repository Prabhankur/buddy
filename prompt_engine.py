# prompt_engine.py - UPDATED
from dotenv import load_dotenv
import os
from groq import Groq
from profile_manager import get_person
from memory_manager import get_memory_summary, save_chat, detect_phase

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def build_system_prompt(person, memory_context, phase):
    return f"""
You are a smart messaging assistant helping craft perfect messages.

Person details:
- Relation: {person['relation']}
- Age: {person['age']}
- Gender: {person['gender']}
- Preferred Language: {person['language']}
- Default Tone: {person['default_tone']}
- Special Habits/Personality: {person['special_habits']}
- Special Days: {person['special_days']}

Current conversation phase: {phase}
- If phase is "greeting" → keep it light, short, warm
- If phase is "warmup" → casual small talk, no heavy topic yet
- If phase is "main_purpose" → get to the point naturally
- If phase is "followup" → reference what was said before

Memory (YOU vs THEM stored separately, prioritized by recency):
{memory_context}

IMPORTANT RULES:
1. YOU and THEY are different people — never mix their words
2. Recent conversations matter MORE than old ones
3. Match the current phase naturally
4. Generate exactly 3 options (short, medium, expressive)
5. Give 2-3 tips at the end labeled "💡 Tips:"

Format:
Option 1 (Short):
<message>

Option 2 (Medium):
<message>

Option 3 (Expressive):
<message>

💡 Tips:
- <tip 1>
- <tip 2>
"""

def generate_message(name, user_input, extra_context="",
                     chosen_option=None, they_said="",
                     you_tone="", they_tone=""):
    person = get_person(name)
    if not person:
        return

    # detect phase automatically
    phase = detect_phase(user_input)

    # pull prioritized memory
    memory_context = get_memory_summary(name, last_n=5)

    full_input = user_input
    if extra_context:
        full_input += f"\n\nExtra context: {extra_context}"

    print(f"\n⚙️ Generating [{phase}] message for {name}...\n")

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": build_system_prompt(person, memory_context, phase)},
            {"role": "user", "content": full_input}
        ]
    )

    result = response.choices[0].message.content
    print(result)

    # save with full detail
    save_chat(
        name=name,
        user_input=user_input,
        generated_options=result,
        chosen_option=chosen_option,
        they_said=they_said,
        phase=phase,
        you_tone=you_tone,
        they_tone=they_tone
    )

    return result