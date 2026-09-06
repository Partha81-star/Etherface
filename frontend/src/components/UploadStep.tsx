import { DragEvent, useEffect, useRef, useState } from "react";
import { ImagePlus, ScanFace, ShieldCheck, Upload } from "lucide-react";
import type { FaceBox } from "../api/client";

type Props = {
  file: File | null;
  faceBox: FaceBox | null;
  busy: boolean;
  error: string | null;
  onFile: (file: File) => void;
  onScan: () => void;
};

export function UploadStep({ file, faceBox, busy, error, onFile, onScan }: Props) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!file || !canvasRef.current) return;
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const context = canvas.getContext("2d");
      if (!context) return;
      const scale = Math.min(960 / image.naturalWidth, 600 / image.naturalHeight, 1);
      canvas.width = Math.round(image.naturalWidth * scale);
      canvas.height = Math.round(image.naturalHeight * scale);
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      if (faceBox) {
        const xScale = canvas.width / faceBox.image_width;
        const yScale = canvas.height / faceBox.image_height;
        context.strokeStyle = "#69f0c3";
        context.lineWidth = Math.max(3, canvas.width / 240);
        context.setLineDash([12, 7]);
        context.strokeRect(
          faceBox.left * xScale,
          faceBox.top * yScale,
          (faceBox.right - faceBox.left) * xScale,
          (faceBox.bottom - faceBox.top) * yScale,
        );
      }
      URL.revokeObjectURL(url);
    };
    image.src = url;
    return () => URL.revokeObjectURL(url);
  }, [file, faceBox]);

  function accept(next: File | undefined) {
    if (next && next.type.startsWith("image/")) onFile(next);
  }

  function drop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    accept(event.dataTransfer.files[0]);
  }

  if (file) {
    return (
      <section aria-labelledby="upload-heading" className="panel overflow-hidden">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Input evidence</p>
            <h2 id="upload-heading">Face sample</h2>
          </div>
          <button className="button-secondary" onClick={() => inputRef.current?.click()}>
            Replace
          </button>
        </div>
        <div className="relative grid min-h-[22rem] place-items-center overflow-hidden bg-black/30 p-4">
          <canvas ref={canvasRef} className="max-h-[34rem] max-w-full rounded-lg object-contain" />
          {busy && (
            <div className="absolute inset-0 grid place-items-center bg-ink/70 backdrop-blur-sm">
              <div className="text-center">
                <ScanFace className="mx-auto mb-3 animate-pulse text-mint" size={38} />
                <p className="font-medium text-white">Extracting local face signature…</p>
              </div>
            </div>
          )}
        </div>
        <div className="flex flex-col gap-4 border-t border-line p-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <p className="truncate font-medium text-slate-100">{file.name}</p>
            <p className="mt-1 text-sm text-muted">{(file.size / 1024 / 1024).toFixed(2)} MB · processed locally by your API</p>
          </div>
          <button className="button-primary shrink-0" disabled={busy} onClick={onScan}>
            <ScanFace aria-hidden="true" size={18} />
            {busy ? "Scanning…" : "Scan authorized set"}
          </button>
        </div>
        {error && <p className="error-message" role="alert">{error}</p>}
        <input ref={inputRef} className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => accept(event.target.files?.[0])} />
      </section>
    );
  }

  return (
    <section aria-labelledby="upload-heading" className="panel p-5 sm:p-7">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow">Input evidence</p>
          <h2 id="upload-heading">Upload a face sample</h2>
        </div>
        <ShieldCheck aria-hidden="true" className="text-mint" size={28} />
      </div>
      <div
        className={`group grid min-h-[20rem] cursor-pointer place-items-center rounded-xl border border-dashed p-8 text-center transition ${dragging ? "border-mint bg-mint/10" : "border-line bg-black/10 hover:border-mint/60 hover:bg-mint/[0.04]"}`}
        onClick={() => inputRef.current?.click()}
        onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={() => setDragging(false)}
        onDrop={drop}
        role="button"
        tabIndex={0}
        onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") inputRef.current?.click(); }}
      >
        <div>
          <span className="mx-auto mb-5 grid h-16 w-16 place-items-center rounded-full border border-line bg-panel text-mint transition group-hover:scale-105">
            <ImagePlus aria-hidden="true" size={28} />
          </span>
          <p className="text-lg font-semibold text-white">Drop a clear portrait here</p>
          <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-muted">JPEG, PNG, or WebP up to 10 MB. The scan is limited to your seeded, authorized images.</p>
          <span className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-mint">
            <Upload aria-hidden="true" size={16} /> Choose image
          </span>
        </div>
      </div>
      {error && <p className="error-message" role="alert">{error}</p>}
      <input ref={inputRef} className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => accept(event.target.files?.[0])} />
    </section>
  );
}
