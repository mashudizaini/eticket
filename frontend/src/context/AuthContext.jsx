import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import keycloak from '../keycloak'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [authenticated, setAuthenticated] = useState(false)
  const [user, setUser] = useState(null)
  const [roles, setRoles] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    keycloak
      .init({
        // login-required: jika belum ada session → redirect ke Keycloak login
        // Jika sudah ada session Keycloak (dari Dashboard) → auto-login langsung
        onLoad: 'login-required',
        pkceMethod: 'S256',
      })
      .then((auth) => {
        if (auth) {
          _handleAuthenticated()
        } else {
          keycloak.login()
        }
      })
      .catch((err) => {
        console.error('[E-Ticket] Keycloak init error:', err)
        setLoading(false)
      })

    keycloak.onTokenExpired = () => {
      keycloak
        .updateToken(30)
        .catch(() => keycloak.login())
    }
  }, [])

  function _handleAuthenticated() {
    const profile = keycloak.tokenParsed
    setUser({
      id:        profile.sub,
      username:  profile.preferred_username,
      email:     profile.email,
      name:      profile.name || profile.preferred_username,
      firstName: profile.given_name,
      lastName:  profile.family_name,
    })
    const clientRoles = profile.resource_access?.['ckdo-eticket']?.roles || []
    setRoles(clientRoles)
    setAuthenticated(true)
    setLoading(false)
  }

  const logout = useCallback(() => {
    keycloak.logout({ redirectUri: window.location.origin })
  }, [])

  const hasRole = useCallback((role) => roles.includes(role), [roles])

  const getToken = useCallback(async () => {
    try {
      await keycloak.updateToken(5)
      return keycloak.token
    } catch {
      keycloak.login()
      return null
    }
  }, [])

  // Tampilkan spinner saat menunggu Keycloak init / SSO check
  if (loading) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        gap: '1rem',
        background: '#f9fafb',
      }}>
        <img src="/logo-header.png" alt="CKDO" style={{ height: 48, marginBottom: 8 }} />
        <div style={{
          width: 40,
          height: 40,
          border: '4px solid #e5e7eb',
          borderTopColor: '#2563eb',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite',
        }} />
        <span style={{ color: '#6b7280', fontSize: 14 }}>Checking authentication...</span>
        <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
      </div>
    )
  }

  return (
    <AuthContext.Provider value={{ authenticated, user, roles, logout, hasRole, getToken, keycloak }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
