// Centralized API calls
const BASE = '';
export async function apiGet(path) { const r = await fetch(BASE + path); return r.json(); }
export async function apiPost(path, body) { const r = await fetch(BASE + path, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) }); return r.json(); }
export default { get: apiGet, post: apiPost };