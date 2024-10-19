# llm-convo
I used 2 LLM's (Claude Sonnet 3.5 and gpt-4o) to write an app that would let 2 openai compatible endpoints talk to each other. 
After running out of daily allowance on both Anthropic and OpenAI I got what's in this repo. I have zero experience with python. Was more of an experiment if I can make an app without any experience more than anything else.

ONLY TESTED with koboldcpp openai compatible endpoints

- Dark/Light theme
- Number of Exchanges between 3 and 30
- Supports streaming/interrupting of responses
- Supports different system prompt for each endpoint
- The endpoint addresses and system prompts are stored in browser Local Storage



![image_2024-10-19_21-06-29](https://github.com/user-attachments/assets/8e04143e-9908-4d7c-80ff-8d8a5bf07c80)


To try it out in docker:
```
git clone https://github.com/hugalafutro/llm-convo.git
cd llm-convo
docker compose build
docker compose up -d
```

Check docker logs all is fine:
```
llm-convo  |  * Serving Flask app 'app.py'
llm-convo  |  * Debug mode: off
llm-convo  | WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
llm-convo  |  * Running on all addresses (0.0.0.0)
llm-convo  |  * Running on http://127.0.0.1:5000
llm-convo  |  * Running on http://172.26.0.2:5000
llm-convo  | Press CTRL+C to quit
```

- Visit `http://0.0.0.0:5234` 
- Write the Intial Prompt in the bottom text input area and click the Send button