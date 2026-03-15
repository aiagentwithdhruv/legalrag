const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface IngestRequest {
  s3_key: string;
  filename: string;
  doc_type?: string;
  department?: string;
  clearance_level?: string;
}

export interface QueryRequest {
  query: string;
  session_id?: string;
  department?: string;
  use_smart_model?: boolean;
}

export async function getUploadUrl(filename: string, contentType: string) {
  const res = await fetch(`${API_URL}/ingest/upload-url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename, content_type: contentType }),
  });
  return res.json();
}

export async function uploadToS3(uploadUrl: string, file: File) {
  const res = await fetch(uploadUrl, {
    method: "PUT",
    body: file,
    headers: { "Content-Type": file.type },
  });
  if (!res.ok) throw new Error("S3 upload failed");
}

export async function processDocument(req: IngestRequest) {
  const res = await fetch(`${API_URL}/ingest/process`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  return res.json();
}

export function streamQuery(
  req: QueryRequest,
  onText: (text: string) => void,
  onSources: (sources: any[]) => void,
  onDone: () => void,
  onError: (err: string) => void
) {
  const controller = new AbortController();

  fetch(`${API_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    signal: controller.signal,
  }).then(async (res) => {
    const reader = res.body!.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const text = decoder.decode(value);
      const lines = text.split("\n");

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const data = line.slice(6).trim();
        if (data === "[DONE]") { onDone(); return; }
        try {
          const event = JSON.parse(data);
          if (event.type === "text") onText(event.content);
          else if (event.type === "sources") onSources(event.sources);
          else if (event.type === "error") onError(event.content);
        } catch {}
      }
    }
    onDone();
  }).catch((e) => {
    if (e.name !== "AbortError") onError(e.message);
  });

  return () => controller.abort();
}
