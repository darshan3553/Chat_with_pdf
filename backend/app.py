from flask import Flask, request, jsonify
import os
import PyPDF2
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from together import Together
from flask_cors import CORS

# ✅ Use environment variable for sensitive data like API keys
TOGETHER_API_KEY = os.environ.get("TOGETHER_API_KEY")

# Create Flask app and enable CORS
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Limit file uploads to 50MB
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# Define upload folder
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global state
pdf_chunks = []
pdf_index = None
embedder = None  # Lazy loaded
client = Together(api_key=TOGETHER_API_KEY) if TOGETHER_API_KEY else None


# 🔹 Helper: Chunk text
def chunk_text(text, chunk_size=500, overlap=50):
    words = text.split()
    chunks, start = [], 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


@app.route("/")
def health():
    return jsonify({"status": "running"}), 200


@app.route("/upload", methods=["POST"])
def upload_file():
    """Handles PDF upload, text extraction, and indexing."""
    global pdf_chunks, pdf_index, embedder

    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    # Save uploaded file
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    # ✅ Extract text
    try:
        pdf_reader = PyPDF2.PdfReader(file_path)
        text = "\n".join(page.extract_text() or "" for page in pdf_reader.pages)
    except Exception as e:
        return jsonify({"error": f"Failed to read PDF file: {e}"}), 500

    if not text.strip():
        return jsonify({"error": "The PDF file appears to be empty or unscannable."}), 400

    # 🔹 Chunk the text
    pdf_chunks = chunk_text(text)

    # 🔹 Lazy load embedder
    if embedder is None:
        embedder = SentenceTransformer("all-MiniLM-L6-v2")

    embeddings = embedder.encode(pdf_chunks, convert_to_numpy=True)

    # 🔹 Create FAISS index
    dim = embeddings.shape[1]
    pdf_index = faiss.IndexFlatL2(dim)
    pdf_index.add(embeddings)

    return jsonify({
        "filename": file.filename,
        "num_pages": len(pdf_reader.pages),
        "chunks": len(pdf_chunks),
        "message": "PDF uploaded & indexed successfully!"
    })


@app.route("/ask", methods=["POST"])
def ask_question():
    """Answers user questions using retrieved context + Together AI."""
    global pdf_chunks, pdf_index, embedder, client

    data = request.get_json()
    question = data.get("question", "")

    if not question.strip():
        return jsonify({"answer": "Please ask a valid question."}), 400
    if pdf_index is None:
        return jsonify({"answer": "No PDF uploaded yet. Please upload one first."}), 400
    if client is None:
        return jsonify({"answer": "API key not configured. Cannot answer."}), 503

    # 🔹 Embed the question
    q_embedding = embedder.encode([question], convert_to_numpy=True)

    # 🔹 Search FAISS
    k = 3
    D, I = pdf_index.search(q_embedding, k)
    retrieved_chunks = [pdf_chunks[i] for i in I[0]]

    # 🔹 Create prompt
    context = "\n\n".join(retrieved_chunks)
    prompt = f"""
    You are a helpful assistant. 
    Answer the question based only on the following PDF content. 
    If the answer is not in the document, say so.

    PDF Content: {context}
    Question: {question}
    """

    try:
        response = client.chat.completions.create(
            model="meta-llama/Llama-3-70b-chat-hf",
            messages=[{"role": "user", "content": prompt}],
        )
        answer = response.choices[0].message.content
    except Exception as e:
        return jsonify({"answer": f"Error with LLM API: {e}"}), 500

    return jsonify({"answer": answer})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
