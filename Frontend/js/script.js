
// AI HEALTH ASSISTANT

function sendMessage() {

    const input = document.getElementById("userInput");
    const chatMessages = document.getElementById("chatMessages");

    if (!input || !chatMessages) return;

    const question = input.value.trim();

    if (question === "") {
        return;
    }

    // Display user message
    const userMessage = document.createElement("div");

    userMessage.className = "message user-message";
    userMessage.textContent = question;

    chatMessages.appendChild(userMessage);

    input.value = "";

    // Generate demonstration response
    setTimeout(function() {

        const botMessage = document.createElement("div");

        botMessage.className = "message bot-message";
        botMessage.textContent = getHealthResponse(question);

        chatMessages.appendChild(botMessage);

        chatMessages.scrollTop = chatMessages.scrollHeight;

    }, 500);

    chatMessages.scrollTop = chatMessages.scrollHeight;
}


// Suggested questions
function askQuestion(question) {

    const input = document.getElementById("userInput");

    if (!input) return;

    input.value = question;

    sendMessage();
}


// Demonstration response system
function getHealthResponse(question) {

    const text = question.toLowerCase();

    if (text.includes("dehydration")) {

        return "Dehydration occurs when the body loses more fluids than it takes in. Common signs include thirst, dark urine, dry mouth and dizziness. Severe symptoms require urgent medical attention.";

    }

    else if (text.includes("diet") || text.includes("food")) {

        return "A balanced diet includes fruits, vegetables, whole grains, protein-rich foods and adequate water. Individual nutritional needs can vary.";

    }

    else if (text.includes("sleep")) {

        return "Sleep supports physical recovery, memory, concentration and overall well-being. Maintaining a regular sleep schedule can help improve sleep quality.";

    }

    else if (text.includes("headache")) {

        return "Headaches can have several causes, including dehydration, stress and lack of sleep. A sudden extremely severe headache or headache with weakness, confusion or vision loss needs emergency medical attention.";

    }

    else {

        return "Thank you for your question. I can currently provide only limited demonstration responses. Please consult a qualified healthcare professional for personalized medical guidance.";
    }
}


// Send message using Enter key
document.addEventListener("DOMContentLoaded", function() {

    const input = document.getElementById("userInput");

    if (input) {

        input.addEventListener("keydown", function(event) {

            if (event.key === "Enter") {
                sendMessage();
            }

        });

    }

});

function analyzeReport() {
    const fileInput = document.getElementById("reportFile");
    const fileMessage = document.getElementById("fileMessage");
    const analysisResult = document.getElementById("analysisResult");

    if (!fileInput || !fileInput.files.length) {
        fileMessage.textContent = "Please select a medical report first.";
        return;
    }

    const file = fileInput.files[0];

    fileMessage.textContent = "Selected file: " + file.name;

    analysisResult.innerHTML = `
        <h3>Report Received Successfully</h3>
        <p><strong>File Name:</strong> ${file.name.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</p>
        <p><strong>File Size:</strong> ${(file.size / 1024).toFixed(2)} KB</p>
        <p><strong>Status:</strong> Ready for preliminary review.</p>
        <p>This is a frontend demonstration. Actual medical report analysis
        requires a connected backend and AI model.</p>
    `;
}

function openFeature(feature) {
    const pages = {
        assistant: "assistant.html",
        resources: "resources.html",
        emergency: "emergency.html",
        reports: "reports.html"
    };

    if (pages[feature]) {
        window.location.href = pages[feature];
    }
}
