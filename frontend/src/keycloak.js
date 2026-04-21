import Keycloak from 'keycloak-js';

// PENTING: url dan realm HARUS SAMA PERSIS dengan ckdo-dashboard-v2
// agar SSO session sharing berfungsi (auto-login tanpa login ulang)
const keycloak = new Keycloak({
  url: 'http://dashboard-dev.ckd-otto.com/auth',
  realm: 'ckdo',
  clientId: 'ckdo-eticket',
});

export default keycloak;
