"use client";
import { useState, useCallback } from "react";
import { getUploadUrl, uploadToS3, processDocument } from "@/lib/api";
import { Upload, FileText, CheckCircle, XCircle, Loader2, ArrowLeft } from "lucide-react";
import Link from "next/link";

type UploadStatus = "idle" | "uploading" | "processing" | "done" | "error" | "duplicate";

interface FileState {
  file: File;
  status: UploadStatus;
  message: string;
  chunks?: number;
}

export default function UploadPage() {
  const [files, setFiles] = useState<FileState[]>([]);
  const [dragging, setDragging] = useState(false);
  const [docType, setDocType] = useState("document");
  const [department, setDepartment] = useState("general");

  const processFiles = async (newFiles: File[]) => {
    const entries: FileState[] = newFiles.map((f) => ({
      file: f,
      status: "idle",
      message: "Queued",
    }));
    setFiles((prev) => [...prev, ...entries]);

    for (let i = 0; i < entries.length; i++) {
      const entry = entries[i];
      const globalIndex = files.length + i;

      const update = (status: UploadStatus, message: string, chunks?: number) => {
        setFiles((prev) => {
          const updated = [...prev];
          updated[globalIndex] = { ...updated[globalIndex], status, message, chunks };
          return updated;
        });
      };

      try {
        // Step 1: Get presigned S3 URL
        update("uploading", "Getting upload URL...");
        const { upload_url, s3_key } = await getUploadUrl(entry.file.name, entry.file.type || "application/pdf");

        // Step 2: Upload to S3
        update("uploading", "Uploading to S3...");
        await uploadToS3(upload_url, entry.file);

        // Step 3: Process (extract → embed → index)
        update("processing", "Processing document...");
        const result = await processDocument({
          s3_key,
          filename: entry.file.name,
          doc_type: docType as any,
          department,
          clearance_level: "internal",
        });

        if (result.status === "indexed") {
          update("done", `Indexed ${result.chunks_indexed} chunks`, result.chunks_indexed);
        } else if (result.status === "skipped") {
          update("duplicate", result.message);
        } else {
          update("error", result.message || "Processing failed");
        }
      } catch (e: any) {
        update("error", e.message || "Upload failed");
      }
    }
  };

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const dropped = Array.from(e.dataTransfer.files).filter(
        (f) => f.type === "application/pdf" || f.name.endsWith(".docx") || f.name.endsWith(".txt")
      );
      if (dropped.length) processFiles(dropped);
    },
    [files, docType, department]
  );

  const statusIcon = (status: UploadStatus) => {
    if (status === "done") return <CheckCircle className="w-4 h-4 text-green-400" />;
    if (status === "error") return <XCircle className="w-4 h-4 text-red-400" />;
    if (status === "duplicate") return <CheckCircle className="w-4 h-4 text-yellow-400" />;
    if (status === "uploading" || status === "processing") return <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />;
    return <FileText className="w-4 h-4 text-gray-500" />;
  };

  return (
    <div className="min-h-screen p-6 max-w-2xl mx-auto">
      <div className="flex items-center gap-3 mb-8">
        <Link href="/" className="text-gray-400 hover:text-white transition">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <h1 className="text-xl font-semibold">Upload Documents</h1>
      </div>

      {/* Options */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Document Type</label>
          <select
            value={docType}
            onChange={(e) => setDocType(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 outline-none"
          >
            <option value="contract">Contract</option>
            <option value="policy">Policy</option>
            <option value="regulation">Regulation</option>
            <option value="case_law">Case Law</option>
            <option value="document">General Document</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">Department</label>
          <input
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
            placeholder="e.g. legal, hr, compliance"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 outline-none placeholder-gray-600"
          />
        </div>
      </div>

      {/* Drop Zone */}
      <div
        onDrop={onDrop}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onClick={() => document.getElementById("file-input")?.click()}
        className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition ${
          dragging ? "border-blue-500 bg-blue-500/5" : "border-gray-700 hover:border-gray-600"
        }`}
      >
        <Upload className={`w-10 h-10 mx-auto mb-3 ${dragging ? "text-blue-400" : "text-gray-600"}`} />
        <p className="text-gray-300 font-medium">Drop files here or click to browse</p>
        <p className="text-gray-600 text-sm mt-1">PDF, DOCX, TXT supported</p>
        <input
          id="file-input"
          type="file"
          multiple
          accept=".pdf,.docx,.txt"
          className="hidden"
          onChange={(e) => {
            const selected = Array.from(e.target.files || []);
            if (selected.length) processFiles(selected);
          }}
        />
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="mt-6 space-y-2">
          {files.map((f, i) => (
            <div key={i} className="flex items-center gap-3 bg-gray-800 rounded-xl px-4 py-3">
              {statusIcon(f.status)}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{f.file.name}</p>
                <p className={`text-xs mt-0.5 ${
                  f.status === "done" ? "text-green-400" :
                  f.status === "error" ? "text-red-400" :
                  f.status === "duplicate" ? "text-yellow-400" :
                  "text-gray-500"
                }`}>{f.message}</p>
              </div>
              {f.chunks && <span className="text-xs text-gray-500">{f.chunks} chunks</span>}
            </div>
          ))}
        </div>
      )}

      {files.some((f) => f.status === "done") && (
        <div className="mt-6 text-center">
          <Link
            href="/"
            className="inline-block px-6 py-2.5 bg-blue-600 hover:bg-blue-700 rounded-xl text-sm font-medium transition"
          >
            Start Chatting →
          </Link>
        </div>
      )}
    </div>
  );
}
