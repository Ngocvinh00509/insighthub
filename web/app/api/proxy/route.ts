import { API_URL } from "@/lib/api";
import { recordWebRequest } from "@/lib/metrics";

export async function POST(req: Request) {
  const startedAt = performance.now();
  const record = (status: number) => recordWebRequest("/api/proxy", status, (performance.now() - startedAt) / 1000);
  const target = new URL(req.url).searchParams.get("target");
  if (target !== "upload" && target !== "chat") {
    record(400);
    return Response.json({ detail: "Đích yêu cầu không hợp lệ." }, { status: 400 });
  }
  const maxBytes = target === "upload" ? 11 * 1024 * 1024 : 16000;
  if (Number(req.headers.get("content-length") || 0) > maxBytes) {
    record(413);
    return Response.json({ detail: "Yêu cầu vượt giới hạn kích thước." }, { status: 413 });
  }
  if (!req.body) {
    record(400);
    return Response.json({ detail: "Thiếu dữ liệu." }, { status: 400 });
  }
  let received = 0;
  const boundedBody = req.body.pipeThrough(new TransformStream({
    transform(chunk, controller) {
      received += chunk.byteLength;
      if (received > maxBytes) throw new Error("BODY_TOO_LARGE");
      controller.enqueue(chunk);
    },
  }));
  try {
    const options: RequestInit & { duplex: "half" } = {
      method: "POST", body: boundedBody, duplex: "half",
      headers: { "Content-Type": req.headers.get("content-type") || "application/json" },
      signal: AbortSignal.timeout(90000), cache: "no-store",
    };
    const res = await fetch(`${API_URL}/${target === "upload" ? "documents" : "chat"}`, options);
    record(res.status);
    return Response.json(await res.json(), { status: res.status });
  } catch {
    const status = received > maxBytes ? 413 : 502;
    record(status);
    return Response.json({ detail: received > maxBytes ? "Yêu cầu vượt giới hạn kích thước." : "API không sẵn sàng hoặc đã hết thời gian chờ." }, { status });
  }
}
