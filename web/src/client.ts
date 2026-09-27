export type ApiResponse = Record<string, unknown>;

export class KolDocEditClient {
  constructor(
    readonly base = "http://127.0.0.1:61337",
    readonly token = ""
  ) {}

  private async request(path: string, method = "GET", body?: unknown): Promise<ApiResponse> {
    const response = await fetch(this.base + path, {
      method,
      headers: {
        "Content-Type": "application/json",
        "X-Kol-Doc-Edit-Token": this.token
      },
      body: body === undefined ? undefined : JSON.stringify(body)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(String(data.error || response.statusText));
    return data;
  }

  health() { return this.request("/api/health"); }
  status() { return this.request("/api/status"); }
  read(path: string) { return this.request("/api/read", "POST", {path}); }
  convert(source: string, target: string, confirm = false) {
    return this.request("/api/convert", "POST", {source, target, confirm});
  }
  edit(path: string, mode: string, find: string, replace: string, content: string,
       expected_sha256 = "", confirm = false) {
    return this.request("/api/edit", "POST", {path, mode, find, replace, content, expected_sha256, confirm});
  }
  sessionTail(player = "", lines = 250, marker = "") {
    return this.request("/api/session-tail", "POST", {player, lines, marker});
  }
  query(sql: string, limit = 500) {
    return this.request("/api/query", "POST", {sql, limit});
  }
  events(limit = 100) { return this.request(`/api/events?limit=${limit}`); }
}
