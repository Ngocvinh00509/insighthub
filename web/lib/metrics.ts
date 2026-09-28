const buckets = [0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60];

type Store = {
  requests: Map<string, number>;
  durations: Map<string, number>;
};

const globalMetrics = globalThis as typeof globalThis & { insighthubWebMetrics?: Store };
const store = globalMetrics.insighthubWebMetrics ?? {
  requests: new Map<string, number>(),
  durations: new Map<string, number>(),
};
globalMetrics.insighthubWebMetrics = store;

function labels(route: string, status: number): string {
  return `route="${route}",status="${status}"`;
}

export function recordWebRequest(route: "/api/documents" | "/api/proxy", status: number, durationSeconds: number): void {
  const requestKey = labels(route, status);
  store.requests.set(requestKey, (store.requests.get(requestKey) ?? 0) + 1);
  for (const bucket of buckets) {
    if (durationSeconds <= bucket) {
      const key = `${requestKey},le="${bucket}"`;
      store.durations.set(key, (store.durations.get(key) ?? 0) + 1);
    }
  }
  const infinityKey = `${requestKey},le="+Inf"`;
  store.durations.set(infinityKey, (store.durations.get(infinityKey) ?? 0) + 1);
}

export function renderMetrics(): string {
  const lines = [
    "# HELP insighthub_web_http_requests_total Server-side web proxy requests by fixed route and status.",
    "# TYPE insighthub_web_http_requests_total counter",
  ];
  for (const [metricLabels, value] of store.requests) lines.push(`insighthub_web_http_requests_total{${metricLabels}} ${value}`);
  lines.push("# HELP insighthub_web_http_request_duration_seconds Server-side web proxy request duration.");
  lines.push("# TYPE insighthub_web_http_request_duration_seconds histogram");
  for (const [metricLabels, value] of store.durations) lines.push(`insighthub_web_http_request_duration_seconds_bucket{${metricLabels}} ${value}`);
  return `${lines.join("\n")}\n`;
}
