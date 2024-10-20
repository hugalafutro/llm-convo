# LLM Convo
***`I have no idea what I'm doing it was the LLMs I swear`***

I used 2 (later 3) LLMs (Claude Sonnet 3.5 and chatgpt-4o-latest (later locally running Qwen2.5-Coder-7B-Instruct)) to write an app that would let 2 LLMs with openai compatible api endpoints talk to each other. I have zero experience with python. After running out of daily allowance on both Anthropic and OpenAI I got what's in this repo more or less. Was more of an experiment if I can make an app without any experience more than anything else. I used [open-webui](https://github.com/open-webui/open-webui) as frontend to "develop" this.

_edit: I successfully managed to implement some stuff while continuing the conversation in [open-webui](https://github.com/open-webui/open-webui) with locally running [Qwen2.5-Coder-7B-Instruct-Q6_K_L.gguf](https://huggingface.co/bartowski/Qwen2.5-Coder-7B-Instruct-GGUF) in [koboldcpp](https://github.com/LostRuins/koboldcpp)_

The *almost* whole conversation exported to pdf: [chat-LLM Convo development.pdf](https://github.com/user-attachments/files/17450061/chat-LLM.Convo.development.pdf)
*(I had to remove posts with pictures as I was running out of quota and later using model which could not ingest images. So if there is a jarring disconnect or a missing reply it was a reply with picture.)*

# ONLY TESTED with [koboldcpp](https://github.com/LostRuins/koboldcpp) openai compatible endpoints

- Dark/Light theme
- Number of Exchanges between 3 and 30
- Supports streaming/interrupting of responses
- The endpoint addresses and system prompts are stored in browser Local Storage
- Timestamps, model names, tokens/second - oh my!
- Supports different system prompt for each endpoint
- Buttons change colors with state

Involving in third LLM (locally running Qwen2.5-Coder-7B-Instruct-Q6_K_L.gguf) I was able to bribe it with enough *virtual head pats* to implement sending of the whole conversation with the prompt. Previously the models would only directly respond to the other models last output. Now they "remember".

I used the following system prompt for both while testing:
```
You are an AI with a distinct personality. Respond naturally to the given prompt, as if in a real conversation. Keep your reply focused and concise, ideally around 50-75 words. Don't continue the conversation beyond your response or roleplay as anyone else. Engage with the topic, add your perspective, or ask a relevant question, but always conclude your response naturally. Avoid overly formal or flowery language - aim for a casual, friendly tone.
```


![image_2024-10-20_12-35-59](https://github.com/user-attachments/assets/74b355ea-6613-4865-aebc-df419f36e5c2)




To try it out in docker:
```
git clone https://github.com/hugalafutro/llm-convo.git
cd llm-convo
docker compose build
docker compose up -d
```


Check docker logs `docker compose logs -f`:
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
- Enter the openai compatible api checkpoint address in format `http://address:port/v1` i.e. `http://192.168.1.163:5001/v1` and press Connect Endpoint button for both Endpoints.
- You should get an popup connection succesful and the Endpoint button will turn green.
- Once both Enndpoint buttons are green it's go time.
- Write the Intial Prompt in the bottom text input area and click the Send button.

---

*My lawyer (Command-R LLM) advised me to include this disclaimer considering the uncertainty of the generated outputs. Future is wild, man.*
# Legal Disclaimer

Please note that the use of this application and the interactions between the two LLMs (Large Language Models) are intended for educational and experimental purposes only. The developer of this app bears no responsibility for the content generated by the LLMs or any subsequent actions taken based on their outputs.

By using this application, you acknowledge and agree to the following:

## User Responsibility
It is the sole responsibility of the user to monitor and control the conversations between the LLMs. You understand that LLMs generate text based on patterns learned from vast amounts of data, and their outputs may occasionally contain inappropriate, offensive, or inaccurate information.

## Content Disclaimer
The developer does not endorse, promote, or condone any specific viewpoints, opinions, or statements made by the LLMs. Any depraved, illegal, or harmful content generated during the interactions is not reflective of the developer's beliefs or intentions.

## Screenshot and Sharing
If you choose to screenshot or share any generated content, you do so at your own risk. The developer is not liable for any consequences arising from the distribution or interpretation of such content. It is your responsibility to ensure that the content shared complies with relevant laws and ethical standards.

## No Guarantee of Accuracy
LLMs are not infallible, and their responses may contain errors, biases, or misleading information. The developer makes no warranty or guarantee regarding the accuracy, reliability, or suitability of the generated outputs for any purpose.

## Indemnification
By using this application, you agree to indemnify and hold the developer harmless from any claims, damages, or liabilities arising from your use of the app, including but not limited to any legal actions resulting from the content generated by the LLMs.

## Termination of Use
The developer reserves the right to terminate access to this application for any user who violates these terms or engages in activities that are illegal, harmful, or unethical.

## Local Use
This application is designed for local use, and the developer is not responsible for any issues or legal implications arising from the deployment or distribution of the LLMs in other contexts.

Remember, as a user, it is crucial to exercise good judgment and ethical considerations when interacting with and sharing content generated by LLMs.

Please read these terms carefully before using the application. By proceeding, you acknowledge that you have understood and accepted the legal disclaimer.
