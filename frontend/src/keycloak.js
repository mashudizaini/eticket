// Keycloak JS adapter dimuat via <script> tag di index.html (dari server Keycloak).
// window.Keycloak tersedia secara global saat runtime.
// PENTING: url dan realm HARUS SAMA dengan ckdo-dashboard-v2 agar SSO session sharing bekerja.
const keycloak = new window.Keycloak({
  url: 'http://dashboard-dev.ckd-otto.com/auth',
  realm: 'ckdo',
  clientId: 'ckdo-eticket',
});

export default keycloak;
