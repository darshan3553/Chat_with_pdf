import { useState } from "react";
import axios from "axios";

export function FileUpload({ onFileUploaded, setIsUploading, isUploading }) {
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    setFile(selectedFile);
    if (selectedFile) {
      setMessage(`Selected: ${selectedFile.name}`);
    } else {
      setMessage("");
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setMessage("Please select a PDF first!");
      return;
    }

    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await axios.post("http://localhost:5000/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const info = {
        filename: res.data.filename,
        pages: res.data.num_pages,
        chunks: res.data.chunks,
      };
      setMessage(`✅ Uploaded: ${info.filename}`);
      onFileUploaded(info);
    } catch (err) {
      console.error("Upload error:", err.response ? err.response.data : err.message);
      setMessage("❌ Upload failed: " + (err.response?.data?.error || err.message));
    } finally {
      setIsUploading(false);
      setFile(null); // Clear the file input
    }
  };

  return (
    <div className="p-4 border border-gray-200 rounded-2xl bg-white shadow-sm">
      <label className="block mb-2 text-sm font-semibold text-gray-700">
        Upload PDF
      </label>
      <input
        type="file"
        accept="application/pdf"
        onChange={handleFileChange}
        className="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-gray-200 file:text-gray-700 hover:file:bg-gray-300 transition-colors"
      />
      <button
        onClick={handleUpload}
        disabled={!file || isUploading}
        className={`mt-3 w-full px-4 py-2 text-white rounded-xl shadow-md transition-all ${
          !file || isUploading
            ? "bg-gray-400 cursor-not-allowed"
            : "bg-green-600 hover:bg-green-700"
        }`}
      >
        {isUploading ? "Uploading..." : "Upload & Process"}
      </button>
      {message && <p className="mt-2 text-xs text-center text-gray-500">{message}</p>}
    </div>
  );
}
