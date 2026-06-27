import { useState } from 'react'
import AdminUserPanel from './AdminUserPanel'

export default function Dashboard({ user, token, onLogout }) {
  const [showToken, setShowToken] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleCopyToken = () => {
    navigator.clipboard.writeText(token)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <div>
          <h1>Welcome back, <span className="highlight-text">{user.username}</span>!</h1>
          <p className="subtitle">LifeCare Health Portal Dashboard</p>
        </div>
        <button type="button" className="logout-btn" onClick={onLogout}>
          Sign Out
        </button>
      </div>

      <div className="dashboard-grid">
        {/* Profile Card */}
        <div className="dashboard-card profile-card">
          <h3>Your Profile</h3>
          <div className="profile-details">
            <div className="detail-item">
              <span className="label">Username:</span>
              <span className="value">{user.username}</span>
            </div>
            <div className="detail-item">
              <span className="label">Email:</span>
              <span className="value">{user.email}</span>
            </div>
            <div className="detail-item">
              <span className="label">Role:</span>
              <span className={`role-badge ${user.role}`}>
                {user.role}
              </span>
            </div>
            <div className="detail-item">
              <span className="label">Account Status:</span>
              <span className="status-badge verified">
                ✓ Verified
              </span>
            </div>
          </div>
        </div>

        {/* Security Credentials Card */}
        <div className="dashboard-card security-card">
          <h3>Active Session Credentials</h3>
          <p className="card-desc">Your JSON Web Token (JWT) is used to authorize API queries to the backend.</p>
          
          <div className="token-viewer">
            <div className="token-header">
              <span>Bearer Access Token</span>
              <button 
                type="button" 
                className="token-action-btn"
                onClick={() => setShowToken(!showToken)}
              >
                {showToken ? 'Hide' : 'Show'}
              </button>
            </div>
            <div className="token-body">
              <code className="token-code">
                {showToken ? token : `${token.slice(0, 20)}...${token.slice(-20)}`}
              </code>
            </div>
            <button 
              type="button" 
              className="copy-token-btn" 
              onClick={handleCopyToken}
            >
              {copied ? '✓ Copied!' : 'Copy Token'}
            </button>
          </div>
        </div>

        {/* Health Portal Features (Dynamic Demo Cards) */}
        <div className="dashboard-card features-card">
          <h3>LifeCare AI Diagnostic Tools</h3>
          <p className="card-desc">Select an AI assistant tool below to start analyzing health parameters.</p>
          <div className="features-list">
            <div className="feature-item">
              <div className="feature-icon">🔍</div>
              <div className="feature-info">
                <h4>AI Skin Disease Classifier</h4>
                <p>Upload a skin lesion photo to classify potential concerns using YOLOv8.</p>
              </div>
            </div>

            <div className="feature-item">
              <div className="feature-icon">🧍</div>
              <div className="feature-info">
                <h4>AI Posture Corrector</h4>
                <p>Run real-time posture analysis to diagnose alignment and ergonomics issues.</p>
              </div>
            </div>

            <div className="feature-item">
              <div className="feature-icon">🤖</div>
              <div className="feature-info">
                <h4>LifeCare Virtual Assistant</h4>
                <p>Chat with our conversational AI to understand symptoms and check diagnostics.</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {user.role === 'admin' && (
        <AdminUserPanel token={token} />
      )}
    </div>
  )
}
