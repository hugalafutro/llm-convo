# LLM Convo

*Most of this was stitched together by language models. I nod along when people explain the code. If something catches fire, that is between you and your firewall.*

**LLM Convo** is a small web app that sits between two OpenAI-compatible chat APIs. You connect each side to its own backend (local or remote), type an opening line, and watch the two models trade replies in real time. The server streams the dialogue to your browser with Server-Sent Events.

![LLM Convo](screenshot-new.png)

## Features

- **Two endpoints** — Each side has its own URL, optional API key, character name, and optional system prompt. **Connect** checks the backend by calling `GET {your-base-url}/v1/models`.
- **Model picker** — After a successful connect, a dropdown lists models from that endpoint; your choice is remembered in the browser.
- **Turn-based dialogue** — You set how many **exchange rounds** to run (1–30). Each round is both models speaking once, in order. The full thread (plus your initial prompt) is sent back into context so the conversation stays coherent.
- **Streaming** — Replies stream in as they are generated. **Stop** closes the stream; **Clear** wipes the transcript and resets server-side turn state.
- **Reasoning-friendly** — If the backend sends thinking tokens (`reasoning` / `reasoning_content`), they appear in a collapsible **Thinking** block above the visible answer.
- **Per-message stats** — Footer on each completion: timestamp, model id, token count, and tokens per second.
- **Markdown in bubbles** — Basic formatting (code, bold, italics, paragraphs) with escaping so random model output does not run script in your page.
- **Dark and light themes** — Toggle in the header; preference is saved locally.
- **Toasts and connection state** — Inline feedback when things connect, fail, or finish; connect buttons show when each side is live.
- **Local persistence** — Endpoint fields, keys, names, prompts, and theme live in **browser localStorage** (not on the server).
- **Docker-ready** — Compose file exposes the UI and includes a health check against `/health`.

## Run locally

You need **Python 3.12+**.

```bash
git clone https://github.com/hugalafutro/llm-convo.git
cd llm-convo
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000`.

## Docker

```bash
git clone https://github.com/hugalafutro/llm-convo.git
cd llm-convo
docker compose build
docker compose up -d
```

Follow logs:

```text
llm-convo  | INFO:     Started server process [1]
llm-convo  | INFO:     Waiting for application startup.
llm-convo  | INFO:     Application startup complete.
llm-convo  | INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

Then open **`http://localhost:5234`** (host port **5234** is mapped to the app on port **8000** inside the container).

## Pointing at your backends

The app always calls `{base_url}/v1/models` and `{base_url}/v1/chat/completions`. Enter the **base URL only**—do **not** append `/v1` yourself, or the paths will be wrong.

Examples that work with many setups (adjust host and port):

- [LM Studio](https://github.com/lmstudio-ai): `http://127.0.0.1:1234`
- [koboldcpp](https://github.com/LostRuins/koboldcpp): `http://192.168.x.x:5001` (use the host/port where the OpenAI-compatible API is served)

Click **Connect** for each side. When both show connected, enter your opening prompt and press **Send** (or Enter).

## Example system prompt

Optional copy-paste for both characters while testing:

```text
You are an AI with a distinct personality. Respond naturally to the given prompt, as if in a real conversation. Keep your reply focused and concise, ideally around 50-75 words. Don't continue the conversation beyond your response or roleplay as anyone else. Engage with the topic, add your perspective, or ask a relevant question, but always conclude your response naturally. Avoid overly formal or flowery language - aim for a casual, friendly tone.
```

## License

Licensed under the MIT License — see [LICENSE](LICENSE).

## Outputs, screenshots, and not-lawyers

*My “lawyer” was still an LLM. This is not legal advice—just common sense wrapped in anxiety.*

This project is a hobby experiment. Anything the models say comes from **their** weights and your backends, not from me. I do not endorse or control that text. You are responsible for how you use the app, what you run against it, and what you screenshot or post. There is no promise that replies are accurate, safe, or appropriate. For warranty and liability limits on the **software itself**, read the MIT license.

---

## How this repo was built

I used 2 (later 3) LLMs (Claude Sonnet 3.5 and chatgpt-4o-latest (later locally running Qwen2.5-Coder-7B-Instruct)) to write an app that would let 2 AI LLMs with openai compatible api endpoints talk to each other. I have zero experience with python. After running out of daily allowance on both Anthropic and OpenAI I got what's in this repo more or less. Was more of an experiment if I can make an app without any experience more than anything else. I used [open-webui](https://github.com/open-webui/open-webui) as frontend to "develop" this.

I successfully managed to implement some stuff while continuing the conversation in [open-webui](https://github.com/open-webui/open-webui) with locally running [Qwen2.5-Coder-7B-Instruct-Q8_0.gguf](https://huggingface.co/bartowski/Qwen2.5-Coder-7B-Instruct-GGUF) in [koboldcpp](https://github.com/LostRuins/koboldcpp)

The *almost* whole conversation exported to pdf: [chat-LLM Convo development.pdf](https://github.com/user-attachments/files/17450061/chat-LLM.Convo.development.pdf)
*(I had to remove posts with pictures as I was running out of quota and later using model which could not ingest images. So if there is a jarring disconnect or a missing reply it was a reply with picture.)*
