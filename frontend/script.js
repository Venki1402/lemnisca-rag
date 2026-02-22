document.addEventListener("DOMContentLoaded", () => {
  const chatBox = document.getElementById("chat-box");
  const userInput = document.getElementById("user-input");
  const sendBtn = document.getElementById("send-btn");
  const debugToggle = document.getElementById("toggle-debug");
  const API_URL = "https://lemnisca-rag.onrender.com/chat";

  // Remove the initial pre-rendered message to handle rendering via JS logic
  chatBox.innerHTML = "";
  addMessage(
    "Hello! I'm the Clearpath Support Assistant. How can I help you today?",
    "bot",
  );

  // Toggle Debug UI
  debugToggle.addEventListener("change", (e) => {
    const panels = document.querySelectorAll(".debug-panel, .warning-banner");
    panels.forEach((p) => {
      if (e.target.checked) p.classList.remove("hidden-debug");
      else p.classList.add("hidden-debug");
    });
  });

  function createTypeIndicator() {
    const id = "typing-" + Date.now();
    const msgDiv = document.createElement("div");
    msgDiv.className = `message bot`;
    msgDiv.id = id;

    msgDiv.innerHTML = `
            <div class="message-text typing-indicator">
                <span></span><span></span><span></span>
            </div>
        `;
    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
    return id;
  }

  function removeTypeIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function addMessage(text, sender) {
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${sender}`;

    // Escape HTML
    const safeText = document.createElement("div");
    safeText.innerText = text;

    msgDiv.innerHTML = `<div class="message-text">${safeText.innerHTML}</div>`;
    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  function appendDebugPanel(msgDiv, debugInfo) {
    let warningHtml = "";
    if (!debugInfo.is_safe || debugInfo.evaluator_flags.length > 0) {
      warningHtml = `
                <div class="warning-banner ${!debugToggle.checked ? "hidden-debug" : ""}">
                    ⚠️ Low confidence — please verify with support.
                </div>
            `;
    }

    let flagsList = "";
    if (debugInfo.evaluator_flags.length > 0) {
      flagsList = `<div><span class="label">Flags:</span> ${debugInfo.evaluator_flags.join("<br>")}</div>`;
    }

    const debugContent = `
            ${warningHtml}
            <div class="debug-panel ${!debugToggle.checked ? "hidden-debug" : ""}">
                <div class="debug-heading">Develper Debug Info</div>
                <div><span class="label">Model:</span> <span style="font-family: monospace">${debugInfo.model_used}</span></div>
                <div><span class="label">Tokens [In/Out]:</span> ${debugInfo.tokens_input} / ${debugInfo.tokens_output}</div>
                ${flagsList}
            </div>
        `;

    // Append it as sibling fragment
    msgDiv.insertAdjacentHTML("beforeend", debugContent);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  async function handleSend() {
    const text = userInput.value.trim();
    if (!text) return;

    // User message
    addMessage(text, "user");
    userInput.value = "";

    // Show typing
    const indicatorId = createTypeIndicator();

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: text }),
      });

      removeTypeIndicator(indicatorId);

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        addMessage(
          "Oops! Something went wrong communicating with the server: " +
          (data.detail || "Server error"),
          "bot",
        );
        return;
      }

      // Create empty container for streaming text
      const msgDiv = document.createElement("div");
      msgDiv.className = "message bot";
      const msgTextDiv = document.createElement("div");
      msgTextDiv.className = "message-text";
      msgDiv.appendChild(msgTextDiv);
      chatBox.appendChild(msgDiv);

      // Read SSE Stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");

        buffer = lines.pop(); // Keep incomplete portion in buffer

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const dataStr = line.substring(5).trim();
              if (!dataStr) continue;
              const payload = JSON.parse(dataStr);

              if (payload.type === "token") {
                // Add small delay for visual typing effect (good for video demo)
                await new Promise((r) => setTimeout(r, 15));

                // Create temporary element to safely pull text content representation and append to DOM
                const tempDiv = document.createElement("span");
                tempDiv.innerText = payload.text;
                msgTextDiv.innerHTML += tempDiv.innerHTML;
                chatBox.scrollTop = chatBox.scrollHeight;
              } else if (payload.type === "meta") {
                appendDebugPanel(msgDiv, payload);
              }
            } catch (e) {
              console.error("Error parsing token", line, e);
            }
          }
        }
      }
    } catch (error) {
      removeTypeIndicator(indicatorId);
      addMessage(
        "Oops! Could not connect to the backend server. Make sure it's running.",
        "bot",
      );
      console.error("Chat error:", error);
    }
  }

  sendBtn.addEventListener("click", handleSend);
  userInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") handleSend();
  });
});
