/**
 * MEDICHAIN AI Health Assistant Module
 * Dedicated handler for assistant.html
 */

(function(global) {
    "use strict";

    // Re-export or alias assistant functions for standalone modular usage
    if (typeof global.sendMessage === "function") {
        global.assistantSendMessage = global.sendMessage;
        global.assistantAskQuestion = global.askQuestion;
    }
})(typeof window !== "undefined" ? window : this);

