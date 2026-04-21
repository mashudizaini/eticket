# CKDO SSO Implementation Guide (Updated)
## Integrasi E-Ticket ke Keycloak SSO — dari Standalone Login ke Auto-Login

**Current State:**
- Dashboard: `dashboard-dev.ckd-otto.com` → login via Keycloak + Google social login ✅
- E-Ticket: login standalone (username/password sendiri) → HARUS diganti ke Keycloak SSO
- Keycloak: sudah running, realm & client Dashboard sudah ada ✅
- Stack: FastAPI + React + PostgreSQL + keycloak-js

**Target:**
User klik "E-Ticket" di App Launcher → langsung masuk tanpa login lagi

---

## OVERVIEW: Apa Yang Berubah di E-Ticket

```
SEBELUM (Current):
┌──────────┐     ┌──────────────────┐     ┌──────────────┐
│  User    │────▶│ E-Ticket Login   │────▶│ E-Ticket DB  │
│          │     │ (form sendiri)   │     │ (users table)│
└──────────┘     └──────────────────┘     └──────────────┘

SESUDAH (Target):
┌──────────┐     ┌──────────────────┐     ┌──────────────┐
│  User    │────▶│ Keycloak         │────▶│ E-Ticket App │
│ (sudah   │     │ (cek session,    │     │ (terima JWT, │
│  login   │     │  sudah ada →     │     │  no login    │
│  di      │     │  langsung token) │     │  form)       │
│ Dashboard)     └──────────────────┘     └──────────────┘
└──────────┘
```

**Yang berubah:**
- ❌ Hapus/bypass login form E-Ticket
- ❌ Tidak lagi cek credentials ke E-Ticket DB users table
- ✅ Tambah keycloak-js di React E-Ticket
- ✅ Backend E-Ticket validasi JWT dari Keycloak (bukan session/cookie sendiri)
- ✅ User mapping: Keycloak user ID → E-Ticket user data

---

## PHASE 1: KEYCLOAK — Tambah Client E-Ticket
*Estimasi: 15 menit*

### Step 1.1 — Login Keycloak Admin Console

Buka Keycloak Admin Console, login sebagai admin, pilih realm yang sama
dengan Dashboard (misalnya `ckdo` atau `ckd-otto`).

> **Cek dulu:** Buka Clients → lihat client Dashboard yang sudah ada.
> Catat realm name dan Keycloak URL-nya — E-Ticket harus pakai yang SAMA persis.

### Step 1.2 — Create Client: ckdo-eticket

**Clients → Create Client:**

| Setting                  | Value                                    |
|--------------------------|------------------------------------------|
| Client ID                | `ckdo-eticket`                           |
| Client Protocol          | `openid-connect`                         |
| Root URL                 | URL E-Ticket app (misal `http://172.21.x.x:3001` atau subdomain) |

**Tab Settings:**

| Setting                  | Value                                    |
|--------------------------|------------------------------------------|
| Client Authentication    | `Off` (public client untuk SPA)          |
| Standard Flow            | `ON`                                     |
| Direct Access Grants     | `OFF`                                    |
| Implicit Flow            | `OFF`                                    |
| Valid Redirect URIs      | `http://172.21.x.x:3001/*` dan/atau `https://eticket-dev.ckd-otto.com/*` |
| Valid Post Logout Redirect URIs | `+` (same as redirect URIs)       |
| Web Origins              | `http://172.21.x.x:3001` dan/atau `https://eticket-dev.ckd-otto.com` |

Klik **Save**.

### Step 1.3 — Buat Client Roles

Di client `ckdo-eticket` → tab **Roles** → Create Role:

| Role Name       | Description                                    |
|-----------------|------------------------------------------------|
| `ticket-admin`  | Full access: manage tickets, categories, users |
| `ticket-agent`  | Handle & resolve assigned tickets              |
| `ticket-user`   | Create & view own tickets only                 |

### Step 1.4 — Assign Roles ke Users

**Users** → pilih user (misal Mashudi Zaini) → **Role Mapping** →
Filter by client `ckdo-eticket` → Assign `ticket-admin`.

Lakukan untuk semua user yang perlu akses E-Ticket.

### Step 1.5 — Pastikan Roles Masuk ke JWT Token

Secara default Keycloak sudah include `resource_access` di token.
Untuk verifikasi:

1. Buka **Clients → ckdo-eticket → Client Scopes** tab
2. Klik `ckdo-eticket-dedicated`
3. Pastikan ada mapper **client roles** — kalau belum ada:
   - **Add Mapper → By Configuration → User Client Role**
   - Name: `client-roles`
   - Client ID: `ckdo-eticket`
   - Token Claim Name: `resource_access.ckdo-eticket.roles`
   - Add to ID token: ON
   - Add to access token: ON

### Step 1.6 — Test Token (Optional tapi Recommended)

Gunakan Keycloak Admin Console → **Clients → ckdo-eticket → Client Scopes →
Evaluate** → pilih user → **Generated Access Token**.

Cek output JSON, pastikan ada:
```json
{
  "resource_access": {
    "ckdo-eticket": {
      "roles": ["ticket-admin"]
    }
  },
  "preferred_username": "mashudi.zaini",
  "email": "mashudi@ckd-otto.com",
  "name": "Mashudi Zaini"
}
```

---

## PHASE 2: E-TICKET REACT — Ganti Login ke Keycloak SSO
*Estimasi: 1-2 jam*

### Step 2.1 — Install keycloak-js

```bash
cd ckdo-eticket/frontend
npm install keycloak-js
```

### Step 2.2 — Buat Keycloak Config

Buat file baru: `src/keycloak.js`

```javascript
import Keycloak from 'keycloak-js';

const keycloak = new Keycloak({
  // ============================================================
  // PENTING: url dan realm HARUS SAMA PERSIS dengan Dashboard
  // Copy dari keycloak.js Dashboard kamu, hanya clientId yang beda
  // ============================================================
  url: 'https://YOUR_KEYCLOAK_URL',   // <-- copy dari Dashboard keycloak.js
  realm: 'YOUR_REALM_NAME',           // <-- copy dari Dashboard keycloak.js
  clientId: 'ckdo-eticket',           // <-- INI YANG BEDA (client baru)
});

export default keycloak;
```

> **KUNCI SSO:** `url` dan `realm` HARUS identik dengan Dashboard.
> Kalau beda satu karakter pun, SSO session tidak akan terdeteksi.

### Step 2.3 — Buat Auth Provider

Buat file baru: `src/context/AuthContext.jsx`

```jsx
import React, {
  createContext, useContext, useState, useEffect, useCallback
} from 'react';
import keycloak from '../keycloak';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [authenticated, setAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    keycloak
      .init({
        // =====================================================
        // 'check-sso' = KUNCI auto-login dari Dashboard
        //
        // Flow:
        // 1. keycloak-js buat hidden iframe ke Keycloak server
        // 2. iframe cek: apakah ada session cookie Keycloak?
        // 3. Session ADA (user sudah login di Dashboard)
        //    → Keycloak return authorization code
        //    → keycloak-js exchange code → dapat token
        //    → User langsung masuk E-Ticket, TANPA lihat login page
        // 4. Session TIDAK ADA
        //    → keycloak.login() dipanggil → redirect ke Keycloak login
        // =====================================================
        onLoad: 'check-sso',
        pkceMethod: 'S256',
        checkLoginIframe: true,
        silentCheckSsoRedirectUri:
          window.location.origin + '/silent-check-sso.html',
      })
      .then((auth) => {
        if (auth) {
          // ✅ SSO session ditemukan — user auto-login!
          console.log('[E-Ticket] SSO auto-login successful');
          handleAuthenticated();
        } else {
          // ❌ Belum ada session — redirect ke Keycloak login
          console.log('[E-Ticket] No SSO session, redirecting to login...');
          keycloak.login();
        }
      })
      .catch((err) => {
        console.error('[E-Ticket] Keycloak init error:', err);
        setLoading(false);
      });

    // Auto-refresh token sebelum expire
    keycloak.onTokenExpired = () => {
      keycloak
        .updateToken(30)
        .then((refreshed) => {
          if (refreshed) {
            console.log('[E-Ticket] Token refreshed');
          }
        })
        .catch(() => {
          console.warn('[E-Ticket] Token refresh failed, re-login');
          keycloak.login();
        });
    };
  }, []);

  const handleAuthenticated = () => {
    const profile = keycloak.tokenParsed;

    setUser({
      id: profile.sub,
      username: profile.preferred_username,
      email: profile.email,
      name: profile.name || profile.preferred_username,
      firstName: profile.given_name,
      lastName: profile.family_name,
    });

    // Extract roles khusus client ckdo-eticket
    const clientRoles =
      profile.resource_access?.['ckdo-eticket']?.roles || [];
    setRoles(clientRoles);

    setAuthenticated(true);
    setLoading(false);
  };

  const logout = useCallback(() => {
    keycloak.logout({ redirectUri: window.location.origin });
  }, []);

  const hasRole = useCallback(
    (role) => roles.includes(role),
    [roles]
  );

  // Get fresh token untuk API calls
  const getToken = useCallback(async () => {
    try {
      await keycloak.updateToken(5);
      return keycloak.token;
    } catch {
      keycloak.login();
      return null;
    }
  }, []);

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        gap: '1rem',
      }}>
        <div style={{
          width: 40, height: 40,
          border: '4px solid #e5e7eb',
          borderTopColor: '#2563eb',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite',
        }} />
        <span style={{ color: '#6b7280' }}>
          Checking authentication...
        </span>
        <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{
      authenticated, user, roles, logout, hasRole, getToken, keycloak,
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
```

### Step 2.4 — Silent Check SSO Page

Buat file: `public/silent-check-sso.html`

```html
<!DOCTYPE html>
<html>
<body>
  <script>
    parent.postMessage(location.href, location.origin);
  </script>
</body>
</html>
```

### Step 2.5 — Modifikasi App.jsx — Wrap dengan AuthProvider

**SEBELUM** (contoh tipikal existing e-ticket):
```jsx
function App() {
  return (
    <BrowserRouter>
      <LoginPage />  {/* atau auth check sendiri */}
      <Routes>
        <Route path="/tickets" element={<TicketList />} />
        ...
      </Routes>
    </BrowserRouter>
  );
}
```

**SESUDAH:**
```jsx
import { AuthProvider } from './context/AuthContext';

function App() {
  return (
    <AuthProvider>
      {/* AuthProvider handles ALL authentication.
          If user has SSO session → auto-login.
          If not → redirect to Keycloak login.
          Login form E-Ticket tidak diperlukan lagi. */}
      <BrowserRouter>
        <Navbar />
        <Routes>
          <Route path="/" element={<TicketList />} />
          <Route path="/create" element={<TicketCreate />} />
          <Route path="/ticket/:id" element={<TicketDetail />} />
          {/* ... existing routes, tanpa LoginPage */}
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
```

### Step 2.6 — Update Navbar: User Info & Logout

Ganti user info display yang sebelumnya dari local auth:

```jsx
import { useAuth } from '../context/AuthContext';

const Navbar = () => {
  const { user, roles, logout } = useAuth();

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <span>🎫 CKDO E-Ticket System</span>
      </div>

      <div className="navbar-user">
        <span className="user-name">{user?.name}</span>
        <span className="user-role">
          {roles.includes('ticket-admin') ? 'Admin' :
           roles.includes('ticket-agent') ? 'Agent' : 'User'}
        </span>
        <button onClick={logout} className="btn-logout">
          Sign Out
        </button>
      </div>
    </nav>
  );
};
```

### Step 2.7 — Update API Calls: Pakai Keycloak Token

**SEBELUM** (contoh tipikal existing):
```javascript
// Mungkin pakai session cookie atau token dari login form sendiri
const response = await fetch('/api/tickets', {
  headers: { 'Authorization': `Bearer ${localToken}` }
});
```

**SESUDAH** — Buat API helper baru: `src/services/api.js`
```javascript
import keycloak from '../keycloak';

const API_BASE = import.meta.env.VITE_API_URL || 'http://172.21.x.x:8001/api/v1';

/**
 * Authenticated fetch — otomatis attach Keycloak JWT token.
 * Token di-refresh otomatis kalau hampir expire.
 */
async function authFetch(endpoint, options = {}) {
  // Pastikan token masih valid (refresh kalau expire dalam 5 detik)
  try {
    await keycloak.updateToken(5);
  } catch {
    keycloak.login();
    return null;
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${keycloak.token}`,  // <-- Keycloak JWT
      ...options.headers,
    },
  });

  if (res.status === 401) {
    // Token rejected oleh backend — force re-login
    keycloak.login();
    return null;
  }

  return res;
}

// ---- Ticket API ----

export const ticketApi = {
  list:        ()           => authFetch('/tickets').then(r => r?.json()),
  get:         (id)         => authFetch(`/tickets/${id}`).then(r => r?.json()),
  create:      (data)       => authFetch('/tickets', {
                                 method: 'POST',
                                 body: JSON.stringify(data),
                               }).then(r => r?.json()),
  update:      (id, data)   => authFetch(`/tickets/${id}`, {
                                 method: 'PUT',
                                 body: JSON.stringify(data),
                               }).then(r => r?.json()),
  close:       (id)         => authFetch(`/tickets/${id}/close`, {
                                 method: 'POST',
                               }).then(r => r?.json()),
  categories:  ()           => authFetch('/categories').then(r => r?.json()),
};
```

### Step 2.8 — Role-Based UI (Optional)

Contoh menampilkan menu berdasarkan role:

```jsx
import { useAuth } from '../context/AuthContext';

const Sidebar = () => {
  const { hasRole } = useAuth();

  return (
    <aside>
      <nav>
        <a href="/">My Tickets</a>
        <a href="/create">New Ticket</a>

        {/* Hanya agent & admin yang lihat menu ini */}
        {(hasRole('ticket-agent') || hasRole('ticket-admin')) && (
          <a href="/manage">Manage Tickets</a>
        )}

        {/* Hanya admin */}
        {hasRole('ticket-admin') && (
          <>
            <a href="/categories">Categories</a>
            <a href="/reports">Reports</a>
          </>
        )}
      </nav>
    </aside>
  );
};
```

---

## PHASE 3: E-TICKET FASTAPI BACKEND — JWT Validation
*Estimasi: 1 jam*

### Step 3.1 — Install Dependencies

```bash
cd ckdo-eticket/backend
pip install python-jose[cryptography] httpx
```

### Step 3.2 — Keycloak Auth Module

Buat file: `app/auth/keycloak.py`

```python
"""
Keycloak JWT verification for E-Ticket backend.

Menggantikan local auth (username/password check ke DB)
dengan validasi JWT token dari Keycloak.
"""

import httpx
from jose import jwt, JWTError
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from functools import lru_cache
from pydantic import BaseModel
from typing import List, Optional

# ============================================================
# CONFIGURATION — sesuaikan dengan Keycloak kamu
# ============================================================
KEYCLOAK_URL   = "https://YOUR_KEYCLOAK_URL"   # sama dengan Dashboard
REALM          = "YOUR_REALM_NAME"              # sama dengan Dashboard
CLIENT_ID      = "ckdo-eticket"                 # client ID yang baru dibuat

ISSUER         = f"{KEYCLOAK_URL}/realms/{REALM}"
CERTS_URL      = f"{ISSUER}/protocol/openid-connect/certs"

security = HTTPBearer()


# ============================================================
# User model dari JWT
# ============================================================
class KeycloakUser(BaseModel):
    id: str                           # sub (unique Keycloak user ID)
    username: str                     # preferred_username
    email: Optional[str] = None
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    roles: List[str] = []             # client roles dari ckdo-eticket


# ============================================================
# Fetch & cache Keycloak public keys
# ============================================================
_jwks_cache = None

def get_jwks():
    global _jwks_cache
    if _jwks_cache is None:
        try:
            resp = httpx.get(CERTS_URL, timeout=10)
            resp.raise_for_status()
            _jwks_cache = resp.json()
        except Exception as e:
            raise HTTPException(503, f"Cannot fetch Keycloak keys: {e}")
    return _jwks_cache

def clear_jwks_cache():
    global _jwks_cache
    _jwks_cache = None


# ============================================================
# Token verification dependency
# ============================================================
async def get_current_user(
    cred: HTTPAuthorizationCredentials = Depends(security),
) -> KeycloakUser:
    """
    FastAPI dependency — verifikasi JWT token dari Keycloak.

    Gunakan:
        @router.get("/tickets")
        async def list_tickets(user: KeycloakUser = Depends(get_current_user)):
            ...
    """
    token = cred.credentials

    try:
        jwks = get_jwks()
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience="account",
            issuer=ISSUER,
            options={"verify_exp": True, "verify_iss": True, "verify_aud": True},
        )
    except JWTError:
        # Mungkin key rotation — clear cache & retry sekali
        clear_jwks_cache()
        try:
            jwks = get_jwks()
            payload = jwt.decode(
                token, jwks, algorithms=["RS256"],
                audience="account", issuer=ISSUER,
            )
        except JWTError as e:
            raise HTTPException(401, f"Invalid token: {e}",
                                headers={"WWW-Authenticate": "Bearer"})

    # Extract client roles
    client_roles = (
        payload.get("resource_access", {})
        .get(CLIENT_ID, {})
        .get("roles", [])
    )

    return KeycloakUser(
        id=payload["sub"],
        username=payload.get("preferred_username", ""),
        email=payload.get("email"),
        name=payload.get("name"),
        first_name=payload.get("given_name"),
        last_name=payload.get("family_name"),
        roles=client_roles,
    )


# ============================================================
# Role check helpers
# ============================================================
def require_role(role: str):
    """Dependency: user HARUS punya role tertentu."""
    async def checker(user: KeycloakUser = Depends(get_current_user)):
        if role not in user.roles:
            raise HTTPException(403, f"Role '{role}' required")
        return user
    return checker

def require_any_role(*roles: str):
    """Dependency: user HARUS punya salah satu dari roles."""
    async def checker(user: KeycloakUser = Depends(get_current_user)):
        if not any(r in user.roles for r in roles):
            raise HTTPException(403, f"One of {list(roles)} required")
        return user
    return checker
```

### Step 3.3 — User Mapping Strategy

Ini bagian krusial: E-Ticket sudah punya `users` table sendiri.
Kamu perlu memetakan Keycloak user ke E-Ticket user.

**Opsi A: Auto-sync on first login (RECOMMENDED)**

```python
# app/services/user_sync.py

from sqlalchemy.orm import Session
from app.auth.keycloak import KeycloakUser
from app.models.user import User  # existing E-Ticket User model

async def get_or_create_eticket_user(
    keycloak_user: KeycloakUser,
    db: Session,
) -> User:
    """
    Map Keycloak user ke E-Ticket user.
    Kalau belum ada, auto-create.
    Kalau sudah ada, update info dari Keycloak.
    """
    # Cari user berdasarkan keycloak ID
    user = db.query(User).filter(
        User.keycloak_id == keycloak_user.id
    ).first()

    if user is None:
        # Coba match berdasarkan email (untuk migrasi user lama)
        user = db.query(User).filter(
            User.email == keycloak_user.email
        ).first()

        if user:
            # User lama ditemukan — link ke Keycloak
            user.keycloak_id = keycloak_user.id
        else:
            # User baru — auto-create
            user = User(
                keycloak_id=keycloak_user.id,
                username=keycloak_user.username,
                email=keycloak_user.email,
                full_name=keycloak_user.name,
                role=_map_keycloak_role(keycloak_user.roles),
            )
            db.add(user)

    # Update info dari Keycloak (single source of truth)
    user.full_name = keycloak_user.name
    user.email = keycloak_user.email

    db.commit()
    db.refresh(user)
    return user


def _map_keycloak_role(kc_roles: list) -> str:
    """Map Keycloak roles ke E-Ticket role field."""
    if 'ticket-admin' in kc_roles:
        return 'admin'
    if 'ticket-agent' in kc_roles:
        return 'agent'
    return 'user'
```

**Tambahkan kolom `keycloak_id` ke users table:**

```sql
-- Migration SQL
ALTER TABLE users
ADD COLUMN keycloak_id VARCHAR(255) UNIQUE;

-- Index untuk fast lookup
CREATE INDEX idx_users_keycloak_id ON users(keycloak_id);
```

### Step 3.4 — Update Routes: Ganti Auth

**SEBELUM** (contoh existing):
```python
@router.get("/tickets")
async def list_tickets(current_user = Depends(get_local_user)):  # local auth
    ...
```

**SESUDAH:**
```python
from app.auth.keycloak import get_current_user, KeycloakUser, require_role
from app.services.user_sync import get_or_create_eticket_user

@router.get("/tickets")
async def list_tickets(
    kc_user: KeycloakUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Map Keycloak user ke E-Ticket user (auto-create if needed)
    user = await get_or_create_eticket_user(kc_user, db)

    if 'ticket-admin' in kc_user.roles or 'ticket-agent' in kc_user.roles:
        tickets = db.query(Ticket).all()
    else:
        tickets = db.query(Ticket).filter(Ticket.created_by == user.id).all()

    return tickets


@router.post("/tickets")
async def create_ticket(
    data: TicketCreate,
    kc_user: KeycloakUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = await get_or_create_eticket_user(kc_user, db)
    ticket = Ticket(**data.dict(), created_by=user.id)
    db.add(ticket)
    db.commit()
    return ticket


# Admin-only endpoint
@router.delete("/tickets/{ticket_id}")
async def delete_ticket(
    ticket_id: int,
    kc_user: KeycloakUser = Depends(require_role("ticket-admin")),
    db: Session = Depends(get_db),
):
    ...
```

### Step 3.5 — CORS Configuration

```python
# app/main.py

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://172.21.x.x:3001",           # E-Ticket frontend (IP)
        "https://eticket-dev.ckd-otto.com",  # E-Ticket frontend (domain)
        "https://dashboard-dev.ckd-otto.com",# Dashboard (if cross-calling)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## PHASE 4: DASHBOARD — Update App Launcher Link
*Estimasi: 5 menit*

Pastikan tombol E-Ticket di App Launcher mengarah ke URL E-Ticket:

```javascript
// Di config aplikasi di Dashboard
{
  id: 'eticket',
  name: 'E-Ticket System',
  description: 'Helpdesk & ticketing',
  url: 'https://eticket-dev.ckd-otto.com',  // atau IP internal
  ssoStatus: 'SSO ACTIVE',
  // TIDAK PERLU passing token, session cookie yang handle
}
```

Ketika user klik → browser buka URL E-Ticket → React init keycloak-js
dengan `check-sso` → Keycloak cek session → session ADA (dari Dashboard)
→ langsung dapat token → user masuk E-Ticket tanpa login.

---

## PHASE 5: TESTING CHECKLIST
*Estimasi: 30 menit*

### Test Flow SSO

```
✅ Test 1: Login Fresh
   1. Buka browser baru (incognito)
   2. Buka dashboard-dev.ckd-otto.com
   3. Login via Google social login
   4. Pastikan masuk Dashboard
   Expected: redirect ke Keycloak, login via Google, masuk Dashboard

✅ Test 2: Auto-Login E-Ticket (INI YANG UTAMA)
   1. Dari Dashboard (sudah login), klik "E-Ticket System"
   2. E-Ticket terbuka
   Expected: LANGSUNG masuk E-Ticket, TANPA halaman login
   Note: mungkin ada flash "Checking authentication..." <1 detik

✅ Test 3: Direct Access E-Ticket (tanpa Dashboard)
   1. Buka tab baru
   2. Ketik langsung URL E-Ticket
   Expected: karena Keycloak session masih ada, tetap auto-login

✅ Test 4: User Info Consistency
   1. Cek nama & email di Dashboard
   2. Cek nama & email di E-Ticket
   Expected: SAMA (dari Keycloak yang sama)

✅ Test 5: Role-Based Access
   1. Login sebagai user dengan role ticket-admin
   2. Pastikan menu admin terlihat
   3. Login sebagai user dengan role ticket-user
   4. Pastikan menu admin TIDAK terlihat
   Expected: roles dari Keycloak mengontrol akses

✅ Test 6: Token Refresh
   1. Buka E-Ticket, tunggu 5+ menit
   2. Lakukan aksi (misal buat ticket baru)
   Expected: masih bisa aksi, token auto-refresh

✅ Test 7: Logout
   1. Klik Sign Out di E-Ticket
   2. Buka kembali Dashboard
   Expected: Dashboard juga minta login ulang (Keycloak session ended)

✅ Test 8: Cross-Logout
   1. Login ke Dashboard + buka E-Ticket
   2. Logout dari Dashboard
   3. Refresh E-Ticket
   Expected: E-Ticket minta login ulang
```

### Debug: Kalau SSO Tidak Auto-Login

```
Problem: E-Ticket tetap muncul login page Keycloak

Check 1: Realm name SAMA?
  → Dashboard: keycloak.js → realm: '???'
  → E-Ticket:  keycloak.js → realm: '???'
  → HARUS identik

Check 2: Keycloak URL SAMA?
  → Dashboard: keycloak.js → url: '???'
  → E-Ticket:  keycloak.js → url: '???'
  → HARUS identik (termasuk http/https dan port)

Check 3: Session cookie ada?
  → DevTools → Application → Cookies
  → Cari domain Keycloak
  → Harus ada KEYCLOAK_SESSION, KEYCLOAK_IDENTITY

Check 4: silent-check-sso.html ada?
  → Buka browser: http://eticket-url/silent-check-sso.html
  → Harus load (blank page, no 404)

Check 5: Console errors?
  → DevTools → Console
  → Cari error dari keycloak-js
  → Biasanya: CORS, redirect URI mismatch, atau iframe blocked
```

---

## RINGKASAN PERUBAHAN

| Component           | Perubahan                                         |
|----------------------|--------------------------------------------------|
| **Keycloak**         | Tambah client `ckdo-eticket` + roles             |
| **E-Ticket React**   | Tambah keycloak-js, AuthProvider, hapus login form|
| **E-Ticket FastAPI** | Ganti local auth → JWT validation dari Keycloak  |
| **E-Ticket DB**      | Tambah kolom `keycloak_id` di users table        |
| **Dashboard**        | Minimal — pastikan link E-Ticket benar           |

## Urutan Pengerjaan

```
1. Keycloak: buat client + roles           [15 min]
2. E-Ticket React: integrasi keycloak-js   [1-2 hr]
3. E-Ticket FastAPI: JWT middleware        [1 hr]
4. E-Ticket DB: tambah keycloak_id         [10 min]
5. Testing SSO flow                        [30 min]
                                    Total: ~3-4 jam
```
