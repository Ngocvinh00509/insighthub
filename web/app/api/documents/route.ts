// InsightHub Web — list documents proxy cho client component
import { listDocuments } from "@/lib/api";
import { recordWebRequest } from "@/lib/metrics";

export async function GET() {
  const startedAt = performance.now();
  try {
    const docs = await listDocuments();
    recordWebRequest("/api/documents", 200, (performance.now() - startedAt) / 1000);
    return Response.json(docs);
  } catch {
    recordWebRequest("/api/documents", 502, (performance.now() - startedAt) / 1000);
    return Response.json([], { status: 502 });
  }
}
