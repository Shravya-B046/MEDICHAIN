/**
 * MEDICHAIN Frontend Core Script
 * Fully integrated with the FastAPI Backend (http://127.0.0.1:8000)
 */

// ============================================================================
// SHARED API RESOLVER
// ============================================================================

function getApiClient() {
    if (typeof window !== "undefined") {
        if (window.medichainApi) return window.medichainApi;
        if (window.MedichainAPI) return window.MedichainAPI;
        if (window.api) return window.api;
        if (window.API) return window.API;
    }
    if (typeof medichainApi !== "undefined") return medichainApi;
    if (typeof api !== "undefined") return api;

    // Guaranteed fallback client pointing directly to backend
    var baseUrl = (typeof window !== "undefined" && window.location && window.location.hostname === "localhost")
        ? "http://localhost:8000"
        : "http://127.0.0.1:8000";

    var fallbackClient = {
        baseUrl: baseUrl,
        request: async function(endpoint, options) {
            options = options || {};
            var url = this.baseUrl + endpoint;
            var headers = Object.assign({ "Accept": "application/json" }, options.headers || {});
            if (options.body && !(options.body instanceof FormData)) {
                headers["Content-Type"] = "application/json";
                options.body = typeof options.body === "string" ? options.body : JSON.stringify(options.body);
            }
            var res = await fetch(url, {
                method: options.method || "GET",
                headers: headers,
                body: options.body
            });
            if (!res.ok) {
                var errText = "HTTP " + res.status + ": " + res.statusText;
                try {
                    var d = await res.json();
                    if (d && d.detail) errText = typeof d.detail === "string" ? d.detail : JSON.stringify(d.detail);
                } catch(_) {}
                throw new Error(errText);
            }
            return await res.json();
        },
        checkHealth: function() { return this.request("/api/health"); },
        sendChatMessage: function(message, context, history) {
            return this.request("/api/assistant/chat", { method: "POST", body: { message: message, context: context || null, history: history || [] } });
        },
        getResources: function() { return this.request("/api/resources"); },
        getResourceSummary: function() { return this.request("/api/resources/summary"); },
        getEmergencies: function() { return this.request("/api/emergency"); },
        getEmergencySummary: function() { return this.request("/api/emergency/summary"); },
        createEmergency: function(data) { return this.request("/api/emergency", { method: "POST", body: data }); },
        updateEmergencyStatus: function(caseId, status, priority) {
            return this.request("/api/emergency/" + caseId + "/status", { method: "PATCH", body: { status: status, priority: priority || null } });
        },
        uploadReport: function(file) {
            var fd = new FormData();
            fd.append("file", file);
            return this.request("/api/reports/upload", { method: "POST", body: fd });
        },
        getHospitals: function() { return this.request("/api/hospitals"); },
        createHospital: function(data) { return this.request("/api/hospitals", { method: "POST", body: data }); },
        deleteHospital: function(id) { return this.request("/api/hospitals/" + id, { method: "DELETE" }); }
    };

    if (typeof window !== "undefined") {
        window.medichainApi = fallbackClient;
    }
    return fallbackClient;
}


// ============================================================================
// MODULE 1: AI HEALTH ASSISTANT (assistant.html)
// ============================================================================

var chatHistory = [];

function clearChat() {
    if (typeof stopSpeaking === "function") stopSpeaking();
    chatHistory = [];
    var chatMessages = document.getElementById("chatMessages");
    if (!chatMessages) return;
    chatMessages.innerHTML = `
        <div class="message bot-message">
            <p><strong>Hello! 👋 Welcome back to MEDICHAIN Clinical AI.</strong></p>
            <p>I am your digital healthcare assistant, grounded in WHO, MedlinePlus, and clinical evidence. You can ask me:</p>
            <ul class="md-list">
                <li>General health, lifestyle & preventive care questions</li>
                <li>Symptom explanations and home precautions</li>
                <li>Detailed <strong>medicine information</strong> (uses, mechanism, side effects, interactions & food timing)</li>
            </ul>
            <p style="font-size: 12px; color: #64748b; margin-top: 6px;">How can I assist your health inquiry today?</p>
            <div class="speak-aloud-container">
                <button type="button" class="speak-aloud-btn" onclick="toggleSpeech(this)"
                    data-speech-text="Hello! Welcome back to MEDICHAIN Clinical AI. I am your digital healthcare assistant, grounded in WHO, MedlinePlus, and clinical evidence. You can ask me general health, lifestyle, and preventive care questions, symptom explanations, and detailed medicine information. How can I assist your health inquiry today?"
                    title="Listen to this answer (Text to Speech)" aria-label="Speak out loud">
                    <span>🔊</span> <span>Speak Out Loud</span>
                </button>
            </div>
        </div>
    `;
}

function renderMedicalMarkdown(text) {
    if (!text) return "";

    // 1. Basic HTML entity escape for XSS protection
    var escaped = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // 2. Format headers
    escaped = escaped.replace(/^### (.*$)/gim, '<h4 class="md-h4">$1</h4>');
    escaped = escaped.replace(/^## (.*$)/gim, '<h3 class="md-h3">$1</h3>');
    escaped = escaped.replace(/^# (.*$)/gim, '<h2 class="md-h2">$1</h2>');

    // 3. Format bold and italic text
    escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    escaped = escaped.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // 4. Format markdown links: [label](url)
    escaped = escaped.replace(/\[(.*?)\]\((https?:\/\/.*?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="md-link">$1 ↗</a>');

    // 5. Format callouts / notes: > [!NOTE] or > quote
    escaped = escaped.replace(/^&gt; \[\!NOTE\]\s*\n&gt; (.*$)/gim, '<div class="md-callout"><strong>Clinical Clarification:</strong> $1</div>');
    escaped = escaped.replace(/^&gt; (.*$)/gim, '<blockquote class="md-quote">$1</blockquote>');

    // 6. Format lists & paragraphs cleanly
    var lines = escaped.split("\n");
    var inList = false;
    var output = [];

    for (var i = 0; i < lines.length; i++) {
        var rawLine = lines[i].trim();
        if (rawLine.startsWith("- ") || rawLine.startsWith("* ")) {
            if (!inList) {
                output.push('<ul class="md-list">');
                inList = true;
            }
            output.push('<li>' + rawLine.substring(2) + '</li>');
        } else {
            if (inList) {
                output.push('</ul>');
                inList = false;
            }
            if (rawLine.length > 0) {
                if (rawLine.startsWith("<h2") || rawLine.startsWith("<h3") || rawLine.startsWith("<h4") || rawLine.startsWith("<div") || rawLine.startsWith("<blockquote")) {
                    output.push(rawLine);
                } else if (rawLine === "---") {
                    output.push('<hr class="md-divider">');
                } else {
                    output.push('<p class="md-p">' + rawLine + '</p>');
                }
            }
        }
    }
    if (inList) {
        output.push('</ul>');
    }

    return output.join("\n");
}

async function checkAssistantOnlineStatus() {
    var statusEl = document.getElementById("assistantStatusText");
    if (!statusEl) return;

    try {
        var client = getApiClient();
        var health = await client.checkHealth();
        var dbLabel = health.database || "operational";
        var aiLabel = health.gemini_ai_configured ? "Gemini 3.1 Live" : "Medical Engine";
        statusEl.innerHTML = `● Online <span style="font-size: 11px; opacity: 0.85;">(${escapeHtml(aiLabel)} | ${escapeHtml(dbLabel)})</span>`;
        statusEl.style.color = "#15803d";
    } catch (e) {
        statusEl.innerHTML = `● Backend Offline <span style="font-size: 11px;">(Check server)</span>`;
        statusEl.style.color = "#b91c1c";
    }
}

async function sendMessage() {
    var input = document.getElementById("userInput");
    var chatMessages = document.getElementById("chatMessages");

    if (!input || !chatMessages) return;

    var question = input.value.trim();
    if (question === "") return;

    // Display user message bubble
    var userMessage = document.createElement("div");
    userMessage.className = "message user-message";
    userMessage.textContent = question;
    chatMessages.appendChild(userMessage);

    input.value = "";
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Display temporary typing indicator
    var typingMessage = document.createElement("div");
    typingMessage.className = "message bot-message chat-typing";
    typingMessage.id = "typingIndicator";
    typingMessage.innerHTML = '<span class="spinner"></span> Consulting MEDICHAIN clinical AI engine...';
    chatMessages.appendChild(typingMessage);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Call real FastAPI backend with conversation history & multilingual support
    try {
        var client = getApiClient();
        var currentLang = (typeof currentLanguage !== "undefined" ? currentLanguage : (localStorage.getItem("medichain_lang") || "en"));
        var data = await client.sendChatMessage(question, null, chatHistory, currentLang);

        // Remove typing indicator
        if (typingMessage.parentNode) {
            typingMessage.parentNode.removeChild(typingMessage);
        }

        // Save turns into conversation history
        chatHistory.push({ role: "user", content: question });
        if (data.reply) {
            chatHistory.push({ role: "assistant", content: data.reply });
        }
        if (chatHistory.length > 12) {
            chatHistory = chatHistory.slice(-12);
        }

        // Display bot response bubble
        var botMessage = document.createElement("div");
        botMessage.className = "message bot-message";

        // Emergency banner
        if (data.is_emergency) {
            var emergencyBanner = document.createElement("div");
            emergencyBanner.className = "emergency-alert-card";
            emergencyBanner.innerHTML = `
                <strong>🚨 Critical Emergency Alert</strong>
                <span>Potential acute medical emergency detected. Immediate professional care is required.</span>
                <div style="margin-top: 8px;">
                    <a href="emergency.html" style="display: inline-block; background: #dc2626; color: white; padding: 6px 12px; border-radius: 4px; text-decoration: none; font-weight: bold; font-size: 12px;">Go to Emergency Coordination ➔</a>
                </div>
            `;
            botMessage.appendChild(emergencyBanner);
        }

        // Formatted Markdown Content
        var contentWrapper = document.createElement("div");
        contentWrapper.innerHTML = renderMedicalMarkdown(data.reply || "No response received from clinical engine.");
        botMessage.appendChild(contentWrapper);

        // Source badge & verified references
        var badge = document.createElement("span");
        if (data.source === "gemini_api") {
            badge.className = "api-badge live";
            badge.textContent = "🤖 Powered by Gemini AI (Model 3.1 Flash-Lite)";
        } else if (data.source === "verified_medical_kb") {
            badge.className = "api-badge live";
            badge.textContent = "📚 Verified Medical Knowledge Base";
        } else {
            badge.className = "api-badge ai";
            badge.textContent = "🩺 Clinical Engine (Educational)";
        }
        botMessage.appendChild(badge);

        // Sources pills
        if (data.verified_sources && data.verified_sources.length > 0) {
            var sourceContainer = document.createElement("div");
            sourceContainer.className = "source-pill-container";
            sourceContainer.innerHTML = '<span style="font-size: 11px; color: #64748b; font-weight: 600;">References:</span>';
            data.verified_sources.forEach(function(src) {
                var pill = document.createElement("span");
                pill.className = "source-pill";
                pill.textContent = src;
                sourceContainer.appendChild(pill);
            });
            botMessage.appendChild(sourceContainer);
        }

        if (data.disclaimer) {
            var disc = document.createElement("p");
            disc.style.fontSize = "11px";
            disc.style.color = "#64748b";
            disc.style.marginTop = "8px";
            disc.style.borderTop = "1px solid #f1f5f9";
            disc.style.paddingTop = "6px";
            disc.textContent = "⚠️ " + data.disclaimer;
            botMessage.appendChild(disc);
        }

        // Append Speak Out Loud accessibility button right at the end of the answer
        var speakContainer = document.createElement("div");
        speakContainer.className = "speak-aloud-container";

        var speakBtn = document.createElement("button");
        speakBtn.type = "button";
        speakBtn.className = "speak-aloud-btn";
        speakBtn.setAttribute("aria-label", "Speak out loud - Text to Speech for accessibility");
        speakBtn.setAttribute("title", "Listen to this answer (Text to Speech)");
        speakBtn.innerHTML = `<span>🔊</span> <span>Speak Out Loud</span>`;
        speakBtn.dataset.speechText = cleanTextForSpeech(data.reply || "");
        speakBtn.onclick = function () {
            toggleSpeech(speakBtn);
        };

        speakContainer.appendChild(speakBtn);
        botMessage.appendChild(speakContainer);

        chatMessages.appendChild(botMessage);
    } catch (error) {
        if (typingMessage.parentNode) {
            typingMessage.parentNode.removeChild(typingMessage);
        }

        var errorMessage = document.createElement("div");
        errorMessage.className = "message bot-message";
        errorMessage.innerHTML = `
            <p style="color: #b91c1c;"><strong>⚠️ Connection Notice:</strong> Unable to reach the clinical assistant service (${escapeHtml(error.message)}).</p>
            <p style="font-size: 13px; margin-top: 6px; color: #64748b;">Please verify that the backend is active.</p>
        `;
        chatMessages.appendChild(errorMessage);
    }

    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function askQuestion(question) {
    var input = document.getElementById("userInput");
    if (!input) return;
    input.value = question;
    sendMessage();
}

// ============================================================================
// TEXT-TO-SPEECH (SPEAK OUT LOUD) ACCESSIBILITY ENGINE
// ============================================================================
var currentSpeechUtterance = null;
var activeSpeakingBtn = null;

function cleanTextForSpeech(raw) {
    if (!raw) return "";
    var text = raw;
    text = text.replace(/\[([^\]]+)\]\([^)]+\)/g, "$1");
    text = text.replace(/#{1,6}\s+/g, "");
    text = text.replace(/\*\*(.*?)\*\*/g, "$1");
    text = text.replace(/\*(.*?)\*/g, "$1");
    text = text.replace(/__(.*?)__/g, "$1");
    text = text.replace(/_(.*?)_/g, "$1");
    text = text.replace(/`{1,3}[^`]*`{1,3}/g, "");
    text = text.replace(/^\s*[-*+]\s+/gm, "");
    text = text.replace(/^\s*\d+\.\s+/gm, "");
    text = text.replace(/^-{3,}|^\*{3,}|^_{3,}/gm, "");
    text = text.replace(/<[^>]*>/g, " ");
    // Strip emojis and high surrogates that crash or mute Windows SAPI voices
    text = text.replace(/[\uD800-\uDBFF][\uDC00-\uDFFF]/g, "");
    text = text.replace(/[\u2600-\u27BF\uE000-\uF8FF]/g, "");
    text = text.replace(/\s+/g, " ").trim();
    return text;
}

function getBestVoice(targetLang) {
    if (!("speechSynthesis" in window)) return null;
    var voices = window.speechSynthesis.getVoices();
    if (!voices || !voices.length) return null;

    if (targetLang) {
        var langLower = targetLang.toLowerCase();
        var exact = voices.find(function (v) { return v.lang && v.lang.toLowerCase() === langLower; });
        if (exact) return exact;

        var prefix = langLower.split("-")[0];
        var prefixMatch = voices.find(function (v) { return v.lang && v.lang.toLowerCase().startsWith(prefix); });
        if (prefixMatch) return prefixMatch;
    }

    var enVoice = voices.find(function (v) { return v.lang && v.lang.toLowerCase().startsWith("en"); });
    if (enVoice) return enVoice;

    return voices[0] || null;
}

function playAudioChime() {
    try {
        var AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) return;
        var ctx = new AudioCtx();
        if (ctx.state === "suspended") {
            ctx.resume();
        }
        var osc = ctx.createOscillator();
        var gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(587.33, ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.12);
        gain.gain.setValueAtTime(0.3, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 0.25);
    } catch (e) {
        console.warn("Chime notice:", e);
    }
}

function stopSpeaking() {
    if ("speechSynthesis" in window) {
        try { window.speechSynthesis.cancel(); } catch (e) { }
    }
    if (activeSpeakingBtn) {
        activeSpeakingBtn.classList.remove("speaking");
        activeSpeakingBtn.innerHTML = "<span>🔊</span> <span>Speak Out Loud</span>";
        activeSpeakingBtn.setAttribute("title", "Listen to this answer (Text to Speech)");
        activeSpeakingBtn = null;
    }
    currentSpeechUtterance = null;
    window._activeSpeechUtterance = null;
}

function toggleSpeech(btn) {
    if (!("speechSynthesis" in window)) {
        alert("Text-to-speech is not supported in this browser. Please try Google Chrome, Microsoft Edge, or Safari.");
        return;
    }

    playAudioChime();

    if (activeSpeakingBtn === btn && (window.speechSynthesis.speaking || window.speechSynthesis.pending)) {
        stopSpeaking();
        return;
    }

    stopSpeaking();

    if (window.speechSynthesis.paused) {
        try { window.speechSynthesis.resume(); } catch (e) { }
    }

    var textToSpeak = btn.dataset.speechText;
    if (!textToSpeak) {
        var parentMsg = btn.closest(".bot-message");
        if (parentMsg) {
            var clone = parentMsg.cloneNode(true);
            var containers = clone.querySelectorAll(".speak-aloud-container, .api-badge, .source-pill-container");
            containers.forEach(function (el) { el.remove(); });
            textToSpeak = cleanTextForSpeech(clone.innerText || clone.textContent);
        }
    }

    if (!textToSpeak) return;

    var bestVoice = getBestVoice("en-US");

    var utterance = new SpeechSynthesisUtterance(textToSpeak);
    utterance.volume = 1.0;
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    if (bestVoice) {
        utterance.voice = bestVoice;
        utterance.lang = bestVoice.lang;
    } else {
        utterance.lang = "en-US";
    }

    activeSpeakingBtn = btn;
    btn.classList.add("speaking");
    btn.innerHTML = "<span>⏹️</span> <span>Stop Speaking</span>";
    btn.setAttribute("title", "Speaking out loud... Click to stop");

    utterance.onend = function () {
        stopSpeaking();
    };

    utterance.onerror = function (err) {
        console.warn("Speech synthesis notice:", err);
        if (err && (err.error === "canceled" || err.error === "interrupted")) {
            return;
        }
        stopSpeaking();
    };

    currentSpeechUtterance = utterance;
    window._activeSpeechUtterance = utterance;

    try {
        window.speechSynthesis.speak(utterance);
        if (window.speechSynthesis.paused) {
            window.speechSynthesis.resume();
        }
    } catch (e) {
        console.error("speechSynthesis.speak error:", e);
        stopSpeaking();
    }
}

// ============================================================================
// VOICE INPUT (SPEECH-TO-TEXT) FOR AI HEALTH ASSISTANT
// ============================================================================

var recognitionInstance = null;
var isListening = false;

function initVoiceRecognition() {
    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        return null;
    }

    var recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = navigator.language || "en-US";

    recognition.onstart = function () {
        isListening = true;
        updateVoiceUI(true);
    };

    recognition.onresult = function (event) {
        var input = document.getElementById("userInput");
        if (!input) return;

        var transcript = "";
        for (var i = 0; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
        }

        if (transcript.trim()) {
            input.value = transcript;
            input.focus();
        }
    };

    recognition.onerror = function (event) {
        console.warn("Speech recognition notice:", event.error);
        if (event.error === "no-speech") {
            return;
        }
        if (event.error === "not-allowed") {
            alert("Microphone permission was denied. Please click the lock 🔒 / tune icon next to localhost in the URL bar and set Microphone to Allow.");
        }
        isListening = false;
        updateVoiceUI(false);
    };

    recognition.onend = function () {
        isListening = false;
        updateVoiceUI(false);
        var input = document.getElementById("userInput");
        if (input && input.value.trim().length > 0) {
            input.focus();
        }
    };

    return recognition;
}

function toggleVoiceInput() {
    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        alert("Speech recognition is not supported in this browser. Please use Google Chrome, Microsoft Edge, or Safari.");
        return;
    }

    if (isListening && recognitionInstance) {
        try {
            recognitionInstance.stop();
        } catch (e) {}
        return;
    }

    if (!recognitionInstance) {
        recognitionInstance = initVoiceRecognition();
    }

    if (recognitionInstance) {
        try {
            recognitionInstance.start();
        } catch (e) {
            try { recognitionInstance.stop(); } catch (err) {}
            recognitionInstance = initVoiceRecognition();
            if (recognitionInstance) {
                setTimeout(function () {
                    try { recognitionInstance.start(); } catch (err) {}
                }, 200);
            }
        }
    }
}

function updateVoiceUI(listening) {
    var micBtn = document.getElementById("micBtn");
    var input = document.getElementById("userInput");
    var voiceStatus = document.getElementById("voiceStatusPill");

    if (micBtn) {
        if (listening) {
            micBtn.classList.add("listening");
            micBtn.title = "Listening to your symptoms... Click to stop";
            micBtn.setAttribute("aria-label", "Listening... Click to stop");
        } else {
            micBtn.classList.remove("listening");
            micBtn.title = "Speak your symptoms (Voice Input)";
            micBtn.setAttribute("aria-label", "Speak your symptoms");
        }
    }

    if (input) {
        if (listening) {
            if (!input.dataset.originalPlaceholder) {
                input.dataset.originalPlaceholder = input.placeholder;
            }
            input.placeholder = "🎙️ Listening to your symptoms... speak clearly";
        } else {
            if (input.dataset.originalPlaceholder) {
                input.placeholder = input.dataset.originalPlaceholder;
            }
        }
    }

    if (voiceStatus) {
        voiceStatus.style.display = listening ? "flex" : "none";
    }
}

if (typeof window !== "undefined") {
    window.sendMessage = sendMessage;
    window.askQuestion = askQuestion;
    window.clearChat = clearChat;
    window.toggleVoiceInput = toggleVoiceInput;
}


// ============================================================================
// MODULE 2: HOSPITAL RESOURCE DASHBOARD (resources.html)
// ============================================================================

var cachedResources = [];

async function loadResourceDashboard() {
    var tableBody = document.getElementById("resourceTableBody");
    if (!tableBody) return; // Not on resources page

    try {
        var client = getApiClient();
        var results = await Promise.all([
            client.getResourceSummary(),
            client.getResources()
        ]);
        var summary = results[0];
        var resources = results[1];
        cachedResources = resources || [];

        // 1. Update Resource Stat Cards
        var resTotalBeds = document.getElementById("resTotalBeds");
        var resAvailableBeds = document.getElementById("resAvailableBeds");
        var resOccupiedBeds = document.getElementById("resOccupiedBeds");
        var resIcuBeds = document.getElementById("resIcuBeds");
        var resDoctors = document.getElementById("resDoctors");
        var resAmbulances = document.getElementById("resAmbulances");

        if (resTotalBeds) resTotalBeds.textContent = summary.total_beds;
        if (resAvailableBeds) resAvailableBeds.textContent = summary.available_beds;
        if (resOccupiedBeds) resOccupiedBeds.textContent = summary.occupied_beds;
        if (resIcuBeds) resIcuBeds.textContent = summary.icu_beds;
        if (resDoctors) resDoctors.textContent = summary.doctors_on_duty;
        if (resAmbulances) resAmbulances.textContent = summary.available_ambulances < 10 
            ? "0" + summary.available_ambulances 
            : summary.available_ambulances;

        // 2. Render Resource Table
        renderResourceRows(cachedResources);
    } catch (err) {
        console.warn("[Resource Dashboard] Error fetching live backend resources:", err);
        tableBody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; color: #b91c1c; padding: 20px;">
                    ⚠️ Error loading live resource metrics (${escapeHtml(err.message)}). Ensure backend is running.
                </td>
            </tr>
        `;
    }
}

function filterResources() {
    var searchInput = document.getElementById("resourceSearchInput");
    var categoryFilter = document.getElementById("resourceCategoryFilter");

    var query = (searchInput ? searchInput.value : "").trim().toLowerCase();
    var category = categoryFilter ? categoryFilter.value : "all";

    var filtered = cachedResources.filter(function(item) {
        var name = (item.resource_type || "").toLowerCase();

        // Category filter check
        if (category === "beds" && !name.includes("bed")) return false;
        if (category === "staff" && (!name.includes("doctor") && !name.includes("ambulance"))) return false;
        if (category === "equipment" && (!name.includes("ventilator") && !name.includes("cylinder") && !name.includes("oxygen"))) return false;
        if (category === "medicine" && (!name.includes("antibiotic") && !name.includes("saline") && !name.includes("fluid"))) return false;

        // Query check
        if (query && !name.includes(query)) return false;

        return true;
    });

    renderResourceRows(filtered);
}

function renderResourceRows(items) {
    var tableBody = document.getElementById("resourceTableBody");
    if (!tableBody) return;

    if (!Array.isArray(items) || items.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; color: #64748b; padding: 20px;">
                    No resources matching filter criteria.
                </td>
            </tr>
        `;
        return;
    }

    tableBody.innerHTML = "";
    items.forEach(function(res) {
        var tr = document.createElement("tr");

        var statusClass = "available";
        var st = (res.status || "").toLowerCase();
        if (st.includes("warn") || st.includes("low")) statusClass = "warning";
        else if (st.includes("occup") || st.includes("critical") || st.includes("full")) statusClass = "occupied";

        tr.innerHTML = `
            <td><strong>${escapeHtml(res.resource_type)}</strong></td>
            <td>${res.total}</td>
            <td><strong style="color: #15803d;">${res.available}</strong></td>
            <td>${res.occupied}</td>
            <td><span class="status ${statusClass}">${escapeHtml(res.status || "Available")}</span></td>
        `;
        tableBody.appendChild(tr);
    });
}


// ============================================================================
// MODULE 3: EMERGENCY COORDINATION (emergency.html)
// ============================================================================

var cachedEmergencies = (function() {
    try {
        var stored = localStorage.getItem("medichain_emergencies");
        if (stored) {
            var parsed = JSON.parse(stored);
            if (Array.isArray(parsed) && parsed.length > 0) return parsed;
        }
    } catch (_) {}

    return [
        { case_id: "EMG001", emergency_type: "Road Accident", location: "Mangaluru", hospital_name: "City Hospital", priority: "Critical", status: "Ambulance Sent" },
        { case_id: "EMG002", emergency_type: "Cardiac Emergency", location: "Bantwal", hospital_name: "General Hospital", priority: "Critical", status: "Ambulance Sent" },
        { case_id: "EMG003", emergency_type: "Medical Emergency", location: "Udupi", hospital_name: "District Hospital", priority: "Medium", status: "Resolved" },
        { case_id: "EMG004", emergency_type: "Accident", location: "Surathkal", hospital_name: "City Hospital", priority: "High", status: "In Progress" },
        { case_id: "EMG005", emergency_type: "Trauma / Fall", location: "Mangaluru", hospital_name: "Jyothi Hospital", priority: "Medium", status: "In Progress" }
    ];
})();

function saveEmergenciesToStorage(list) {
    try {
        localStorage.setItem("medichain_emergencies", JSON.stringify(list));
    } catch (_) {}
}

function filterEmergencyView(view) {
    var tabs = ["all", "pending", "dispatched", "resolved"];
    tabs.forEach(function(t) {
        var btn = document.getElementById("tabBtn" + t.charAt(0).toUpperCase() + t.slice(1));
        if (btn) {
            if (t === view) {
                btn.classList.add("active");
            } else {
                btn.classList.remove("active");
            }
        }
    });

    var secPending = document.getElementById("sectionPending");
    var secDispatched = document.getElementById("sectionDispatched");
    var secResolved = document.getElementById("sectionResolved");

    if (secPending) secPending.style.display = (view === "all" || view === "pending") ? "block" : "none";
    if (secDispatched) secDispatched.style.display = (view === "all" || view === "dispatched") ? "block" : "none";
    if (secResolved) secResolved.style.display = (view === "all" || view === "resolved") ? "block" : "none";
}

function renderEmergencyRows(cases, type, highlightedCaseId) {
    if (!Array.isArray(cases) || cases.length === 0) {
        var emptyText = "No cases in this category.";
        if (type === "pending") emptyText = "No pending emergencies awaiting dispatch.";
        else if (type === "dispatched") emptyText = "No dispatched ambulance units en route.";
        else if (type === "resolved") emptyText = "No resolved cases logged.";
        return `<tr><td colspan="7" class="empty-case-msg">${emptyText}</td></tr>`;
    }

    return cases.map(function(c) {
        var p = (c.priority || "").toLowerCase();
        var priorityClass = "available";
        if (p === "critical") priorityClass = "occupied";
        else if (p === "high") priorityClass = "warning";

        var s = (c.status || "").toLowerCase();
        var statusClass = "warning";
        if (s === "resolved" || s === "closed" || s === "completed") statusClass = "available";
        else if (s === "ambulance sent" || s === "dispatched") statusClass = "warning";

        var actionHtml = "";
        if (type === "pending") {
            actionHtml = `<button class="emg-btn-dispatch" onclick="updateCaseStatus('${escapeHtml(c.case_id)}', 'Ambulance Sent')">Dispatch 🚑</button>`;
        } else if (type === "dispatched") {
            actionHtml = `<button class="emg-btn-resolve" onclick="updateCaseStatus('${escapeHtml(c.case_id)}', 'Resolved')">Resolve ✓</button>`;
        } else {
            actionHtml = `<span class="badge-status-closed">Closed ✓</span>`;
        }

        var isHighlighted = highlightedCaseId && c.case_id === highlightedCaseId;
        var rowClass = isHighlighted ? ' class="newly-added-case"' : "";

        return `
            <tr${rowClass} id="row-${escapeHtml(c.case_id)}">
                <td><strong>${escapeHtml(c.case_id)}</strong></td>
                <td>${escapeHtml(c.emergency_type)}</td>
                <td>${escapeHtml(c.location)}</td>
                <td>${escapeHtml(c.hospital_name)}</td>
                <td><span class="status ${priorityClass}">${escapeHtml(c.priority)}</span></td>
                <td><span class="status ${statusClass}">${escapeHtml(c.status)}</span></td>
                <td>${actionHtml}</td>
            </tr>
        `;
    }).join("");
}

function renderCategorizedEmergencies(emergencies, highlightedCaseId) {
    var tablePending = document.getElementById("tableBodyPending");
    var tableDispatched = document.getElementById("tableBodyDispatched");
    var tableResolved = document.getElementById("tableBodyResolved");
    var legacyBody = document.getElementById("emergencyTableBody");

    var pendingCases = [];
    var dispatchedCases = [];
    var resolvedCases = [];

    (emergencies || []).forEach(function(c) {
        var st = (c.status || "").toLowerCase();
        if (st === "resolved" || st === "closed" || st === "completed") {
            resolvedCases.push(c);
        } else if (st.includes("ambulance") || st.includes("sent") || st.includes("dispatched") || st.includes("en route")) {
            dispatchedCases.push(c);
        } else {
            pendingCases.push(c);
        }
    });

    // 1. Update Overview Metric Cards
    var emgTotal = document.getElementById("emgTotal");
    var emgActive = document.getElementById("emgActive");
    var emgDispatched = document.getElementById("emgDispatched");
    var emgResolved = document.getElementById("emgResolved");

    var fmt = function(num) {
        return num < 10 ? "0" + num : "" + num;
    };

    if (emgTotal) emgTotal.textContent = fmt(emergencies.length);
    if (emgActive) emgActive.textContent = fmt(pendingCases.length);
    if (emgDispatched) emgDispatched.textContent = fmt(dispatchedCases.length);
    if (emgResolved) emgResolved.textContent = fmt(resolvedCases.length);

    // 2. Update Filter Tab Count Badges
    var countAll = document.getElementById("countAll");
    var countPending = document.getElementById("countPending");
    var countDispatched = document.getElementById("countDispatched");
    var countResolved = document.getElementById("countResolved");

    if (countAll) countAll.textContent = emergencies.length;
    if (countPending) countPending.textContent = pendingCases.length;
    if (countDispatched) countDispatched.textContent = dispatchedCases.length;
    if (countResolved) countResolved.textContent = resolvedCases.length;

    // 3. Update Section Headers Count Badges
    var badgePendingCount = document.getElementById("badgePendingCount");
    var badgeDispatchedCount = document.getElementById("badgeDispatchedCount");
    var badgeResolvedCount = document.getElementById("badgeResolvedCount");

    if (badgePendingCount) badgePendingCount.textContent = `${pendingCases.length} Awaiting Dispatch`;
    if (badgeDispatchedCount) badgeDispatchedCount.textContent = `${dispatchedCases.length} En Route`;
    if (badgeResolvedCount) badgeResolvedCount.textContent = `${resolvedCases.length} Closed`;

    // 4. Render Table Bodies
    if (tablePending) {
        tablePending.innerHTML = renderEmergencyRows(pendingCases, "pending", highlightedCaseId);
    }
    if (tableDispatched) {
        tableDispatched.innerHTML = renderEmergencyRows(dispatchedCases, "dispatched", highlightedCaseId);
    }
    if (tableResolved) {
        tableResolved.innerHTML = renderEmergencyRows(resolvedCases, "resolved", highlightedCaseId);
    }

    if (legacyBody) {
        legacyBody.innerHTML = renderEmergencyRows(emergencies, "all", highlightedCaseId);
    }
}

async function loadEmergencyDashboard() {
    var tablePending = document.getElementById("tableBodyPending");
    var legacyBody = document.getElementById("emergencyTableBody");
    if (!tablePending && !legacyBody) return; // Not on emergency page

    // Immediate initial render from cached/default data
    renderCategorizedEmergencies(cachedEmergencies);

    try {
        var client = getApiClient();
        var results = await Promise.all([
            client.getEmergencySummary().catch(function() { return null; }),
            client.getEmergencies().catch(function() { return null; })
        ]);
        var liveEmergencies = results[1];

        if (Array.isArray(liveEmergencies) && liveEmergencies.length > 0) {
            cachedEmergencies = liveEmergencies;
            saveEmergenciesToStorage(cachedEmergencies);
            renderCategorizedEmergencies(cachedEmergencies);
        }
    } catch (err) {
        console.warn("[Emergency Dashboard] Error fetching live backend emergencies, using cached:", err);
    }
}

async function handleEmergencySubmit(event) {
    if (event) {
        event.preventDefault();
        if (event.stopPropagation) event.stopPropagation();
    }

    var typeEl = document.getElementById("emgType");
    var priorityEl = document.getElementById("emgPriority");
    var locEl = document.getElementById("emgLocation");
    var hospEl = document.getElementById("emgHospital");
    var statusEl = document.getElementById("emgFormStatus");
    var submitBtn = document.getElementById("emgSubmitBtn");

    if (!typeEl || !locEl || !hospEl) return false;

    var emergency_type = typeEl.value.trim();
    var priority = priorityEl ? priorityEl.value : "Critical";
    var location = locEl.value.trim();
    var hospital_name = hospEl.value.trim();

    if (!emergency_type || !location || !hospital_name) {
        if (statusEl) {
            statusEl.textContent = "Please fill all required fields.";
            statusEl.style.color = "#b91c1c";
        }
        return false;
    }

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span> Logging case...';
    }
    if (statusEl) {
        statusEl.textContent = "Transmitting to emergency coordination dispatch...";
        statusEl.style.color = "#0e7490";
    }

    // Generate local fallback case code
    var maxNum = 0;
    cachedEmergencies.forEach(function(item) {
        var match = (item.case_id || "").match(/\d+/);
        if (match) {
            var n = parseInt(match[0], 10);
            if (n > maxNum) maxNum = n;
        }
    });
    var nextId = "EMG" + String(maxNum + 1).padStart(3, "0");

    var newCaseObj = {
        case_id: nextId,
        emergency_type: emergency_type,
        location: location,
        hospital_name: hospital_name,
        priority: priority,
        status: "In Progress"
    };

    // 1. Optimistically add to cachedEmergencies at the beginning so user sees it right away!
    cachedEmergencies.unshift(newCaseObj);
    saveEmergenciesToStorage(cachedEmergencies);
    renderCategorizedEmergencies(cachedEmergencies, newCaseObj.case_id);

    // 2. Ensure "Yet to Dispatch" or "All" tab is visible
    var secPending = document.getElementById("sectionPending");
    if (secPending) {
        secPending.style.display = "block";
        try {
            secPending.scrollIntoView({ behavior: "smooth", block: "nearest" });
        } catch (_) {}
    }

    try {
        var client = getApiClient();
        var serverCase = await client.createEmergency({
            emergency_type: emergency_type,
            priority: priority,
            location: location,
            hospital_name: hospital_name,
            status: "In Progress"
        });

        if (serverCase && serverCase.case_id) {
            newCaseObj.case_id = serverCase.case_id;
            saveEmergenciesToStorage(cachedEmergencies);
            renderCategorizedEmergencies(cachedEmergencies, serverCase.case_id);
        }

        if (statusEl) {
            statusEl.innerHTML = `✅ <strong>Case Logged:</strong> Assigned ID <code>${escapeHtml(newCaseObj.case_id)}</code>. Added to <em>Yet to Dispatch</em> below.`;
            statusEl.style.color = "#15803d";
        }
    } catch (err) {
        console.warn("[Emergency Submission] Server offline, stored locally in dispatch queue:", err);
        if (statusEl) {
            statusEl.innerHTML = `✅ <strong>Case Logged (Local Queue):</strong> Assigned ID <code>${escapeHtml(newCaseObj.case_id)}</code>. Added to <em>Yet to Dispatch</em> below.`;
            statusEl.style.color = "#15803d";
        }
    } finally {
        // Reset form
        typeEl.value = "";
        locEl.value = "";
        hospEl.value = "";

        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = "🚨 Submit Emergency Request";
        }
    }

    return false;
}

async function updateCaseStatus(caseId, newStatus) {
    if (!caseId || !newStatus) return;

    // Immediately update local state
    var found = false;
    for (var i = 0; i < cachedEmergencies.length; i++) {
        if (cachedEmergencies[i].case_id === caseId) {
            cachedEmergencies[i].status = newStatus;
            found = true;
            break;
        }
    }
    if (found) {
        saveEmergenciesToStorage(cachedEmergencies);
        renderCategorizedEmergencies(cachedEmergencies, caseId);
    }

    try {
        var client = getApiClient();
        await client.updateEmergencyStatus(caseId, newStatus);
    } catch (err) {
        console.warn("[Emergency Status Update] Local update applied, server sync delayed:", err);
    }
}


// ============================================================================
// MODULE 4: AI PRELIMINARY REPORT ANALYSIS (reports.html)
// ============================================================================

function handleReportFileSelect(input) {
    var fileMessage = document.getElementById("fileMessage");
    if (!input || !input.files || !input.files.length) {
        if (fileMessage) fileMessage.textContent = "";
        return;
    }
    var file = input.files[0];
    var allowed = ["pdf", "png", "jpg", "jpeg"];
    var ext = file.name.split(".").pop().toLowerCase();
    if (!allowed.includes(ext)) {
        if (fileMessage) {
            fileMessage.textContent = "⚠️ Unsupported format '." + ext + "'. Please choose PDF, PNG, or JPG.";
            fileMessage.style.color = "#b91c1c";
        }
        return;
    }
    if (fileMessage) {
        fileMessage.textContent = "📄 Ready to analyze: " + file.name + " (" + (file.size / 1024).toFixed(1) + " KB)";
        fileMessage.style.color = "#0369a1";
    }
}

async function analyzeReport() {
    var fileInput = document.getElementById("reportFile");
    var fileMessage = document.getElementById("fileMessage");
    var analysisResult = document.getElementById("analysisResult");
    var btn = document.getElementById("analyzeBtn");

    if (!fileInput || !fileInput.files.length) {
        if (fileMessage) {
            fileMessage.textContent = "⚠️ Please select a medical report file first.";
            fileMessage.style.color = "#b91c1c";
        }
        return;
    }

    var file = fileInput.files[0];
    var allowed = ["pdf", "png", "jpg", "jpeg"];
    var ext = file.name.split(".").pop().toLowerCase();

    if (!allowed.includes(ext)) {
        if (fileMessage) {
            fileMessage.textContent = "Unsupported format '." + ext + "'. Please upload PDF, PNG, or JPG.";
            fileMessage.style.color = "#b91c1c";
        }
        return;
    }

    if (file.size > 10 * 1024 * 1024) {
        if (fileMessage) {
            fileMessage.textContent = "File exceeds the 10 MB limit.";
            fileMessage.style.color = "#b91c1c";
        }
        return;
    }

    if (fileMessage) {
        fileMessage.textContent = "Selected: " + file.name + " (" + (file.size / 1024).toFixed(2) + " KB)";
        fileMessage.style.color = "#0f4c81";
    }

    if (btn) {
        btn.disabled = true;
        btn.textContent = "⏳ Analyzing Report...";
        btn.style.opacity = "0.7";
    }

    // Show loading state
    analysisResult.innerHTML = `
        <div style="padding: 20px; text-align: center;">
            <p><span class="spinner" style="width: 20px; height: 20px;"></span> <strong>Uploading and analyzing report with MEDICHAIN AI engine...</strong></p>
            <p style="font-size: 13px; color: #64748b; margin-top: 8px;">Processing through secure temporary memory pipeline. File will be automatically cleaned up.</p>
        </div>
    `;

    try {
        var client = getApiClient();
        var result = await client.uploadReport(file);

        if (result.is_medical === false || (result.status && result.status.indexOf("Rejected") !== -1)) {
            analysisResult.innerHTML = `
                <div style="background: #fff7ed; border-left: 5px solid #ea580c; padding: 22px; border-radius: 8px; color: #9a3412;">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                        <span style="font-size: 24px;">🚫</span>
                        <h3 style="margin: 0; color: #c2410c; font-size: 19px;">I am only scanning reports related to health</h3>
                    </div>
                    <p style="font-size: 15px; margin: 10px 0 14px 0; line-height: 1.5; color: #7c2d12;">
                        The uploaded file (<strong>${escapeHtml(result.filename)}</strong>) is not recognized as a health or medical report. <strong>I am only scanning reports related to health.</strong>
                    </p>
                    <div style="background: #ffedd5; padding: 12px 16px; border-radius: 6px; font-size: 13px; color: #9a3412;">
                        <strong>Please upload a report related to health, such as:</strong>
                        <ul style="margin: 6px 0 0 18px; padding-left: 0;">
                            <li>Pathology & Blood Tests (CBC, Blood Sugar, Lipid Profile, Thyroid, etc.)</li>
                            <li>Doctor Prescriptions & Hospital Discharge Notes</li>
                            <li>Diagnostic Imaging (X-Ray, Ultrasound, CT, MRI)</li>
                            <li>Official Clinical Health Checkup Records</li>
                        </ul>
                    </div>
                </div>
            `;
            return;
        }

        // Observations HTML
        var observationsHtml = "";
        if (Array.isArray(result.key_observations)) {
            observationsHtml = result.key_observations
                .map(function(obs) { return `<li>${escapeHtml(obs)}</li>`; })
                .join("");
        }

        // Extracted Findings HTML (from PDF parser)
        var findingsBlockHtml = "";
        if (Array.isArray(result.extracted_findings) && result.extracted_findings.length > 0) {
            var findingsList = result.extracted_findings
                .map(function(f) { return `<li><code>${escapeHtml(f)}</code></li>`; })
                .join("");
            findingsBlockHtml = `
                <div class="report-section-block" style="border-left-color: #6366f1; margin-top: 15px;">
                    <h4 style="color: #4338ca;">🔬 Extracted Clinical Metrics & Lab Values from Document</h4>
                    <ul>${findingsList}</ul>
                </div>
            `;
        }

        // Questions HTML
        var questionsHtml = "";
        if (Array.isArray(result.suggested_questions_for_doctor)) {
            questionsHtml = result.suggested_questions_for_doctor
                .map(function(q) { return `<li>${escapeHtml(q)}</li>`; })
                .join("");
        }

        analysisResult.innerHTML = `
            <div style="margin-bottom: 15px;">
                <span class="api-badge live">✓ Temporary File Cleaned from Server Memory</span>
                <span class="api-badge ai">Status: ${escapeHtml(result.status || "Completed")}</span>
                <span class="api-badge live">Method: ${escapeHtml(result.extraction_method || "pdf_parser")}</span>
            </div>
            
            <h3 style="color: #0f4c81; margin-bottom: 8px;">${escapeHtml(result.summary_title || "Preliminary Report Summary")}</h3>
            
            <p style="font-size: 13px; color: #64748b; margin-bottom: 15px;">
                <strong>File:</strong> ${escapeHtml(result.filename)} | 
                <strong>Size:</strong> ${result.file_size_kb} KB | 
                <strong>Type:</strong> ${escapeHtml(result.content_type)}
            </p>

            <div class="report-section-block">
                <h4>📋 Key Clinical Observations</h4>
                <ul>${observationsHtml}</ul>
            </div>

            ${findingsBlockHtml}

            <div class="report-section-block" style="border-left-color: #059669; margin-top: 15px;">
                <h4 style="color: #065f46;">💬 Suggested Questions for Your Doctor</h4>
                <ul>${questionsHtml}</ul>
            </div>

            <p class="disclaimer" style="margin-top: 20px;">
                ⚠️ <strong>Medical Notice:</strong> ${escapeHtml(result.disclaimer)}
            </p>
        `;
    } catch (error) {
        analysisResult.innerHTML = `
            <div class="connection-banner error">
                <div>
                    <strong>Analysis Error:</strong> ${escapeHtml(error.message)}
                    <div style="font-size: 12px; margin-top: 4px;">Ensure the backend is running at <code>http://127.0.0.1:8000</code>.</div>
                </div>
            </div>
        `;
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = "Analyze Report";
            btn.style.opacity = "1";
        }
    }
}


// ============================================================================
// MAIN DASHBOARD OVERVIEW (index.html)
// ============================================================================

async function loadIndexOverview() {
    var statHospitals = document.getElementById("overviewHospitals");
    if (!statHospitals) return; // Not on index.html

    try {
        var client = getApiClient();
        var results = await Promise.all([
            client.getHospitals().catch(function() { return []; }),
            client.getResourceSummary().catch(function() { return null; }),
            client.getEmergencySummary().catch(function() { return null; })
        ]);
        var hospitals = results[0];
        var resourceSummary = results[1];
        var emergencySummary = results[2];

        if (Array.isArray(hospitals) && statHospitals) {
            statHospitals.textContent = 24 + hospitals.filter(function(h) { return !h.is_sample; }).length;
        }

        var statBeds = document.getElementById("overviewBeds");
        if (resourceSummary && statBeds) {
            statBeds.textContent = resourceSummary.available_beds;
        }

        var statEmergencies = document.getElementById("overviewEmergencies");
        if (emergencySummary && statEmergencies) {
            var count = emergencySummary.active_emergencies;
            statEmergencies.textContent = count < 10 ? "0" + count : "" + count;
        }
    } catch (err) {
        console.warn("[Index Overview] Error loading live overview stats:", err);
    }
}


// ============================================================================
// NAVIGATION HELPER
// ============================================================================

function openFeature(feature) {
    var pages = {
        assistant: "assistant.html",
        resources: "resources.html",
        emergency: "emergency.html",
        reports: "reports.html"
    };

    if (pages[feature]) {
        window.location.href = pages[feature];
    }
}

// Authentication & Session Management
function getAuthUser() {
    var raw = localStorage.getItem("medichain_auth") || sessionStorage.getItem("medichain_auth");
    if (!raw) return null;
    try {
        return JSON.parse(raw);
    } catch (e) {
        return null;
    }
}

function handleLogout() {
    localStorage.removeItem("medichain_auth");
    sessionStorage.removeItem("medichain_auth");
    window.location.replace("login.html");
}

// Sidebar Minimize / Maximize (using the topbar hamburger toggle)
function toggleSidebar() {
    var sidebar = document.querySelector(".sidebar");
    if (!sidebar) return;

    sidebar.classList.toggle("collapsed");
    var isCollapsed = sidebar.classList.contains("collapsed");
    localStorage.setItem("medichain_sidebar_collapsed", isCollapsed ? "true" : "false");
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


// ============================================================================
// DOM READY INITIALIZATION
// ============================================================================

document.addEventListener("DOMContentLoaded", function() {
    // 1. Restore sidebar minimized/maximized state
    var isCollapsed = localStorage.getItem("medichain_sidebar_collapsed") === "true";
    if (isCollapsed) {
        var sidebar = document.querySelector(".sidebar");
        if (sidebar) {
            sidebar.classList.add("collapsed");
        }
    }

    // 2. Enter key support for AI assistant
    var input = document.getElementById("userInput");
    if (input) {
        input.addEventListener("keydown", function(event) {
            if (event.key === "Enter") {
                sendMessage();
            }
        });
    }

    // 3. Attach emergency form submission listener
    var emgForm = document.getElementById("emergencyForm");
    if (emgForm) {
        emgForm.addEventListener("submit", handleEmergencySubmit);
    }

    // 4. Dispatch page-specific live data fetchers
    checkAssistantOnlineStatus();
    loadIndexOverview();
    loadResourceDashboard();
    loadEmergencyDashboard();
});

// Explicit global registrations
if (typeof window !== "undefined") {
    window.analyzeReport = analyzeReport;
    window.handleReportFileSelect = handleReportFileSelect;
    window.sendMessage = sendMessage;
    window.askQuestion = askQuestion;
    window.toggleSidebar = toggleSidebar;
    window.toggleVoiceInput = toggleVoiceInput;
    window.handleLogout = handleLogout;
    window.filterEmergencyView = filterEmergencyView;
    window.updateCaseStatus = updateCaseStatus;
    window.handleEmergencySubmit = handleEmergencySubmit;
    window.toggleSpeech = toggleSpeech;
    window.stopSpeaking = stopSpeaking;
}
