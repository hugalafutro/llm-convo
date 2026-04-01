(function () {
  "use strict";

  // ===== State =====
  let eventSource = null;
  let endpoint1Connected = false;
  let endpoint2Connected = false;
  let currentMessageEl = null;
  let currentContent = "";
  let currentReasoning = "";
  let currentSpeaker = "";
  let turnIndex = 0;

  // ===== DOM refs =====
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const dom = {
    themeToggle: $("#theme-toggle"),
    conversation: $("#conversation"),
    promptInput: $("#prompt-input"),
    sendBtn: $("#send-btn"),
    stopBtn: $("#stop-btn"),
    clearBtn: $("#clear-btn"),
    numExchanges: $("#num-exchanges"),
    numExchangesValue: $("#num-exchanges-value"),
    initialPrompt: $("#initial-prompt"),
    initialPromptText: $("#initial-prompt-text"),
    typingIndicator: $("#typing-indicator"),
    toastContainer: $("#toast-container"),
  };

  // ===== Toast Notifications =====
  function toast(message, type = "info") {
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.textContent = message;
    dom.toastContainer.appendChild(el);
    setTimeout(() => el.remove(), 4000);
  }

  // ===== Theme =====
  function initTheme() {
    const saved = localStorage.getItem("theme");
    if (saved === "light") {
      document.body.classList.add("light");
    }
    dom.themeToggle.addEventListener("click", () => {
      document.body.classList.toggle("light");
      localStorage.setItem(
        "theme",
        document.body.classList.contains("light") ? "light" : "dark",
      );
    });
  }

  // ===== LocalStorage persistence =====
  function saveField(id, value) {
    localStorage.setItem(`llm_convo_${id}`, value);
  }

  function loadField(id, fallback = "") {
    return localStorage.getItem(`llm_convo_${id}`) || fallback;
  }

  function initPersistence() {
    const fields = [
      "endpoint1-url",
      "endpoint1-key",
      "endpoint1-name",
      "endpoint1-prompt",
      "endpoint2-url",
      "endpoint2-key",
      "endpoint2-name",
      "endpoint2-prompt",
    ];
    fields.forEach((id) => {
      const el = $(`#${id}`);
      if (!el) return;
      const saved = loadField(id);
      if (saved) el.value = saved;
      el.addEventListener("input", () => saveField(id, el.value));
    });
  }

  // ===== Endpoint Connection =====
  async function connectEndpoint(num) {
    const url = $(`#endpoint${num}-url`).value.trim();
    const key = $(`#endpoint${num}-key`).value.trim();
    const name = $(`#endpoint${num}-name`).value.trim();
    const prompt = $(`#endpoint${num}-prompt`).value;
    const btn = $(`#connect${num}`);
    const spinner = btn.querySelector(".spinner");
    const btnText = btn.querySelector(".btn-text");

    if (!url) {
      toast("Please enter an endpoint URL", "error");
      return;
    }

    btn.disabled = true;
    spinner.classList.remove("hidden");
    btnText.textContent = "Connecting...";

    try {
      const resp = await fetch("/connect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          endpoint_num: num,
          endpoint_url: url,
          system_prompt: prompt,
          api_key: key,
          character_name: name || `Character ${num}`,
        }),
      });
      const data = await resp.json();

      if (data.status === "success") {
        btn.classList.add("connected");
        btnText.textContent = "Connected";
        if (num === 1) endpoint1Connected = true;
        else endpoint2Connected = true;

        // Check for saved model preference for this API URL and endpoint
        const savedModel =
          localStorage.getItem(`llm_convo_model_${num}_${url}`) ||
          data.saved_model ||
          "";
        const select = $(`#endpoint${num}-model`);
        populateModelSelect(select, data.models || [], savedModel);
        select.classList.remove("hidden");
        select.disabled = false;
        toast(
          `Endpoint ${num} connected (${data.model || "unknown"})`,
          "success",
        );
      } else {
        btn.classList.remove("connected");
        btnText.textContent = "Connect";
        if (num === 1) endpoint1Connected = false;
        else endpoint2Connected = false;
        toast(data.message || "Connection failed", "error");
      }
    } catch (err) {
      btn.classList.remove("connected");
      btnText.textContent = "Connect";
      if (num === 1) endpoint1Connected = false;
      else endpoint2Connected = false;
      toast(`Failed to connect: ${err.message}`, "error");
    } finally {
      btn.disabled = false;
      spinner.classList.add("hidden");
      updateSendState();
    }
  }

  function updateSendState() {
    dom.sendBtn.disabled = !(endpoint1Connected && endpoint2Connected);
  }

  function populateModelSelect(selectEl, models, selectedModel) {
    selectEl.innerHTML = "";
    models.forEach((id) => {
      const opt = document.createElement("option");
      opt.value = id;
      opt.textContent = id;
      if (id === selectedModel) opt.selected = true;
      selectEl.appendChild(opt);
    });
    if (!models.length) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "No models available";
      selectEl.appendChild(opt);
    }
  }

  async function onModelChange(num) {
    const select = $(`#endpoint${num}-model`);
    const modelId = select.value;
    const urlInput = $(`#endpoint${num}-url`);
    const apiUrl = urlInput ? urlInput.value.trim() : "";
    try {
      await fetch("/set-model", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ endpoint_num: num, model_id: modelId }),
      });
      if (apiUrl) {
        localStorage.setItem(`llm_convo_model_${num}_${apiUrl}`, modelId);
      }
    } catch (err) {
      toast(`Failed to set model: ${err.message}`, "error");
    }
  }

  function setModelSelectsDisabled(disabled) {
    $(`#endpoint1-model`).disabled = disabled || !endpoint1Connected;
    $(`#endpoint2-model`).disabled = disabled || !endpoint2Connected;
  }

  // ===== Simple Markdown Rendering (XSS-safe) =====
  function renderMarkdown(text) {
    const escaped = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    let html = escaped
      // code blocks
      .replace(/```(\w*)\n([\s\S]*?)```/g, (_m, _lang, code) => {
        return `<pre><code>${code}</code></pre>`;
      })
      // inline code
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      // bold + italic
      .replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>")
      // bold
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      // italic
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      // line breaks -> paragraphs
      .replace(/\n{2,}/g, "</p><p>")
      .replace(/\n/g, "<br>");

    return `<p>${html}</p>`;
  }

  function ensureReasoningDetails() {
    if (!currentMessageEl) {
      return null;
    }
    let details = currentMessageEl.querySelector(".message-reasoning");
    if (!details) {
      details = document.createElement("details");
      details.className = "message-reasoning";
      const summary = document.createElement("summary");
      summary.textContent = "Thinking";
      details.appendChild(summary);
      const inner = document.createElement("div");
      inner.className = "message-reasoning-body";
      details.appendChild(inner);
      const body = currentMessageEl.querySelector(".message-body");
      currentMessageEl.insertBefore(details, body);
    }
    return details.querySelector(".message-reasoning-body");
  }

  // ===== Chat Streaming =====
  function startChat() {
    const prompt = dom.promptInput.value.trim();
    const numExchanges = dom.numExchanges.value;

    if (!prompt) {
      toast("Please enter a prompt", "error");
      return;
    }

    dom.initialPromptText.textContent = prompt;
    dom.initialPrompt.classList.remove("hidden");
    dom.promptInput.value = "";

    currentMessageEl = null;
    currentContent = "";
    currentReasoning = "";
    currentSpeaker = "";
    turnIndex = 0;

    dom.sendBtn.disabled = true;
    dom.stopBtn.disabled = false;
    dom.typingIndicator.classList.remove("hidden");
    setModelSelectsDisabled(true);

    const params = new URLSearchParams({ prompt, num_exchanges: numExchanges });
    eventSource = new EventSource(`/chat?${params}`);

    eventSource.addEventListener("sender", (e) => {
      const data = JSON.parse(e.data);
      finishCurrentMessage();
      turnIndex++;

      const side = turnIndex % 2 === 1 ? "model2" : "model1";
      currentSpeaker = data.sender;

      const msgDiv = document.createElement("div");
      msgDiv.className = `message ${side}`;

      const senderDiv = document.createElement("div");
      senderDiv.className = "message-sender";
      senderDiv.textContent = data.sender;
      msgDiv.appendChild(senderDiv);

      const bodyDiv = document.createElement("div");
      bodyDiv.className = "message-body";
      msgDiv.appendChild(bodyDiv);

      dom.conversation.appendChild(msgDiv);
      currentMessageEl = msgDiv;
      currentContent = "";
      currentReasoning = "";
      scrollToBottom();
    });

    eventSource.addEventListener("reasoning", (e) => {
      const data = JSON.parse(e.data);
      currentReasoning += data.reasoning;
      const inner = ensureReasoningDetails();
      if (inner) {
        inner.innerHTML = renderMarkdown(currentReasoning);
      }
      scrollToBottom();
    });

    eventSource.addEventListener("content", (e) => {
      const data = JSON.parse(e.data);
      currentContent += data.content;
      if (currentMessageEl) {
        const body = currentMessageEl.querySelector(".message-body");
        body.innerHTML = renderMarkdown(currentContent);
      }
      scrollToBottom();
    });

    eventSource.addEventListener("end", (e) => {
      const data = JSON.parse(e.data);
      if (currentMessageEl) {
        const infoDiv = document.createElement("div");
        infoDiv.className = "message-info";
        infoDiv.textContent = `${data.timestamp} \u2022 ${data.model} \u2022 ${data.total_tokens} tokens \u2022 ${data.tps.toFixed(2)} t/s`;
        currentMessageEl.appendChild(infoDiv);
      }
      currentMessageEl = null;
      currentContent = "";
      currentReasoning = "";
      scrollToBottom();
    });

    eventSource.addEventListener("error", (e) => {
      if (e.data) {
        try {
          const data = JSON.parse(e.data);
          toast(data.error || "Stream error", "error");
        } catch {
          // EventSource reconnect error, not our custom event
        }
      }
    });

    eventSource.addEventListener("done", () => {
      finishCurrentMessage();
      stopChat(false);
      toast("Conversation complete", "success");
    });

    eventSource.onerror = () => {
      stopChat(false);
    };
  }

  function finishCurrentMessage() {
    if (!currentMessageEl) {
      return;
    }
    const body = currentMessageEl.querySelector(".message-body");
    if (body && currentContent) {
      body.innerHTML = renderMarkdown(currentContent);
    }
    if (currentReasoning) {
      const inner = ensureReasoningDetails();
      if (inner) {
        inner.innerHTML = renderMarkdown(currentReasoning);
      }
    }
  }

  function stopChat(notify = true) {
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
    dom.sendBtn.disabled = !(endpoint1Connected && endpoint2Connected);
    dom.stopBtn.disabled = true;
    dom.typingIndicator.classList.add("hidden");
    setModelSelectsDisabled(false);
    if (notify) toast("Generation stopped", "info");
  }

  async function clearConversation() {
    dom.conversation.innerHTML = "";
    dom.initialPrompt.classList.add("hidden");
    dom.initialPromptText.textContent = "";
    currentMessageEl = null;
    currentContent = "";
    currentReasoning = "";
    turnIndex = 0;

    try {
      await fetch("/clear", { method: "POST" });
    } catch {
      // best effort
    }
    toast("Conversation cleared", "info");
  }

  function scrollToBottom() {
    const panel = $("#conversation-panel");
    panel.scrollTop = panel.scrollHeight;
  }

  // ===== Init =====
  function init() {
    initTheme();
    initPersistence();
    updateSendState();

    dom.numExchanges.addEventListener("input", () => {
      dom.numExchangesValue.textContent = dom.numExchanges.value;
    });

    $$("#connect1, #connect2").forEach((btn) => {
      const num = parseInt(btn.dataset.endpoint, 10);
      btn.addEventListener("click", () => connectEndpoint(num));
    });

    [1, 2].forEach((num) => {
      $(`#endpoint${num}-model`).addEventListener("change", () =>
        onModelChange(num),
      );
    });

    dom.sendBtn.addEventListener("click", startChat);
    dom.stopBtn.addEventListener("click", () => stopChat(true));
    dom.clearBtn.addEventListener("click", clearConversation);

    dom.promptInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !dom.sendBtn.disabled) {
        startChat();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
