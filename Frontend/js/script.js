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
        sendChatMessage: function(message, context) {
            return this.request("/api/assistant/chat", { method: "POST", body: { message: message, context: context || null } });
        },
        getResources: function() { return this.request("/api/resources"); },
        getResourceSummary: function() { return this.request("/api/resources/summary"); },
        getEmergencies: function() { return this.request("/api/emergency"); },
        getEmergencySummary: function() { return this.request("/api/emergency/summary"); },
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
    typingMessage.innerHTML = '<span class="spinner"></span> Consulting MEDICHAIN AI engine...';
    chatMessages.appendChild(typingMessage);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Call real FastAPI backend: POST /api/assistant/chat
    try {
        var client = getApiClient();
        var data = await client.sendChatMessage(question);

        // Remove typing indicator
        if (typingMessage.parentNode) {
            typingMessage.parentNode.removeChild(typingMessage);
        }

        // Display bot response bubble
        var botMessage = document.createElement("div");
        botMessage.className = "message bot-message";

        var textPara = document.createElement("p");
        textPara.textContent = data.reply || "No response received from clinical engine.";
        botMessage.appendChild(textPara);

        // Source badge (Gemini API vs Medical Knowledge Engine)
        var badge = document.createElement("span");
        if (data.source === "gemini_api") {
            badge.className = "api-badge live";
            badge.textContent = "🤖 Powered by Gemini AI";
        } else {
            badge.className = "api-badge ai";
            badge.textContent = "🩺 MEDICHAIN Medical Engine";
        }
        botMessage.appendChild(badge);

        chatMessages.appendChild(botMessage);
    } catch (error) {
        if (typingMessage.parentNode) {
            typingMessage.parentNode.removeChild(typingMessage);
        }

        var errorMessage = document.createElement("div");
        errorMessage.className = "message bot-message";
        errorMessage.innerHTML = `
            <p style="color: #b91c1c;"><strong>⚠️ Connection Notice:</strong> Unable to reach the backend service (${escapeHtml(error.message)}).</p>
            <p style="font-size: 13px; margin-top: 6px; color: #64748b;">Please verify that the backend is running at <code>http://127.0.0.1:8000</code>.</p>
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
// MODULE 2: HOSPITAL RESOURCE DASHBOARD (resources.html)
// ============================================================================

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

        // 2. Populate Resource Table
        if (Array.isArray(resources) && resources.length > 0) {
            tableBody.innerHTML = "";
            resources.forEach(function(res) {
                var tr = document.createElement("tr");

                var statusClass = "available";
                var st = (res.status || "").toLowerCase();
                if (st.includes("warn") || st.includes("low")) statusClass = "warning";
                else if (st.includes("occup") || st.includes("critical") || st.includes("full")) statusClass = "occupied";

                tr.innerHTML = `
                    <td>${escapeHtml(res.resource_type)}</td>
                    <td>${res.total}</td>
                    <td>${res.available}</td>
                    <td>${res.occupied}</td>
                    <td><span class="status ${statusClass}">${escapeHtml(res.status || "Available")}</span></td>
                `;
                tableBody.appendChild(tr);
            });
        }
    } catch (err) {
        console.warn("[Resource Dashboard] Error fetching live backend resources:", err);
    }
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

                tr.innerHTML = `
                    <td><strong>${escapeHtml(c.case_id)}</strong></td>
                    <td>${escapeHtml(c.emergency_type)}</td>
                    <td>${escapeHtml(c.location)}</td>
                    <td>${escapeHtml(c.hospital_name)}</td>
                    <td><span class="status ${priorityClass}">${escapeHtml(c.priority)}</span></td>
                    <td><span class="status ${statusClass}">${escapeHtml(c.status)}</span></td>
                `;
                tableBody.appendChild(tr);
            });
        }
    } catch (err) {
        console.warn("[Emergency Dashboard] Error fetching live backend emergencies:", err);
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
    const raw = localStorage.getItem("medichain_auth") || sessionStorage.getItem("medichain_auth");
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
    const sidebar = document.querySelector(".sidebar");
    if (!sidebar) return;

    sidebar.classList.toggle("collapsed");
    const isCollapsed = sidebar.classList.contains("collapsed");
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
    const isCollapsed = localStorage.getItem("medichain_sidebar_collapsed") === "true";
    if (isCollapsed) {
        const sidebar = document.querySelector(".sidebar");
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
    loadIndexOverview();
    loadResourceDashboard();
    loadEmergencyDashboard();
});
