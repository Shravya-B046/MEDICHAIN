/**
 * MEDICHAIN Shared API Client
 * Connects frontend vanilla JavaScript modules with the FastAPI backend.
 * Compatible with all modern browsers and local server origins.
 */

(function(global) {
    "use strict";

    // Dynamic base URL resolving to backend port 8000
    var API_BASE_URL = (function() {
        if (typeof window !== "undefined" && window.location) {
            // Match host to prevent IPv4/IPv6 hostname cross-origin mismatch
            if (window.location.hostname === "localhost") {
                return "http://localhost:8000";
            }
        }
        return "http://127.0.0.1:8000";
    })();

    var MedichainApiClient = {
        baseUrl: API_BASE_URL,

        /**
         * Generic helper for JSON and multipart HTTP requests with error handling
         */
        request: async function(endpoint, options) {
            options = options || {};
            var url = this.baseUrl + endpoint;
            var headers = Object.assign({
                "Accept": "application/json"
            }, options.headers || {});

            if (options.body && !(options.body instanceof FormData)) {
                headers["Content-Type"] = "application/json";
                options.body = typeof options.body === "string" 
                    ? options.body 
                    : JSON.stringify(options.body);
            }

            try {
                var response = await fetch(url, {
                    method: options.method || "GET",
                    headers: headers,
                    body: options.body
                });

                if (!response.ok) {
                    var errorMessage = "HTTP " + response.status + ": " + response.statusText;
                    try {
                        var errData = await response.json();
                        if (errData && errData.detail) {
                            errorMessage = typeof errData.detail === "string" 
                                ? errData.detail 
                                : JSON.stringify(errData.detail);
                        }
                    } catch (_) {}
                    throw new Error(errorMessage);
                }

                return await response.json();
            } catch (error) {
                console.error("[MEDICHAIN API Error] " + endpoint + ":", error);
                throw error;
            }
        },

        // Health Check
        checkHealth: function() {
            return this.request("/api/health");
        },

        // Module 1: AI Health Assistant
        sendChatMessage: function(message, context) {
            return this.request("/api/assistant/chat", {
                method: "POST",
                body: { message: message, context: context || null }
            });
        },

        // Module 2: Hospital Resources
        getResources: function() {
            return this.request("/api/resources");
        },

        getResourceSummary: function() {
            return this.request("/api/resources/summary");
        },

        updateResource: function(id, updateData) {
            return this.request("/api/resources/" + id, {
                method: "PUT",
                body: updateData
            });
        },

        // Module 3: Emergency Coordination
        getEmergencies: function() {
            return this.request("/api/emergency");
        },

        getEmergencySummary: function() {
            return this.request("/api/emergency/summary");
        },

        createEmergency: function(caseData) {
            return this.request("/api/emergency", {
                method: "POST",
                body: caseData
            });
        },

        updateEmergencyStatus: function(caseId, status, priority) {
            return this.request("/api/emergency/" + caseId + "/status", {
                method: "PATCH",
                body: { status: status, priority: priority || null }
            });
        },

        // Module 4: AI Preliminary Report Analysis
        uploadReport: function(file) {
            var formData = new FormData();
            formData.append("file", file);

            return this.request("/api/reports/upload", {
                method: "POST",
                body: formData
            });
        },

        // Hospital Administration
        getHospitals: function() {
            return this.request("/api/hospitals");
        },

        createHospital: function(data) {
            return this.request("/api/hospitals", {
                method: "POST",
                body: data
            });
        },

        deleteHospital: function(id) {
            return this.request("/api/hospitals/" + id, {
                method: "DELETE"
            });
        }
    };

    // Export to all conventional names on window and global
    global.medichainApi = MedichainApiClient;
    global.MedichainAPI = MedichainApiClient;
    global.api = MedichainApiClient;
    global.API = MedichainApiClient;

    if (typeof window !== "undefined") {
        window.medichainApi = MedichainApiClient;
        window.MedichainAPI = MedichainApiClient;
        window.api = MedichainApiClient;
        window.API = MedichainApiClient;

        try {
            window.dispatchEvent(new CustomEvent("medichainApiReady", { detail: MedichainApiClient }));
        } catch (_) {}
    }

})(typeof window !== "undefined" ? window : this);
