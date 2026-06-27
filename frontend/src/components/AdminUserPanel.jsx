import { useState, useEffect } from 'react'

const API_BASE_URL = 'http://localhost:8000/api/v1/users'

export default function AdminUserPanel({ token }) {
  const [users, setUsers] = useState([])
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('user')
  const [password, setPassword] = useState('')
  
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Fetch users on component mount
  const fetchUsers = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'application/json'
        }
      })
      if (!response.ok) {
        throw new Error('Failed to retrieve user directory.')
      }
      const data = await response.json()
      setUsers(data)
    } catch (err) {
      console.error(err)
      setError(err.message)
    }
  }

  useEffect(() => {
    fetchUsers()
  }, [token])

  const validatePassword = (pwd) => {
    if (pwd.length < 8) {
      return 'Password must be at least 8 characters long.'
    }
    if (!/[A-Z]/.test(pwd)) {
      return 'Password must contain at least one uppercase letter.'
    }
    if (!/\d/.test(pwd)) {
      return 'Password must contain at least one digit.'
    }
    return null
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    // Basic frontend checks
    if (username.trim().length < 3) {
      setError('Username must be at least 3 characters long.')
      return
    }

    const passwordError = validatePassword(password)
    if (passwordError) {
      setError(passwordError)
      return
    }

    setIsLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          username: username.trim(),
          email: email.trim(),
          password,
          role
        })
      })

      const data = await response.json()

      if (!response.ok) {
        // Detailed error messages from FastAPI
        if (response.status === 422 && data.detail) {
          if (Array.isArray(data.detail)) {
            throw new Error(data.detail.map(d => d.msg).join(', '))
          }
          throw new Error(data.detail)
        }
        throw new Error(data.detail || 'Could not create account.')
      }

      setSuccess(`Successfully created account for ${data.username}!`)
      setUsername('')
      setEmail('')
      setPassword('')
      setRole('user')
      
      // Refresh user list
      fetchUsers()
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="admin-panel-card">
      <div className="admin-panel-header">
        <h3>User Management Directory</h3>
        <p className="admin-subtitle">Add new authorized accounts and view the current roster.</p>
      </div>

      <div className="admin-panel-grid">
        {/* Creation Form */}
        <div className="admin-section create-user-section">
          <h4>Create New Account</h4>
          {error && <div className="auth-alert auth-alert-error">{error}</div>}
          {success && <div className="auth-alert auth-alert-success">{success}</div>}
          
          <form onSubmit={handleSubmit} className="admin-form">
            <div className="auth-form-group">
              <label htmlFor="adminRegUsername">Username</label>
              <input
                id="adminRegUsername"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. nurse_jane"
                required
                disabled={isLoading}
              />
            </div>

            <div className="auth-form-group">
              <label htmlFor="adminRegEmail">Email Address</label>
              <input
                id="adminRegEmail"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="e.g. jane@lifecare.local"
                required
                disabled={isLoading}
              />
            </div>

            <div className="auth-form-group">
              <label htmlFor="adminRegRole">Role Assignment</label>
              <select
                id="adminRegRole"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                disabled={isLoading}
                className="admin-select"
              >
                <option value="user">User (Standard Portal Access)</option>
                <option value="admin">Administrator (Full Directory Access)</option>
              </select>
            </div>

            <div className="auth-form-group">
              <label htmlFor="adminRegPassword">Password</label>
              <input
                id="adminRegPassword"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 8 chars, 1 uppercase, 1 digit"
                required
                disabled={isLoading}
              />
            </div>

            <button type="submit" className="auth-submit-btn admin-btn" disabled={isLoading}>
              {isLoading ? 'Creating account...' : 'Create Account'}
            </button>
          </form>
        </div>

        {/* Directory Listing */}
        <div className="admin-section directory-section">
          <h4>Active Users ({users.length})</h4>
          <div className="user-table-wrapper">
            <table className="user-table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Registered</th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.id}>
                    <td>
                      <span className="user-table-username">{u.username}</span>
                    </td>
                    <td>{u.email}</td>
                    <td>
                      <span className={`role-badge ${u.role}`}>{u.role}</span>
                    </td>
                    <td>{new Date(u.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
