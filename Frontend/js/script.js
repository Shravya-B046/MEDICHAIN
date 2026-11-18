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

    // Call real FastAPI backend with conversation history for multi-turn support
    try {
        var client = getApiClient();
        var data = await client.sendChatMessage(question, null, chatHistory);

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

if (typeof window !== "undefined") {
    window.sendMessage = sendMessage;
    window.askQuestion = askQuestion;
    window.clearChat = clearChat;
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

async function loadEmergencyDashboard() {
    var tableBody = document.getElementById("emergencyTableBody");
    if (!tableBody) return; // Not on emergency page

    try {
        var client = getApiClient();
        var results = await Promise.all([
            client.getEmergencySummary(),
            client.getEmergencies()
        ]);
        var summary = results[0];
        var emergencies = results[1];

        // 1. Update Emergency Metric Cards
        var emgTotal = document.getElementById("emgTotal");
        var emgActive = document.getElementById("emgActive");
        var emgDispatched = document.getElementById("emgDispatched");
        var emgResolved = document.getElementById("emgResolved");

        var fmt = function(num) {
            return num < 10 ? "0" + num : "" + num;
        };

        if (emgTotal) emgTotal.textContent = fmt(summary.total_emergencies);
        if (emgActive) emgActive.textContent = fmt(summary.active_emergencies);
        if (emgDispatched) emgDispatched.textContent = fmt(summary.ambulances_dispatched);
        if (emgResolved) emgResolved.textContent = fmt(summary.resolved_cases);

        // 2. Populate Emergency Case Table
        if (Array.isArray(emergencies) && emergencies.length > 0) {
            tableBody.innerHTML = "";
            emergencies.forEach(function(c) {
                var tr = document.createElement("tr");

                var priorityClass = "occupied";
                var p = (c.priority || "").toLowerCase();
                if (p === "critical") priorityClass = "occupied";
                else if (p === "high") priorityClass = "warning";
                else priorityClass = "available";

                var statusClass = "warning";
                var s = (c.status || "").toLowerCase();
                if (s === "resolved") statusClass = "available";
                else if (s === "in progress") statusClass = "warning";
                else if (s === "ambulance sent") statusClass = "warning";

                var actionBtn = "";
                if (s === "in progress") {
                    actionBtn = `<button style="padding: 4px 10px; background: #0284c7; color: white; border: none; border-radius: 4px; font-size: 11px; cursor: pointer;" onclick="updateCaseStatus('${escapeHtml(c.case_id)}', 'Ambulance Sent')">Dispatch 🚑</button>`;
                } else if (s === "ambulance sent") {
                    actionBtn = `<button style="padding: 4px 10px; background: #059669; color: white; border: none; border-radius: 4px; font-size: 11px; cursor: pointer;" onclick="updateCaseStatus('${escapeHtml(c.case_id)}', 'Resolved')">Resolve ✓</button>`;
                } else {
                    actionBtn = `<span style="font-size: 12px; color: #166534; font-weight: 600;">Closed</span>`;
                }

                tr.innerHTML = `
                    <td><strong>${escapeHtml(c.case_id)}</strong></td>
                    <td>${escapeHtml(c.emergency_type)}</td>
                    <td>${escapeHtml(c.location)}</td>
                    <td>${escapeHtml(c.hospital_name)}</td>
                    <td><span class="status ${priorityClass}">${escapeHtml(c.priority)}</span></td>
                    <td><span class="status ${statusClass}">${escapeHtml(c.status)}</span></td>
                    <td>${actionBtn}</td>
                `;
                tableBody.appendChild(tr);
            });
        }
    } catch (err) {
        console.warn("[Emergency Dashboard] Error fetching live backend emergencies:", err);
    }
}

async function handleEmergencySubmit(event) {
    if (event) event.preventDefault();

    var typeEl = document.getElementById("emgType");
    var priorityEl = document.getElementById("emgPriority");
    var locEl = document.getElementById("emgLocation");
    var hospEl = document.getElementById("emgHospital");
    var statusEl = document.getElementById("emgFormStatus");
    var submitBtn = document.getElementById("emgSubmitBtn");

    if (!typeEl || !locEl || !hospEl) return;

    var emergency_type = typeEl.value.trim();
    var priority = priorityEl ? priorityEl.value : "Critical";
    var location = locEl.value.trim();
    var hospital_name = hospEl.value.trim();

    if (!emergency_type || !location || !hospital_name) {
        if (statusEl) {
            statusEl.textContent = "Please fill all required fields.";
            statusEl.style.color = "#b91c1c";
        }
        return;
    }

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span> Logging case...';
    }
    if (statusEl) {
        statusEl.textContent = "Transmitting to emergency coordination backend...";
        statusEl.style.color = "#0e7490";
    }

    try {
        var client = getApiClient();
        var newCase = await client.createEmergency({
            emergency_type: emergency_type,
            priority: priority,
            location: location,
            hospital_name: hospital_name,
            status: "In Progress"
        });

        if (statusEl) {
            statusEl.innerHTML = `✅ <strong>Case Logged:</strong> Assigned ID <code>${escapeHtml(newCase.case_id)}</code>. Coordinated with ${escapeHtml(newCase.hospital_name)}.`;
            statusEl.style.color = "#15803d";
        }

        // Reset form
        typeEl.value = "";
        locEl.value = "";
        hospEl.value = "";

        // Refresh emergency metrics and table
        await loadEmergencyDashboard();
    } catch (err) {
        if (statusEl) {
            statusEl.textContent = `Submission failed: ${err.message}`;
            statusEl.style.color = "#b91c1c";
        }
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = "🚨 Submit Emergency Request";
        }
    }
}

async function updateCaseStatus(caseId, newStatus) {
    if (!caseId || !newStatus) return;

    try {
        var client = getApiClient();
        await client.updateEmergencyStatus(caseId, newStatus);
        await loadEmergencyDashboard();
    } catch (err) {
        alert("Failed to update case: " + err.message);
    }
}


// ============================================================================
// MODULE 4: AI PRELIMINARY REPORT ANALYSIS (reports.html)
// ============================================================================

async function analyzeReport() {
    var fileInput = document.getElementById("reportFile");
    var fileMessage = document.getElementById("fileMessage");
    var analysisResult = document.getElementById("analysisResult");

    if (!fileInput || !fileInput.files.length) {
        if (fileMessage) {
            fileMessage.textContent = "Please select a medical report file first.";
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

    // 3. Dispatch page-specific live data fetchers
    checkAssistantOnlineStatus();
    loadIndexOverview();
    loadResourceDashboard();
    loadEmergencyDashboard();
});
