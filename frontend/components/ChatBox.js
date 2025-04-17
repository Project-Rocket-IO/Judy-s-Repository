import { useState } from "react";
import axios from "axios";

export default function ChatBox() {
    const [message, setMessage] = useState("");
    const [messages, setMessages] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [mode, setMode] = useState("chat");


    const toggleMode = (newMode) => {
        setMode(newMode);
        setMessages([]);
    };

    const sendMessage = async () => {
        if (!message.trim()) {
            setError("Please enter a message.");
            return;
        }

        const userMessage = { sender: "user", text: message };
        setMessages((prev) => [...prev, userMessage]);
        setMessage("");
        setIsLoading(true);
        setError(null);

        try {
            const res = await axios.post("http://127.0.0.1:8000/chatbot/", {
                message,
                action_type: mode
            });

            const botMessage = { sender: "bot", text: res.data.response };
            setMessages((prev) => [...prev, botMessage]);
        } catch (err) {
            setError("An error occurred while sending the message.");
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === "Enter") {
            sendMessage();
        }
    };

    return (
        <div style={{ padding: "20px", maxWidth: "600px", margin: "auto" }}>
            <h1>AI Chatbot</h1>

            {/* Tab buttons */}
            <div style={{ display: "flex", justifyContent: "center", marginBottom: "20px" }}>
                <button
                    onClick={() => toggleMode("chat")}
                    style={{
                        padding: "10px 20px",
                        backgroundColor: mode === "chat" ? "#007bff" : "#f1f1f1",
                        color: mode === "chat" ? "#fff" : "#000",
                        border: "1px solid #ccc",
                        cursor: "pointer",
                        borderRadius: "5px",
                    }}
                >
                    General Chat
                </button>
                <button
                    onClick={() => toggleMode("update_ticket")}
                    style={{
                        padding: "10px 20px",
                        backgroundColor: mode === "update_ticket" ? "#28a745" : "#f1f1f1",
                        color: mode === "update_ticket" ? "#fff" : "#000",
                        border: "1px solid #ccc",
                        cursor: "pointer",
                        borderRadius: "5px",
                        marginLeft: "10px"
                    }}
                >
                    Update DB
                </button>
            </div>

            <div style={{ maxHeight: "300px", overflowY: "auto", padding: "10px", border: "1px solid #ccc", borderRadius: "5px", marginBottom: "10px" }}>
                {messages.map((msg, idx) => (
                    <div key={idx} style={{ textAlign: msg.sender === "user" ? "right" : "left", margin: "10px 0" }}>
                        <strong>{msg.sender === "user" ? "You" : "Bot"}:</strong> {msg.text}
                    </div>
                ))}
                {isLoading && <p>Bot is typing...</p>}
            </div>

            <input
                type="text"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKeyPress}
                disabled={isLoading}
                placeholder={mode === "chat" ? "Type your message..." : "Enter ticket details..."}
                style={{ width: "100%", padding: "10px", marginBottom: "10px" }}
            />

            <button
                onClick={sendMessage}
                disabled={isLoading}
                style={{
                    width: "100%",
                    padding: "10px",
                    backgroundColor: "#007bff",
                    color: "#fff",
                    border: "none",
                    cursor: "pointer"
                }}
            >
                {isLoading ? "Sending..." : "Send"}
            </button>

            {error && <p style={{ color: "red", marginTop: "10px" }}>{error}</p>}
        </div>
    );
}
