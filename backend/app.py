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

# Create Flask app and enable CORS for local development
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})

# Limit file uploads to 50MB
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# Define upload folder and create it if it doesn't exist
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global storage for the PDF chunks and the FAISS index
pdf_chunks = []
pdf_index = None

# Initialize the Sentence Transformer model for creating embeddings
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# Initialize the TogetherAI client using the environment variable
if TOGETHER_API_KEY:
    client = Together(api_key=TOGETHER_API_KEY)
else:
    client = None
    print("⚠️ Warning: TOGETHER_API_KEY environment variable not set. API calls will fail.")


# 🔹 Helper function to split text into manageable chunks
def chunk_text(text, chunk_size=500, overlap=50):
    words = text.split()
    chunks, start = [], 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        # Move the start position back to create overlap
        start += chunk_size - overlap
    return chunks


@app.route("/upload", methods=["POST"])
def upload_file():
    """Handles the PDF file upload, text extraction, and indexing."""
    global pdf_chunks, pdf_index

    # Check if a file was included in the request
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    # Save uploaded file
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    # ✅ Extract text from the PDF
    try:
        pdf_reader = PyPDF2.PdfReader(file_path)
        text = ""
        for page in pdf_reader.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"
    except Exception as e:
        return jsonify({"error": f"Failed to read PDF file: {e}"}), 500

    if not text.strip():
        return jsonify({"error": "The PDF file appears to be empty or unscannable."}), 400

    # 🔹 Chunk the extracted text
    pdf_chunks = chunk_text(text)

    # Convert chunks to embeddings
    embeddings = embedder.encode(pdf_chunks, convert_to_numpy=True)

    # 🔹 Store embeddings in FAISS index
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
    """Handles the user's question, retrieves relevant context, and gets an answer from Together AI."""
    global pdf_chunks, pdf_index

    data = request.get_json()
    question = data.get("question", "")

    # Validate
    if not question.strip():
        return jsonify({"answer": "Please ask a valid question."}), 400
    if pdf_index is None:
        return jsonify({"answer": "No PDF uploaded yet. Please upload one first."}), 400
    if client is None:
        return jsonify({"answer": "API key not configured. Cannot answer."}), 503

    # 🔹 Embed the question
    q_embedding = embedder.encode([question], convert_to_numpy=True)

    # 🔹 Search FAISS index for top 'k' chunks
    k = 3
    D, I = pdf_index.search(q_embedding, k)
    retrieved_chunks = [pdf_chunks[i] for i in I[0]]

    # 🔹 Create prompt
    context = "\n\n".join(retrieved_chunks)
    prompt = f"""
    You are a helpful assistant. 
    Answer the question based only on the following PDF content. 
    Do not use any external knowledge. 
    If the answer is not in the document, state that you cannot find the information.

    PDF Content: {context}
    Question: {question}
    """

    # 🔹 Call TogetherAI API
    try:
        response = client.chat.completions.create(
            model="meta-llama/Llama-3-70b-chat-hf",
            messages=[{"role": "user", "content": prompt}],
        )
        answer = response.choices[0].message.content
    except Exception as e:
        return jsonify({"answer": f"An error occurred with the LLM API: {e}"}), 500

    return jsonify({"answer": answer})


if __name__ == "__main__":
    app.run(debug=True)
