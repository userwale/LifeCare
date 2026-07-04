import { useState, useRef, useEffect } from 'react'

const API_BASE_URL = '/api/v1/auth'

export default function Auth({ onLoginSuccess, onCancel }) {
  // Views: 'login' | 'register' | 'login_otp' | 'register_otp' | 'forgot_password' | 'reset_password'
  const [view, setView] = useState('login')
  
  // Form states
  const [usernameOrEmail, setUsernameOrEmail] = useState('')
  const [password, setPassword] = useState('')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [newPassword, setNewPassword] = useState('')
  
  // OTP states
  const [otpDigits, setOtpDigits] = useState(['', '', '', '', '', ''])
  const otpInputsRef = useRef([])

  // Feedback states
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  // Clear feedback on view change
  useEffect(() => {
    setError('')
    setSuccess('')
    setOtpDigits(['', '', '', '', '', ''])
  }, [view])

  // Shift focus for OTP inputs
  const handleOtpChange = (index, value) => {
    // Only allow numbers
    if (value && !/^\d+$/.test(value)) return

    const newDigits = [...otpDigits]
    newDigits[index] = value.slice(-1) // keep last typed character
    setOtpDigits(newDigits)

    // Auto-focus next input
    if (value && index < 5) {
      otpInputsRef.current[index + 1]?.focus()
    }
  }

  const handleOtpKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !otpDigits[index] && index > 0) {
      otpInputsRef.current[index - 1]?.focus()
    }
  }

  const getOtpCode = () => otpDigits.join('')

  // Handle errors safely
  const handleError = (err) => {
    console.error(err)
    if (err.response) {
      setError(err.response.detail || 'An error occurred. Please try again.')
    } else {
      setError(err.message || 'Connection error. Make sure the backend is running.')
    }
  }

  // API Call helper
  const apiCall = async (endpoint, data) => {
    setIsLoading(true)
    setError('')
    setSuccess('')
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      const result = await response.json()
      if (!response.ok) {
        throw new Error(result.detail || 'Something went wrong')
      }
      return result
    } catch (err) {
      throw err;
    } finally {
      setIsLoading(false)
    }
  }

  // 1. Submit Username/Password for Login
  const handleLoginSubmit = async (e) => {
    e.preventDefault()
    if (!usernameOrEmail || !password) {
      setError('Please enter all credentials.')
      return
    }
    try {
      const res = await apiCall('/login', {
        username_or_email: usernameOrEmail,
        password: password,
      })
      if (res.status === 'otp_sent') {
        // Capture email associated with user (could be email or username typed)
        setEmail(res.email)
        setSuccess('Password verified! A 2FA code has been sent to your email.')
        setView('login_otp')
      } else if (res.access_token) {
        setSuccess('Logged in successfully!')
        onLoginSuccess(res)
      }
    } catch (err) {
      handleError(err)
    }
  }


  // 2. Verify Login OTP
  const handleVerifyLoginSubmit = async (e) => {
    e.preventDefault()
    const code = getOtpCode()
    if (code.length < 6) {
      setError('Please enter all 6 digits.')
      return
    }
    try {
      const res = await apiCall('/verify-login', {
        email: email,
        code: code,
      })
      setSuccess('Logged in successfully!')
      // Pass token and user details to parent App
      onLoginSuccess(res)
    } catch (err) {
      handleError(err)
    }
  }

  // 3. Register Account
  const handleRegisterSubmit = async (e) => {
    e.preventDefault()
    if (!username || !email || !password) {
      setError('Please fill in all fields.')
      return
    }
    try {
      await apiCall('/register', {
        username,
        email,
        password,
      })
      setSuccess('Account created! Please verify your email with the OTP code.')
      setView('register_otp')
    } catch (err) {
      handleError(err)
    }
  }

  // 4. Verify Registration OTP
  const handleVerifyRegisterSubmit = async (e) => {
    e.preventDefault()
    const code = getOtpCode()
    if (code.length < 6) {
      setError('Please enter the 6-digit code.')
      return
    }
    try {
      const res = await apiCall('/verify-registration', {
        email: email,
        code: code,
      })
      setSuccess('Email verified and logged in!')
      onLoginSuccess(res)
    } catch (err) {
      handleError(err)
    }
  }

  // 5. Request Password Reset OTP
  const handleForgotPasswordSubmit = async (e) => {
    e.preventDefault()
    if (!email) {
      setError('Please enter your email.')
      return
    }
    try {
      await apiCall('/forgot-password', { email })
      setSuccess('If the email exists, a password reset code has been sent.')
      setView('reset_password')
    } catch (err) {
      handleError(err)
    }
  }

  // 6. Reset Password with OTP
  const handleResetPasswordSubmit = async (e) => {
    e.preventDefault()
    const code = getOtpCode()
    if (code.length < 6 || !newPassword) {
      setError('Please enter the 6-digit code and a new password.')
      return
    }
    try {
      await apiCall('/reset-password', {
        email: email,
        code: code,
        new_password: newPassword,
      })
      setSuccess('Password reset successful! You can now log in.')
      setView('login')
    } catch (err) {
      handleError(err)
    }
  }

  // Resend OTP
  const handleResendOtp = async (purpose) => {
    try {
      await apiCall('/resend-otp', {
        email: email,
        purpose: purpose,
      })
      setSuccess('A new OTP verification code has been sent!')
      setOtpDigits(['', '', '', '', '', ''])
      otpInputsRef.current[0]?.focus()
    } catch (err) {
      handleError(err)
    }
  }

  return (
    <div className="auth-card-container">
      <div className="auth-card">
        {/* Close Button / Cancel */}
        {onCancel && (
          <button type="button" className="auth-close-btn" onClick={onCancel} aria-label="Close auth">
            &times;
          </button>
        )}

        <div className="auth-header">
          <div className="auth-logo-symbol">♥</div>
          <h2>LifeCare</h2>
          <p className="auth-subtitle">
            {view === 'login' && 'Sign in to access your health portal'}
            {view === 'login_otp' && 'Enter 2-Factor authentication code'}
            {view === 'register' && 'Create your LifeCare account'}
            {view === 'register_otp' && 'Verify your registration email'}
            {view === 'forgot_password' && 'Reset your password'}
            {view === 'reset_password' && 'Define your new password'}
          </p>
        </div>

        {/* Global Success / Error Messages */}
        {error && <div className="auth-alert auth-alert-error">{error}</div>}
        {success && <div className="auth-alert auth-alert-success">{success}</div>}

        {/* 1. Login View */}
        {view === 'login' && (
          <form onSubmit={handleLoginSubmit} className="auth-form">
            <div className="auth-form-group">
              <label htmlFor="usernameOrEmail">Username or Email</label>
              <input
                id="usernameOrEmail"
                type="text"
                value={usernameOrEmail}
                onChange={(e) => setUsernameOrEmail(e.target.value)}
                placeholder="e.g. john_doe"
                required
                disabled={isLoading}
              />
            </div>

            <div className="auth-form-group">
              <div className="auth-label-row">
                <label htmlFor="password">Password</label>
                <button
                  type="button"
                  className="auth-link-btn"
                  onClick={() => setView('forgot_password')}
                  tabIndex="-1"
                >
                  Forgot Password?
                </button>
              </div>
              <div className="auth-password-wrapper">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  disabled={isLoading}
                />
                <button
                  type="button"
                  className="auth-password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? '👁️' : '👁️‍🗨️'}
                </button>
              </div>
            </div>

            <button type="submit" className="auth-submit-btn" disabled={isLoading}>
              {isLoading ? 'Verifying...' : 'Sign In'}
            </button>

            <div className="auth-footer-prompt">
              Don't have an account?{' '}
              <button type="button" className="auth-link-btn font-semibold" onClick={() => setView('register')}>
                Sign Up
              </button>
            </div>
          </form>
        )}

        {/* 2. Login OTP View */}
        {view === 'login_otp' && (
          <form onSubmit={handleVerifyLoginSubmit} className="auth-form">
            <p className="auth-instructions">
              Please enter the 6-digit verification code sent to <strong>{email}</strong>.
            </p>
            
            <div className="auth-otp-row">
              {otpDigits.map((digit, idx) => (
                <input
                  key={idx}
                  ref={(el) => (otpInputsRef.current[idx] = el)}
                  type="text"
                  maxLength="1"
                  pattern="[0-9]"
                  value={digit}
                  onChange={(e) => handleOtpChange(idx, e.target.value)}
                  onKeyDown={(e) => handleOtpKeyDown(idx, e)}
                  disabled={isLoading}
                  required
                  aria-label={`OTP Digit ${idx + 1}`}
                />
              ))}
            </div>

            <button type="submit" className="auth-submit-btn" disabled={isLoading}>
              {isLoading ? 'Verifying...' : 'Verify & Login'}
            </button>

            <div className="auth-footer-prompt">
              Didn't receive the code?{' '}
              <button
                type="button"
                className="auth-link-btn font-semibold"
                onClick={() => handleResendOtp('login')}
                disabled={isLoading}
              >
                Resend OTP
              </button>
            </div>

            <button
              type="button"
              className="auth-back-btn"
              onClick={() => setView('login')}
              disabled={isLoading}
            >
              Back to Login
            </button>
          </form>
        )}

        {/* 3. Register View */}
        {view === 'register' && (
          <form onSubmit={handleRegisterSubmit} className="auth-form">
            <div className="auth-form-group">
              <label htmlFor="regUsername">Username</label>
              <input
                id="regUsername"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="john_doe"
                required
                disabled={isLoading}
              />
            </div>

            <div className="auth-form-group">
              <label htmlFor="regEmail">Email Address</label>
              <input
                id="regEmail"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="john@example.com"
                required
                disabled={isLoading}
              />
            </div>

            <div className="auth-form-group">
              <label htmlFor="regPassword">Password</label>
              <div className="auth-password-wrapper">
                <input
                  id="regPassword"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 8 chars, 1 number, 1 uppercase"
                  required
                  disabled={isLoading}
                />
                <button
                  type="button"
                  className="auth-password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? '👁️' : '👁️‍🗨️'}
                </button>
              </div>
            </div>

            <button type="submit" className="auth-submit-btn" disabled={isLoading}>
              {isLoading ? 'Creating account...' : 'Create Account'}
            </button>

            <div className="auth-footer-prompt">
              Already have an account?{' '}
              <button type="button" className="auth-link-btn font-semibold" onClick={() => setView('login')}>
                Sign In
              </button>
            </div>
          </form>
        )}

        {/* 4. Register OTP Verification View */}
        {view === 'register_otp' && (
          <form onSubmit={handleVerifyRegisterSubmit} className="auth-form">
            <p className="auth-instructions">
              Enter the 6-digit confirmation code sent to <strong>{email}</strong> to activate your account.
            </p>

            <div className="auth-otp-row">
              {otpDigits.map((digit, idx) => (
                <input
                  key={idx}
                  ref={(el) => (otpInputsRef.current[idx] = el)}
                  type="text"
                  maxLength="1"
                  pattern="[0-9]"
                  value={digit}
                  onChange={(e) => handleOtpChange(idx, e.target.value)}
                  onKeyDown={(e) => handleOtpKeyDown(idx, e)}
                  disabled={isLoading}
                  required
                  aria-label={`OTP Digit ${idx + 1}`}
                />
              ))}
            </div>

            <button type="submit" className="auth-submit-btn" disabled={isLoading}>
              {isLoading ? 'Verifying...' : 'Verify & Activate'}
            </button>

            <div className="auth-footer-prompt">
              Didn't receive the code?{' '}
              <button
                type="button"
                className="auth-link-btn font-semibold"
                onClick={() => handleResendOtp('registration')}
                disabled={isLoading}
              >
                Resend OTP
              </button>
            </div>

            <button
              type="button"
              className="auth-back-btn"
              onClick={() => setView('register')}
              disabled={isLoading}
            >
              Back to Registration
            </button>
          </form>
        )}

        {/* 5. Forgot Password View */}
        {view === 'forgot_password' && (
          <form onSubmit={handleForgotPasswordSubmit} className="auth-form">
            <p className="auth-instructions">
              Enter your email address and we'll send you an OTP to reset your password.
            </p>

            <div className="auth-form-group">
              <label htmlFor="resetEmail">Email Address</label>
              <input
                id="resetEmail"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="john@example.com"
                required
                disabled={isLoading}
              />
            </div>

            <button type="submit" className="auth-submit-btn" disabled={isLoading}>
              {isLoading ? 'Sending...' : 'Send Reset Code'}
            </button>

            <button
              type="button"
              className="auth-back-btn"
              onClick={() => setView('login')}
              disabled={isLoading}
            >
              Back to Login
            </button>
          </form>
        )}

        {/* 6. Reset Password View */}
        {view === 'reset_password' && (
          <form onSubmit={handleResetPasswordSubmit} className="auth-form">
            <p className="auth-instructions">
              Enter the 6-digit code sent to your email and choose your new password.
            </p>

            <div className="auth-otp-row">
              {otpDigits.map((digit, idx) => (
                <input
                  key={idx}
                  ref={(el) => (otpInputsRef.current[idx] = el)}
                  type="text"
                  maxLength="1"
                  pattern="[0-9]"
                  value={digit}
                  onChange={(e) => handleOtpChange(idx, e.target.value)}
                  onKeyDown={(e) => handleOtpKeyDown(idx, e)}
                  disabled={isLoading}
                  required
                  aria-label={`OTP Digit ${idx + 1}`}
                />
              ))}
            </div>

            <div className="auth-form-group">
              <label htmlFor="newPassword">New Password</label>
              <div className="auth-password-wrapper">
                <input
                  id="newPassword"
                  type={showPassword ? 'text' : 'password'}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="At least 8 chars, 1 number, 1 uppercase"
                  required
                  disabled={isLoading}
                />
                <button
                  type="button"
                  className="auth-password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? '👁️' : '👁️‍🗨️'}
                </button>
              </div>
            </div>

            <button type="submit" className="auth-submit-btn" disabled={isLoading}>
              {isLoading ? 'Resetting password...' : 'Reset Password'}
            </button>

            <button
              type="button"
              className="auth-back-btn"
              onClick={() => setView('login')}
              disabled={isLoading}
            >
              Back to Login
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
