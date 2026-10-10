# KOS Portfolio Chatbot

An AI assistant for [kamukamaosbertl.github.io](https://kamukamaosbertl.github.io) that answers visitors' questions about **Kamukama Osbert** (skills, projects, services) and **Virtual Room Beddings & Comfort** (linen products, ordering).

Built with **Python + FastAPI** using **Retrieval-Augmented Generation (RAG)**: every question first searches the knowledge files, then only the matching facts are given to the AI model, so it answers from real information instead of making things up.

```
Visitor ──► chat bubble (GitHub Pages) ──► POST /chat (FastAPI on Render)
                                               │
                                   1. search knowledge/*.md (BM25)
                                   2. build prompt with the top sections
                                   3. call AI model (Gemini / Groq / OpenAI)
                                               │
Visitor ◄──────────── short, grounded answer ◄─┘
```

## Project structure

| Path | What it is |
|---|---|
| `knowledge/*.md` | **What the bot knows.** Edit these to change its answers. |
| `app/retrieval.py` | Splits knowledge into sections and ranks them (BM25 search). |
| `app/prompt.py` | System prompt and rules (no invented prices, send customers to WhatsApp). |
| `app/llm.py` | Calls any OpenAI-compatible AI API. |
| `app/ratelimit.py` | 20 messages per visitor per 5 minutes, to protect your credits. |
| `app/service.py` | Ties it together; works without a key in "test mode". |
| `app/main.py` | FastAPI app: `POST /chat`, `GET /health`, CORS for your site only. |
| `tests/` | Unit tests (no API key needed). |

## Run it on your computer

```bash
python -m venv venv
venv\Scripts\activate            # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env           # Mac/Linux: cp .env.example .env  → then paste your key in .env
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000/docs**, click **POST /chat → Try it out**, and send `{"message": "What is ClariBox?"}`.
Without a key it runs in **test mode** and replies with the matching knowledge section, which is handy for checking retrieval.

Run the tests: `python -m unittest discover -s tests -v`

## Get a free AI key

**Google Gemini (default):** go to [aistudio.google.com](https://aistudio.google.com) → **Get API key** → create a key.
Defaults already set: `LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai`, `LLM_MODEL=gemini-2.5-flash`.
Model names change over time; if you get a "model not found" error, check the current model list in AI Studio and update `LLM_MODEL`.

**Or Groq:** [console.groq.com](https://console.groq.com) → API Keys. Set `LLM_BASE_URL=https://api.groq.com/openai/v1` and `LLM_MODEL` to a model listed in your Groq console.

Never put the key in your website code or commit it to GitHub. It only goes in `.env` (local) or Render's environment settings.

## Deploy to Render (free)

1. Push this folder to a **new GitHub repo**, e.g. `kos-chatbot`.
2. Go to [render.com](https://render.com), sign in with GitHub → **New + → Blueprint** → pick the repo. Render reads `render.yaml`.
3. When asked, paste your key into **LLM_API_KEY** → **Apply**.
4. After it builds, open `https://<your-service>.onrender.com/health`. You should see `"ai": true`.

The free plan sleeps after about 15 minutes of no visitors, so the first message after a sleep can take up to a minute. The chat bubble tells the visitor it's "waking up".

## Add the chat bubble to the website

Copy `js/chatbot.js` and `css/chatbot.css` into the website repo, then add these two lines just before `</body>` in `index.html` (use your real Render URL):

```html
<link href="css/chatbot.css" rel="stylesheet">
<script src="js/chatbot.js" data-api="https://kos-chatbot.onrender.com"></script>
```

## Teach it new things

Add or edit sections in `knowledge/*.md`. Each `## Heading` becomes one searchable section, so keep each heading about one topic. Push to GitHub and Render redeploys automatically.
Good next additions: Virtual Room prices and delivery areas, opening hours, and more detail on each project.

## Ideas to upgrade

- Swap BM25 for embeddings + **FAISS** (same as ClariBox) in `KnowledgeBase.search`.
- Log anonymous questions to see what visitors ask most.
- Connect the same `/chat` API to the WhatsApp Cloud API.
