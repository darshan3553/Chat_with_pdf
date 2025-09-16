import { useState } from "react";
import axios from "axios";

export function SearchBar({ onSearch, isLoading, setIsLoading }) {
  const [question, setQuestion] = useState("");

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!question.trim() || isLoading) return;

    onSearch({ sender: "user", text: question });
    setQuestion("");
    setIsLoading(true);

    try {
      const res = await axios.post("http://localhost:5000/ask", { question });
      onSearch({ sender: "ai", text: res.data.answer });
    } catch (err) {
      console.error("Search error:", err.response ? err.response.data : err.message);
      onSearch({ sender: "ai", text: "Sorry, I couldn't get an answer. Please make sure a PDF is uploaded and the backend is running." });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSearch} className="relative">
      <input
        type="text"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        className="w-full px-5 py-3 pr-14 text-sm bg-gray-100 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
        placeholder="Ask a question about your PDF..."
        disabled={isLoading}
      />
      <button
        type="submit"
        disabled={!question.trim() || isLoading}
        className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-indigo-600 text-white rounded-full hover:bg-indigo-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
      >
        {isLoading ? (
          <div className="flex space-x-1">
            <div className="w-1.5 h-1.5 bg-white rounded-full dot-pulse"></div>
            <div className="w-1.5 h-1.5 bg-white rounded-full dot-pulse"></div>
            <div className="w-1.5 h-1.5 bg-white rounded-full dot-pulse"></div>
          </div>
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
          </svg>
        )}
      </button>
    </form>
  );
}
