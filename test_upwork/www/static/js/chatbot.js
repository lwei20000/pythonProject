async function sendMessage() {
    const userInput = document.getElementById("userInput").value;
    if (!userInput) return;

    // Display user's message
    const messagesDiv = document.getElementById("messages");
    messagesDiv.innerHTML += `<p class="user-message">${userInput}</p>`;
    document.getElementById("userInput").value = ""; // Clear input

    // Send message to Flask backend
    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: userInput })
        });
        const data = await response.json();

        if (data.error) {
            messagesDiv.innerHTML += `<p class="bot-message">Error: ${data.error}</p>`;
        } else {
            messagesDiv.innerHTML += `<p class="bot-message">${data.response}</p>`;
        }
    } catch (error) {
        messagesDiv.innerHTML += `<p class="bot-message">Error connecting to server.</p>`;
    }

    // Auto-scroll to the latest message
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}