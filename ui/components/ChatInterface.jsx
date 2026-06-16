import { useState, useRef, useEffect } from 'react';
import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || '';
const AUTH_HEADERS = API_KEY ? { 'X-API-Key': API_KEY } : {};

export default function ChatInterface() {
  const [messages, setMessages] = useState([
    {
      type: 'assistant',
      text: 'Hi! I\'m your AI Knowledge Assistant. Ask me anything about the knowledge base.',
      sources: []
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [nRetrieve, setNRetrieve] = useState(3);
  const [apiStatus, setApiStatus] = useState(API_KEY ? 'checking' : 'missing-key');
  const messagesEndRef = useRef(null);

  // Check API health on mount
  useEffect(() => {
    if (API_KEY) {
      checkApiHealth();
    }
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const checkApiHealth = async () => {
    try {
      const response = await axios.get(`${API_URL}/health`, {
        timeout: 5000,
        headers: AUTH_HEADERS,
      });
      setApiStatus('connected');
    } catch (error) {
      setApiStatus('disconnected');
    }
  };

  const handleFileChange = (e) => {
    setSelectedFiles(Array.from(e.target.files || []));
  };

  const uploadFiles = async () => {
    if (!selectedFiles.length) return;

    setUploading(true);

    const formData = new FormData();
    selectedFiles.forEach((file) => {
      formData.append('files', file);
    });

    try {
      const response = await axios.post(`${API_URL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          ...AUTH_HEADERS,
        },
        timeout: 300000,
      });

      const uploadResult = response.data;
      const assistantMessage = {
        type: 'assistant',
        text: `Uploaded ${uploadResult.uploaded_files} file(s) and indexed ${uploadResult.chunks_ingested} chunks successfully. You can now ask questions about the new content.`,
        sources: [],
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setSelectedFiles([]);
    } catch (error) {
      const errorMessage = {
        type: 'error',
        text: `File upload failed: ${error.response?.data?.detail || error.message}`,
        sources: [],
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setUploading(false);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();

    if (!input.trim()) return;

    // Add user message
    const userMessage = {
      type: 'user',
      text: input,
      sources: []
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      // Call /ask endpoint
      const response = await axios.post(`${API_URL}/ask`, {
        question: input,
        n_retrieve: nRetrieve,
        model: 'llama3.1',
        temperature: 0.3,
      }, {
        headers: AUTH_HEADERS,
        timeout: 300000,
      });

      const { answer, sources, truncation_used, fallback_used, chunks_requested, chunks_used } = response.data;

      const extraNotes = [];
      if (truncation_used) {
        extraNotes.push('⚠️ Prompt was truncated to fit the LLM prompt size limit.');
      }
      if (fallback_used) {
        extraNotes.push('⚠️ The backend retried with fewer chunks to complete generation successfully.');
      }
      if (chunks_requested !== undefined && chunks_used !== undefined) {
        extraNotes.push(`Used ${chunks_used}/${chunks_requested} chunks.`);
      }

      const assistantText = [answer, ...extraNotes].filter(Boolean).join('\n\n');

      const assistantMessage = {
        type: 'assistant',
        text: assistantText,
        sources: sources || []
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      let errorMessage = 'Failed to get response. ';
      
      if (error.response?.status === 503) {
        errorMessage += 'Ollama service is not running. Please start it: ollama serve';
      } else if (error.response?.status === 500) {
        errorMessage += 'Server error. Check the backend logs.';
      } else if (error.code === 'ECONNREFUSED') {
        errorMessage += 'Cannot connect to API. Make sure the backend is running on port 8000.';
      } else if (error.message === 'timeout of 300000ms exceeded') {
        errorMessage += 'Request timed out. The LLM took too long to generate a response.';
      } else {
        errorMessage += error.message;
      }

      const errorMessage_ = {
        type: 'error',
        text: errorMessage,
        sources: []
      };
      setMessages((prev) => [...prev, errorMessage_]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <header className="bg-white shadow-md border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-bold text-lg">
              AI
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-800">Knowledge Assistant</h1>
              <p className="text-sm text-gray-500">Powered by RAG + Local LLM</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div
              className={`w-3 h-3 rounded-full ${
                apiStatus === 'connected'
                  ? 'bg-green-500'
                  : apiStatus === 'checking'
                  ? 'bg-yellow-500'
                  : 'bg-red-500'
              }`}
            />
            <span className="text-sm font-medium text-gray-600">
              {apiStatus === 'connected'
                ? 'Connected'
                : apiStatus === 'checking'
                ? 'Checking...'
                : apiStatus === 'missing-key'
                ? 'API key missing'
                : 'Offline'}
            </span>
          </div>
        </div>
      </header>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto bg-gradient-to-b from-blue-50 to-indigo-50">
        <div className="max-w-4xl mx-auto px-6 py-8 space-y-6">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${
                message.type === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              <div
                className={`max-w-2xl ${
                  message.type === 'user'
                    ? 'bg-indigo-600 text-white rounded-lg rounded-tr-none'
                    : message.type === 'error'
                    ? 'bg-red-100 text-red-800 rounded-lg rounded-tl-none border border-red-300'
                    : 'bg-white text-gray-800 rounded-lg rounded-tl-none shadow-md'
                } px-6 py-4`}
              >
                {/* Message Text */}
                <p className="text-base leading-relaxed mb-3">{message.text}</p>

                {/* Sources/Citations */}
                {message.sources && message.sources.length > 0 && (
                  <div className="border-t border-gray-300 pt-3 mt-3">
                    <p className="text-sm font-semibold mb-2">📚 Sources:</p>
                    <div className="space-y-1">
                      {message.sources.map((source, idx) => (
                        <div
                          key={idx}
                          className="text-sm bg-gray-50 rounded px-3 py-2 flex items-center justify-between"
                        >
                          <span className="font-medium text-gray-700">
                            {source.source}
                          </span>
                          <span className="text-gray-500 text-xs">
                            {(source.relevance * 100).toFixed(0)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-white text-gray-800 rounded-lg rounded-tl-none shadow-md px-6 py-4">
                <div className="flex items-center gap-2">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-indigo-600 rounded-full animate-bounce" />
                    <div className="w-2 h-2 bg-indigo-600 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                    <div className="w-2 h-2 bg-indigo-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                  </div>
                  <span className="text-sm text-gray-500 ml-2">Thinking...</span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <footer className="bg-white border-t border-gray-200 shadow-lg">
        <div className="max-w-4xl mx-auto px-6 py-4 space-y-4">
          <div className="grid gap-3 sm:grid-cols-[1fr_auto] items-end">
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">Upload documents</label>
              <input
                type="file"
                multiple
                accept=".md,.pdf,.docx,.csv,.txt,.text"
                onChange={handleFileChange}
                disabled={uploading}
                className="w-full text-sm text-gray-700 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
              />
              {selectedFiles.length > 0 && (
                <p className="text-xs text-gray-500">
                  Selected {selectedFiles.length} file(s): {selectedFiles.map((file) => file.name).join(', ')}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={uploadFiles}
              disabled={uploading || selectedFiles.length === 0 || apiStatus !== 'connected'}
              className="bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-medium px-6 py-3 rounded-lg transition-colors duration-200"
            >
              {uploading ? 'Uploading...' : 'Upload Files'}
            </button>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <span>Context chunks:</span>
              <input
                type="number"
                min={1}
                max={10}
                value={nRetrieve}
                onChange={(e) => setNRetrieve(Math.max(1, Math.min(10, Number(e.target.value) || 1)))}
                className="w-20 px-3 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-transparent"
              />
            </label>
            <p className="text-xs text-gray-500">Lower values are faster; higher values can return more context.</p>
          </div>
          <form onSubmit={sendMessage} className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask me anything about the knowledge base..."
              disabled={loading || apiStatus !== 'connected'}
              className="flex-1 px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            />
            <button
              type="submit"
              disabled={loading || !input.trim() || apiStatus !== 'connected'}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white font-medium px-6 py-3 rounded-lg transition-colors duration-200 flex items-center gap-2"
            >
              {loading ? (
                <>
                  <span className="animate-spin">⏳</span>
                  Thinking...
                </>
              ) : (
                <>
                  <span>Send</span>
                  <span>→</span>
                </>
              )}
            </button>
          </form>
          <p className="text-xs text-gray-500">
            Make sure Ollama is running: <code className="bg-gray-100 px-2 py-1 rounded">ollama serve</code>
          </p>
          {apiStatus === 'missing-key' && (
            <p className="text-xs text-red-600">
              Set <code className="bg-gray-100 px-2 py-1 rounded">NEXT_PUBLIC_API_KEY</code> in <code className="bg-gray-100 px-2 py-1 rounded">ui/.env.local</code> to authenticate with the backend.
            </p>
          )}
        </div>
      </footer>
    </div>
  );
}
