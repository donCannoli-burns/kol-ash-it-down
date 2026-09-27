# Local API

Base: `http://127.0.0.1:61337`

All endpoints except `/api/health` require:

```text
X-Kol-Doc-Edit-Token: <contents of data/doc_edit/service.token>
```

Mutating document operations additionally require `confirm: true`.

Endpoints:

```text
GET  /api/health
GET  /api/status
GET  /api/events?limit=N
POST /api/read
POST /api/edit
POST /api/convert
POST /api/session-tail
POST /api/query
POST /api/status-artifact
```

The service binds to loopback only and refuses non-local relay browser origins through CORS.
