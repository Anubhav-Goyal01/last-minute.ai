import { useState } from "react";
import styles from "./ChatWithYourData.module.css"; // Import the CSS module

export const ChatWithYourData = () => {
  const [input, setInput] = useState("");
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [suggestedQuestions, setSuggestedQuestions] = useState([]);

  const handleInputChange = (event) => {
    setInput(event.target.value);
  };

  const handleGenerateAnswerClick = async () => {
    if (input.trim() === "") {
      // Ignore empty input
      return;
    }

    setLoading(true);

    // Generate answer for the user input
    const answer = await getAnswerFromBackend(input);
    setLoading(false);
    // Add the user input and generated answer to conversations
    setConversations([
      ...conversations,
      { question: input, answer: answer["Answer"] },
    ]);

    // Clear input field
    setInput("");

    // Fetch new suggested questions
    const newSuggestedQuestions = answer["Questions"];
    setSuggestedQuestions(newSuggestedQuestions);
  };

  const handleSuggestedQuestionClick = async (question) => {
    setInput(question);
    await handleGenerateAnswerClick();
  };

  const getAnswerFromBackend = (question) => {
    const fetchOptions = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ question: question }),
    };

    return fetch("http://localhost:5000/get_answer", fetchOptions)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Failed to fetch answer");
        }
        return response.json(); // Assuming the response is a text string
      })
      .catch((error) => {
        console.error("Error fetching answer:", error);
        throw error; // Re-throw the error to be caught by the caller
      });
  };

  return (
    <div className={styles.chatContainer}>
      <header className={styles.header}>
        <h1>Chat with your Personal AI tutor</h1>
        <p>Ask anything from your docs</p>
      </header>

      <div className={styles.inputContainer}>
        <input
          type="text"
          value={input}
          onChange={handleInputChange}
          placeholder="Ask a question..."
          className={styles.input}
        />
        <button onClick={handleGenerateAnswerClick} className={styles.button}>
          Start Generating
        </button>
      </div>

      <div className={styles.conversations}>
        {conversations.map((conv, index) => (
          <div key={index} className={styles.conversationEntry}>
            <p className={styles.question}>
              <strong>Q:</strong> {conv.question}
            </p>
            <p className={styles.answer}>
              <strong>A:</strong> {conv.answer}
            </p>
          </div>
        ))}
      </div>

      {loading && <div className={styles.loading}>Generating...</div>}

      {!loading && suggestedQuestions.length > 0 && (
        <div className={styles.suggestedQuestions}>
          {suggestedQuestions.map((question, index) => (
            <button
              key={index}
              className={styles.suggestedQuestion}
              onClick={() => handleSuggestedQuestionClick(question)}
            >
              {question}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default ChatWithYourData;
