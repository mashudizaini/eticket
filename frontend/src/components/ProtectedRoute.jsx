import { useAuth } from '../context/AuthContext'

// Loading dan redirect ke Keycloak sudah ditangani di AuthProvider.
// ProtectedRoute hanya perlu memastikan user sudah authenticated.
export default function ProtectedRoute({ children }) {
  const { authenticated } = useAuth()

  if (!authenticated) {
    // AuthProvider sudah memanggil keycloak.login() — render null sementara redirect
    return null
  }

  return children
}
