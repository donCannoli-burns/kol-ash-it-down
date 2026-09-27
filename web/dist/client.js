export class KolDocEditClient {
  constructor(base = "http://127.0.0.1:61337", token = "") {
    this.base = base;
    this.token = token;
  }
  async request(path, method = "GET", body) {
    const response = await fetch(this.base + path, {
      method,
      headers: {"Content-Type": "application/json", "X-Kol-Doc-Edit-Token": this.token},
      body: body === undefined ? undefined : JSON.stringify(body)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(String(data.error || response.statusText));
    return data;
  }
  health() { return this.request("/api/health"); }
  status() { return this.request("/api/status"); }
  read(path) { return this.request("/api/read", "POST", {path}); }
  convert(source, target, confirm=false) { return this.request("/api/convert", "POST", {source,target,confirm}); }
  edit(path, mode, find, replace, content, expected_sha256="", confirm=false) {
    return this.request("/api/edit", "POST", {path,mode,find,replace,content,expected_sha256,confirm});
  }
  sessionTail(player="", lines=250, marker="") { return this.request("/api/session-tail", "POST", {player,lines,marker}); }
  query(sql, limit=500) { return this.request("/api/query", "POST", {sql,limit}); }
  events(limit=100) { return this.request(`/api/events?limit=${limit}`); }
}
