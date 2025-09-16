import { useEffect, useRef } from "react";

export function ChatBox({ messages, isLoading }) {
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="space-y-6">
      {messages.length === 0 ? (
        <div className="flex justify-center items-center h-full">
          <p className="text-gray-400 text-lg italic">Upload a PDF and ask a question to get started.</p>
        </div>
      ) : (
        messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'} message-fade-in`}>
            <div className={`p-4 rounded-3xl max-w-xl shadow-md transition-all ${
              msg.sender === 'user'
                ? 'bg-indigo-600 text-white rounded-br-none'
                : 'bg-white text-gray-900 border border-gray-100 rounded-bl-none'
            }`}>
              <div className="whitespace-pre-wrap">{msg.text}</div>
            </div>
          </div>
        ))
      )}
      {isLoading && (
        <div className="flex justify-start">
          <div className="p-4 rounded-3xl max-w-xl shadow-md bg-white text-gray-900 border border-gray-100 rounded-bl-none">
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-indigo-500 rounded-full dot-pulse"></div>
              <div className="w-2 h-2 bg-indigo-500 rounded-full dot-pulse"></div>
              <div className="w-2 h-2 bg-indigo-500 rounded-full dot-pulse"></div>
            </div>
          </div>
        </div>
      )}
      <div ref={chatEndRef} />
    </div>
  );
}
