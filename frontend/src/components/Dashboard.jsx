import { useState, useEffect, useRef } from 'react'
import AdminUserPanel from './AdminUserPanel'

const API_BASE_URL = '/api/v1'

export default function Dashboard({ user, token, onLogout }) {
  const [activeTab, setActiveTab] = useState('ai-interaction')
  
  // Posture state
  const [analyzing, setAnalyzing] = useState(false)
  const [postureResult, setPostureResult] = useState(null)
  const [uploadFile, setUploadFile] = useState(null)
  
  // Webcam state
  const [webcamActive, setWebcamActive] = useState(false)
  const [autoAnalyze, setAutoAnalyze] = useState(false)
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const autoAnalyzeTimer = useRef(null)
  const streamRef = useRef(null)

  // Chatbot state
  const [chatMessage, setChatMessage] = useState('')
  const [chatHistory, setChatHistory] = useState([
    {
      role: 'assistant',
      content: 'Hello! I am the **LifeCare Virtual Assistant**, powered by LLaMA. Ask me anything about ergonomics, joint health, stretching exercises, or help with interpreting your posture logs!'
    }
  ])
  const [chatLoading, setChatLoading] = useState(false)
  const [chatModelInfo, setChatModelInfo] = useState('LLaMA')
  const chatBottomRef = useRef(null)

  // Analytics states
  const [history, setHistory] = useState([])
  const [stats, setStats] = useState(null)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [zoomImage, setZoomImage] = useState(null)

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatHistory, chatLoading])

  // Fetch history and stats
  const fetchAnalytics = async () => {
    setLoadingHistory(true)
    try {
      // 1. Fetch History
      const histResponse = await fetch(`${API_BASE_URL}/ai/history`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (histResponse.ok) {
        const histData = await histResponse.json()
        setHistory(histData)
      }

      // 2. Fetch Stats
      const statsResponse = await fetch(`${API_BASE_URL}/ai/stats`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (statsResponse.ok) {
        const statsData = await statsResponse.json()
        setStats(statsData)
      }
    } catch (err) {
      console.error('Error fetching analytics:', err)
    } finally {
      setLoadingHistory(false)
    }
  }

  // Load analytics when Tab changes to 'analytics'
  useEffect(() => {
    if (activeTab === 'analytics') {
      fetchAnalytics()
    }
  }, [activeTab])

  // Cleanup webcam stream on unmount
  useEffect(() => {
    return () => {
      stopWebcam()
    }
  }, [])

  // Webcam controls
  const startWebcam = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 }
      })
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        streamRef.current = stream
        setWebcamActive(true)
      }
    } catch (err) {
      alert('Could not access webcam. Make sure permissions are granted.')
      console.error(err)
    }
  }

  const stopWebcam = () => {
    setAutoAnalyze(false)
    if (autoAnalyzeTimer.current) {
      clearInterval(autoAnalyzeTimer.current)
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setWebcamActive(false)
  }

  // Capture frame and send to base64 endpoint
  const captureAndAnalyze = async () => {
    if (!videoRef.current || !canvasRef.current || analyzing) return
    
    setAnalyzing(true)
    const video = videoRef.current
    const canvas = canvasRef.current
    const context = canvas.getContext('2d')
    
    // Draw current frame to canvas
    context.drawImage(video, 0, 0, canvas.width, canvas.height)
    const base64Image = canvas.toDataURL('image/jpeg')
    
    try {
      const response = await fetch(`${API_BASE_URL}/ai/analyze-base64`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ image: base64Image })
      })
      
      if (!response.ok) {
        const errData = await response.json()
        throw new Error(errData.detail || 'Analysis error')
      }
      
      const data = await response.json()
      setPostureResult(data)
      
      // Refresh analytics in background if on analytics tab
      if (activeTab === 'analytics') {
        fetchAnalytics()
      }
    } catch (err) {
      console.error(err)
      if (!autoAnalyze) {
        alert(err.message || 'Webcam analysis failed.')
      }
    } finally {
      setAnalyzing(false)
    }
  }

  // Handle auto-analyze toggle
  useEffect(() => {
    if (autoAnalyze && webcamActive) {
      autoAnalyzeTimer.current = setInterval(() => {
        captureAndAnalyze()
      }, 3000)
    } else {
      if (autoAnalyzeTimer.current) {
        clearInterval(autoAnalyzeTimer.current)
      }
    }
    return () => {
      if (autoAnalyzeTimer.current) {
        clearInterval(autoAnalyzeTimer.current)
      }
    }
  }, [autoAnalyze, webcamActive])

  // File Upload analyze
  const handleFileUpload = async (e) => {
    e.preventDefault()
    if (!uploadFile) return
    
    setAnalyzing(true)
    setPostureResult(null)
    
    const formData = new FormData()
    formData.append('file', uploadFile)
    
    try {
      const response = await fetch(`${API_BASE_URL}/ai/analyze`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`
        },
        body: formData
      })
      
      if (!response.ok) {
        const errData = await response.json()
        throw new Error(errData.detail || 'Analysis error')
      }
      
      const data = await response.json()
      setPostureResult(data)
    } catch (err) {
      alert(err.message || 'Image analysis failed.')
      console.error(err)
    } finally {
      setAnalyzing(false)
    }
  }

  // Submit Chatbot query
  const handleChatSubmit = async (e) => {
    e.preventDefault()
    if (!chatMessage.trim() || chatLoading) return
    
    const userPrompt = chatMessage.trim()
    setChatMessage('')
    
    // Add user message to history
    const updatedHistory = [...chatHistory, { role: 'user', content: userPrompt }]
    setChatHistory(updatedHistory)
    setChatLoading(true)
    
    try {
      const cleanHistory = updatedHistory.slice(1).map(h => ({
        role: h.role,
        content: h.content
      }))

      const response = await fetch(`${API_BASE_URL}/chatbot/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          message: userPrompt,
          history: cleanHistory
        })
      })
      
      if (!response.ok) {
        throw new Error('Could not contact chatbot service.')
      }
      
      const data = await response.json()
      setChatHistory([
        ...updatedHistory,
        { role: 'assistant', content: data.response }
      ])
      setChatModelInfo(data.model_used)
    } catch (err) {
      setChatHistory([
        ...updatedHistory,
        { role: 'assistant', content: `⚠️ **Error**: ${err.message}` }
      ])
    } finally {
      setChatLoading(false)
    }
  }

  return (
    <div className="dashboard-container">
      {/* Dashboard Subheader */}
      <div className="dashboard-header">
        <div>
          <h1>Welcome, <span className="highlight-text">{user.username}</span>!</h1>
          <p className="subtitle">LifeCare Premium Health Portal</p>
        </div>
        
        {/* Navigation Tabs */}
        <div className="dashboard-tabs">
          <button 
            type="button" 
            className={`tab-btn ${activeTab === 'ai-interaction' ? 'active' : ''}`}
            onClick={() => { stopWebcam(); setActiveTab('ai-interaction') }}
          >
            🤖 AI Interaction Dashboard
          </button>
          <button 
            type="button" 
            className={`tab-btn ${activeTab === 'analytics' ? 'active' : ''}`}
            onClick={() => { stopWebcam(); setActiveTab('analytics') }}
          >
            📊 Analytics & History
          </button>
        </div>
      </div>

      {/* Main Interfaces */}
      {activeTab === 'ai-interaction' ? (
        <div className="tab-content-grid">
          
          {/* Posture Analysis Panel */}
          <div className="dashboard-card posture-panel">
            <div className="panel-header">
              <h2>🧍 AI Posture Corrector</h2>
              <p className="card-desc">Analyze your posture ergonomics using our trained models.</p>
            </div>
            
            <div className="posture-methods">
              {/* Method 1: Webcam testing */}
              <div className="method-box webcam-box">
                <h3>Real-Time Webcam Analysis</h3>
                
                <div className="webcam-viewport">
                  {webcamActive ? (
                    <>
                      <video ref={videoRef} className="webcam-feed" autoPlay playsInline muted />
                      <canvas ref={canvasRef} width="640" height="480" style={{ display: 'none' }} />
                    </>
                  ) : (
                    <div className="webcam-placeholder">
                      <span className="camera-icon">📷</span>
                      <p>Webcam is currently disabled</p>
                    </div>
                  )}
                </div>

                <div className="webcam-controls">
                  {!webcamActive ? (
                    <button type="button" className="btn-primary" onClick={startWebcam}>
                      Start Live Feed
                    </button>
                  ) : (
                    <>
                      <button type="button" className="btn-secondary" onClick={stopWebcam}>
                        Stop Feed
                      </button>
                      <button type="button" className="btn-success" onClick={captureAndAnalyze} disabled={analyzing}>
                        {analyzing ? 'Analyzing...' : 'Capture Frame'}
                      </button>
                      <label className="toggle-label">
                        <input
                          type="checkbox"
                          checked={autoAnalyze}
                          onChange={(e) => setAutoAnalyze(e.target.checked)}
                        />
                        <span className="toggle-text">Auto-Analyze (every 3s)</span>
                      </label>
                    </>
                  )}
                </div>
              </div>

              {/* Method 2: Image upload */}
              <div className="method-box upload-box">
                <h3>Static Photo Upload</h3>
                <form onSubmit={handleFileUpload} className="file-upload-form">
                  <div className="file-dropzone">
                    <input 
                      type="file" 
                      id="postureImgInput" 
                      accept="image/*" 
                      onChange={(e) => setUploadFile(e.target.files[0])}
                    />
                    <label htmlFor="postureImgInput">
                      {uploadFile ? `Selected: ${uploadFile.name}` : 'Drag & drop an image or click to browse'}
                    </label>
                  </div>
                  <button type="submit" className="btn-primary" disabled={!uploadFile || analyzing}>
                    {analyzing ? 'Analyzing photo...' : 'Upload & Analyze'}
                  </button>
                </form>
              </div>
            </div>

            {/* Analysis Result Box */}
            {postureResult && (
              <div className={`analysis-result-card ${postureResult.posture_status}`}>
                <div className="result-badge-row">
                  <span className={`result-badge ${postureResult.posture_status}`}>
                    {postureResult.posture_status} POSTURE
                  </span>
                  <span className="result-time">
                    {new Date(postureResult.created_at).toLocaleTimeString()}
                  </span>
                </div>
                <div className="result-details">
                  <div className="result-img-wrapper">
                    <img 
                      src={postureResult.posture_image} 
                      alt="Analyzed Posture" 
                      onClick={() => setZoomImage(postureResult.posture_image)}
                    />
                  </div>
                  <div className="result-text">
                    {postureResult.posture_status === 'BAD' ? (
                      <>
                        <p className="warning-text">⚠️ Diagnostic Alert!</p>
                        <p>Our AI model identified symptoms associated with: <strong>{postureResult.disease_risk}</strong></p>
                        <p>Confidence index: <strong>{postureResult.disease_probability.toFixed(1)}%</strong></p>
                      </>
                    ) : (
                      <>
                        <p className="success-text">✅ Neutral Alignment Verified</p>
                        <p>No major spinal stress points or ergonomics issues detected. Keep up the good work!</p>
                      </>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Chatbot Panel */}
          <div className="dashboard-card chatbot-panel">
            <div className="panel-header">
              <h2>🤖 LifeCare Virtual Assistant</h2>
              <span className="engine-badge">{chatModelInfo}</span>
            </div>
            
            <div className="chat-log">
              {chatHistory.map((msg, index) => (
                <div key={index} className={`chat-bubble-wrapper ${msg.role}`}>
                  <div className={`chat-bubble ${msg.role}`}>
                    <div className="chat-bubble-header">
                      {msg.role === 'assistant' ? 'LifeCare Health Bot' : 'You'}
                    </div>
                    <div className="chat-bubble-body">
                      {msg.content.split('\n').map((line, lIdx) => (
                        <p key={lIdx}>{line}</p>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
              {chatLoading && (
                <div className="chat-bubble-wrapper assistant">
                  <div className="chat-bubble assistant loading">
                    <span className="chat-dot"></span>
                    <span className="chat-dot"></span>
                    <span className="chat-dot"></span>
                  </div>
                </div>
              )}
              <div ref={chatBottomRef} />
            </div>

            <form onSubmit={handleChatSubmit} className="chat-input-row">
              <input
                type="text"
                value={chatMessage}
                onChange={(e) => setChatMessage(e.target.value)}
                placeholder="Ask about neck pain, lumbar exercises, desk setup..."
                disabled={chatLoading}
              />
              <button type="submit" disabled={!chatMessage.trim() || chatLoading}>
                Send
              </button>
            </form>
          </div>
          
        </div>
      ) : (
        /* Analytics Tab content */
        <div className="analytics-view">
          {stats ? (
            <>
              {/* Stats Widgets */}
              <div className="stats-widgets-grid">
                <div className="stat-widget">
                  <span className="widget-icon">📋</span>
                  <div className="widget-info">
                    <h4>Total Posture Checks</h4>
                    <p className="widget-value">{stats.total_checks}</p>
                  </div>
                </div>

                <div className="stat-widget">
                  <span className="widget-icon">⚡</span>
                  <div className="widget-info">
                    <h4>Posture Health Score</h4>
                    <p className="widget-value highlight-value">{stats.health_score}%</p>
                    <span className="widget-sub">Ratio of GOOD posture detections</span>
                  </div>
                </div>

                <div className="stat-widget">
                  <span className="widget-icon">✅</span>
                  <div className="widget-info">
                    <h4>Healthy Frames</h4>
                    <p className="widget-value">{stats.good_checks}</p>
                  </div>
                </div>

                <div className="stat-widget">
                  <span className="widget-icon">❌</span>
                  <div className="widget-info">
                    <h4>Poor Alignment Frames</h4>
                    <p className="widget-value">{stats.bad_checks}</p>
                  </div>
                </div>
              </div>

              {/* Feedback Charts Grid */}
              <div className="charts-grid">
                {/* Chart 1: Donut Chart (GOOD vs BAD) */}
                <div className="chart-card">
                  <h3>Posture Quality Distribution</h3>
                  <div className="svg-chart-container">
                    {stats.total_checks > 0 ? (
                      <svg width="240" height="240" viewBox="0 0 42 42" className="donut-svg">
                        <circle cx="21" cy="21" r="15.915" fill="transparent" stroke="var(--border)" strokeWidth="4.2" />
                        <circle 
                          cx="21" 
                          cy="21" 
                          r="15.915" 
                          fill="transparent" 
                          stroke="#10b981" 
                          strokeWidth="4.2" 
                          strokeDasharray={`${stats.health_score} ${100 - stats.health_score}`}
                          strokeDashoffset="25" 
                          className="donut-segment"
                        />
                        <text x="21" y="21" className="donut-center-text" textAnchor="middle" dominantBaseline="middle">
                          {stats.health_score}%
                        </text>
                        <text x="21" y="27" className="donut-center-sub" textAnchor="middle">
                          Healthy
                        </text>
                      </svg>
                    ) : (
                      <div className="chart-empty-message">No posture checks logged yet.</div>
                    )}
                    <div className="chart-legend">
                      <div className="legend-item"><span className="legend-dot green"></span> Good Posture ({stats.good_checks})</div>
                      <div className="legend-item"><span className="legend-dot red"></span> Bad Posture ({stats.bad_checks})</div>
                    </div>
                  </div>
                </div>

                {/* Chart 2: Bar Chart (Diseases counts) */}
                <div className="chart-card">
                  <h3>Spinal Risk Area Distribution</h3>
                  <div className="bar-chart-container">
                    {stats.bad_checks > 0 ? (
                      <div className="bar-chart">
                        {Object.entries(stats.disease_counts).map(([disease, count]) => {
                          const maxCount = Math.max(...Object.values(stats.disease_counts), 1);
                          const percentage = (count / maxCount) * 100;
                          return (
                            <div className="bar-row" key={disease}>
                              <div className="bar-label">{disease}</div>
                              <div className="bar-rail">
                                <div 
                                  className="bar-fill" 
                                  style={{ width: `${percentage}%` }}
                                >
                                  <span className="bar-value">{count}</span>
                                </div>
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    ) : (
                      <div className="chart-empty-message">No clinical warnings detected. Good alignment!</div>
                    )}
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="loading-stats">Loading dashboard statistics...</div>
          )}

          {/* User History Logs Table */}
          <div className="dashboard-card history-table-card">
            <h3>Posture Analysis History Log</h3>
            {loadingHistory ? (
              <p>Fetching logs...</p>
            ) : history.length > 0 ? (
              <div className="user-table-wrapper">
                <table className="user-table">
                  <thead>
                    <tr>
                      <th>Thumbnail</th>
                      <th>Posture Status</th>
                      <th>Identified Risk</th>
                      <th>Risk Probability</th>
                      <th>Date / Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((record) => (
                      <tr key={record.id}>
                        <td>
                          <div className="history-thumbnail-wrapper">
                            <img 
                              src={record.posture_image} 
                              alt="Check thumbnail" 
                              onClick={() => setZoomImage(record.posture_image)}
                            />
                          </div>
                        </td>
                        <td>
                          <span className={`status-badge ${record.posture_status}`}>
                            {record.posture_status}
                          </span>
                        </td>
                        <td>
                          <span className="disease-risk-text">
                            {record.disease_risk === 'None' ? '✓ None (Healthy)' : record.disease_risk}
                          </span>
                        </td>
                        <td>
                          {record.posture_status === 'BAD' ? `${record.disease_probability.toFixed(1)}%` : '--'}
                        </td>
                        <td>
                          {new Date(record.created_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="chart-empty-message">No posture analysis logs found. Go to the AI Interaction tab to perform your first check!</div>
            )}
          </div>
        </div>
      )}

      {/* Image Modal Lightbox Zoom */}
      {zoomImage && (
        <div className="modal-overlay" onClick={() => setZoomImage(null)}>
          <div className="modal-content lightbox" onClick={(e) => e.stopPropagation()}>
            <img src={zoomImage} className="lightbox-img" alt="Zoomed Posture" />
            <button type="button" className="lightbox-close" onClick={() => setZoomImage(null)}>✕</button>
          </div>
        </div>
      )}

      {user.role === 'admin' && (
        <AdminUserPanel token={token} />
      )}
    </div>
  )
}
