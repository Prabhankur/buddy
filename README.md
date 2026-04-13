Buddy — AI-Powered Personal Communication Assistant

PROBLEM
Communicating effectively with different people requires constantly adjusting tone, language, and word choice.
A message to your boss needs to be formal, while thesame information to a friend should be casual.
Managing this mental load across multiple relationships is exhausting and often leads to miscommunication.

SOLUTION
Buddy is an AI assistant that understands WHO you are talking to and helps you say the RIGHT thing in theRIGHT way.
You type what you want to say in any language or tone — Buddy converts it into 3 perfectly crafted message options suited for that specific person.

HOW IT WORKS
1. Create a profile for each person in your life storing their relation, age, language preference, personality traits and special days

2. Tell Buddy what you want to say — in any language, any tone, as raw as you want

3. Buddy uses the person's profile + past conversation memory to generate 3 tailored message options

4. Copy the message you like and send it

5. Paste their reply back — Buddy remembers it for next time, building a rich conversation memory

TECHNICAL HIGHLIGHTS
→ RAG-inspired memory architecture storing conversations
  separately for sender and receiver, prioritized by
  recency (today → last 7 days → older → summary)

→ Automatic conversation phase detection
  (greeting / warmup / main purpose / followup)
  ensuring messages feel natural and sequential

→ Auto-summarization of old conversations to prevent
  context window overflow while preserving key context

→ Multi-user authentication with password hashing
  ensuring complete data privacy between users

→ Dual interface — Streamlit web app for detailed use
  and Telegram bot for daily mobile use, both connected
  to the same MongoDB cloud database

→ Docker containerization for consistent deployment

TECH STACK
Language    → Python
LLM         → Groq API (Llama 3.3 70B)
Database    → MongoDB Atlas (cloud)
Web App     → Streamlit
Bot         → Python Telegram Bot API
Container   → Docker
Hosting     → GitHub
