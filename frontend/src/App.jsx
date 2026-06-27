import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from './assets/vite.svg'
import heroImg from './assets/hero.png'
import Auth from './components/Auth'
import Dashboard from './components/Dashboard'
import './App.css'

function App() {
  const [token, setToken] = useState(() => localStorage.getItem('lifecare_token') || '')
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('lifecare_user')
    try {
      return saved ? JSON.parse(saved) : null
    } catch {
      return null
    }
  })
  const [showAuth, setShowAuth] = useState(false)

  const handleLoginSuccess = (authData) => {
    const { access_token, user: userData } = authData
    setToken(access_token)
    setUser(userData)
    localStorage.setItem('lifecare_token', access_token)
    localStorage.setItem('lifecare_user', JSON.stringify(userData))
    setShowAuth(false)
  }

  const handleLogout = () => {
    setToken('')
    setUser(null)
    localStorage.removeItem('lifecare_token')
    localStorage.removeItem('lifecare_user')
  }

  return (
    <>
      {/* Brand Header */}
      <header className="main-header">
        <div className="header-logo">
          <span className="logo-icon">♥</span>
          <span className="logo-text">LifeCare</span>
        </div>
        <div className="header-actions">
          {token ? (
            <div className="user-indicator">
              <span className="user-dot"></span>
              <span className="user-name">{user?.username}</span>
              <button type="button" className="btn-secondary" onClick={handleLogout}>
                Sign Out
              </button>
            </div>
          ) : (
            <button type="button" className="btn-primary" onClick={() => setShowAuth(true)}>
              Sign In
            </button>
          )}
        </div>
      </header>

      {/* Main Content Area */}
      <main className="main-content">
        {token ? (
          <Dashboard user={user} token={token} onLogout={handleLogout} />
        ) : (
          <div className="landing-view">
            <section id="center">
              <div className="hero">
                <img src={heroImg} className="base" width="170" height="179" alt="" />
                <img src={reactLogo} className="framework" alt="React logo" />
                <img src={viteLogo} className="vite" alt="Vite logo" />
              </div>
              <div className="welcome-text">
                <h1>LifeCare Health Portal</h1>
                <p className="hero-desc">
                  An advanced, AI-driven assistant for skin classification, posture check, and medical queries.
                </p>
                <div className="cta-row">
                  <button
                    type="button"
                    className="cta-btn primary-cta"
                    onClick={() => setShowAuth(true)}
                  >
                    Get Started Now
                  </button>
                </div>
              </div>
            </section>

            <div className="ticks"></div>

            <section id="next-steps">
              <div id="docs">
                <svg className="icon" role="presentation" aria-hidden="true">
                  <use href="/icons.svg#documentation-icon"></use>
                </svg>
                <h2>Documentation</h2>
                <p>Learn more about Vite, React, and FastAPI schemas.</p>
                <ul>
                  <li>
                    <a href="https://vite.dev/" target="_blank" rel="noreferrer">
                      <img className="logo" src={viteLogo} alt="" />
                      Vite Docs
                    </a>
                  </li>
                  <li>
                    <a href="https://react.dev/" target="_blank" rel="noreferrer">
                      <img className="button-icon" src={reactLogo} alt="" />
                      React Docs
                    </a>
                  </li>
                </ul>
              </div>
              <div id="social">
                <svg className="icon" role="presentation" aria-hidden="true">
                  <use href="/icons.svg#social-icon"></use>
                </svg>
                <h2>Connect with us</h2>
                <p>Visit repository sources and documentation.</p>
                <ul>
                  <li>
                    <a href="https://github.com" target="_blank" rel="noreferrer">
                      <svg className="button-icon" role="presentation" aria-hidden="true">
                        <use href="/icons.svg#github-icon"></use>
                      </svg>
                      GitHub
                    </a>
                  </li>
                </ul>
              </div>
            </section>
          </div>
        )}
      </main>

      {/* Auth Modal Overlay */}
      {showAuth && (
        <div className="modal-overlay" onClick={() => setShowAuth(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <Auth onLoginSuccess={handleLoginSuccess} onCancel={() => setShowAuth(false)} />
          </div>
        </div>
      )}

      <div className="ticks"></div>
      <footer className="main-footer">
        <p>&copy; {new Date().getFullYear()} LifeCare. All rights reserved.</p>
      </footer>
    </>
  )
}

export default App

