import { useState } from "react";
import axios from "axios";

export default function ChatBox() {
    const [message, setMessage] = useState("");
    const [response, setResponse] = useState("");
    const [isLoading, setIsLoading] = useState(false); // To handle loading state
    const [error, setError] = useState(null); // To handle errors

    const sendMessage = async () => {
        if (!message.trim()) {
            setError("Please enter a message."); // Validate empty input
            return;
        }

        setIsLoading(true);
        setError(null);

        try {
            const res = await axios.post("http://127.0.0.1:8000/chatbot/", { message : message });
            setResponse(res.data.response);
        } catch (err) {
            setError("An error occurred while sending the message."); // Handle API errors
            console.error(err);
        } finally {
            setIsLoading(false); // Reset loading state
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === "Enter") {
            sendMessage(); // Allow sending message on pressing Enter
        }
    };

    return (
        <div style={{ padding: "20px", maxWidth: "400px", margin: "auto" }}>
            <h1>Chatbot</h1>
            <div>
                <input
                    type="text"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    disabled={isLoading} // Disable input while loading
                    placeholder="Type your message..."
                    style={{ width: "100%", padding: "10px", marginBottom: "10px" }}
                />
                <button
                    onClick={sendMessage}
                    disabled={isLoading} // Disable button while loading
                    style={{ width: "100%", padding: "10px", backgroundColor: "#007bff", color: "#fff", border: "none", cursor: "pointer" }}
                >
                    {isLoading ? "Sending..." : "Send"}
                </button>
            </div>
            {error && <p style={{ color: "red" }}>{error}</p>}
            {response && (
                <div style={{ marginTop: "20px", padding: "10px", backgroundColor: "#000000", borderRadius: "5px" }}>
                    <p><strong>Response:</strong> {response}</p>
                </div>
            )}
        </div>
    );
}