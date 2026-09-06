import { DragEvent, useEffect, useRef, useState } from "react";
import { BadgeCheck, Camera, CameraOff, LoaderCircle, RefreshCw, Upload } from "lucide-react";
import { useCamera } from "../hooks/useCamera";

type Props = {
  value: File | null;
  onChange: (file: File | null) => void;
  disabled?: boolean;
  title?: string;
  description?: string;
};

export function FaceCapture({
  value,
  onChange,
  disabled = false,
  title = "Face scan",
  description = "Use a clear, front-facing image with one person in frame.",
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const camera = useCamera();

  useEffect(() => {
    if (!value) {
      setPreview(null);
      return;
    }
    const nextPreview = URL.createObjectURL(value);
    setPreview(nextPreview);
    return () => URL.revokeObjectURL(nextPreview);
  }, [value]);

  function accept(file: File | undefined) {
    if (!file) return;
    if (!file.type.startsWith("image/")) return;
    camera.stop();
    onChange(file);
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    accept(event.dataTransfer.files[0]);
  }

  async function takePhoto() {
    const file = await camera.capture();
    if (file) onChange(file);
  }

  if (preview && value) {
    return (
      <div className="capture-card capture-card-ready">
        <div className="capture-preview">
          <img src={preview} alt="Selected face preview" />
          <span className="scan-corner scan-corner-tl" />
          <span className="scan-corner scan-corner-tr" />
          <span className="scan-corner scan-corner-bl" />
          <span className="scan-corner scan-corner-br" />
          <span className="capture-ready-badge"><BadgeCheck size={15} /> Ready</span>
        </div>
        <div className="capture-footer">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-white">{value.name}</p>
            <p className="text-xs text-muted">{(value.size / 1024 / 1024).toFixed(2)} MB · not retained after processing</p>
          </div>
          <button type="button" className="button-secondary" disabled={disabled} onClick={() => onChange(null)}>
            <RefreshCw size={15} /> Retake
          </button>
        </div>
      </div>
    );
  }

  if (camera.status === "requesting" || camera.status === "ready") {
    return (
      <div className="capture-card">
        <div className="capture-preview capture-camera">
          <video ref={camera.videoRef} playsInline muted aria-label="Live camera preview" />
          <div className="face-guide" aria-hidden="true" />
          {camera.status === "requesting" && (
            <div className="capture-overlay">
              <LoaderCircle className="animate-spin text-mint" size={30} />
              <span>Waiting for camera…</span>
            </div>
          )}
        </div>
        <div className="capture-footer">
          <p className="text-sm text-muted">Center your face inside the guide and look directly at the camera.</p>
          <div className="flex shrink-0 gap-2">
            <button type="button" className="button-secondary" onClick={camera.stop}>Cancel</button>
            <button type="button" className="button-primary" disabled={camera.status !== "ready" || disabled} onClick={takePhoto}>
              <Camera size={17} /> Capture
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="capture-card">
      <div
        className={`capture-empty ${dragging ? "capture-empty-dragging" : ""}`}
        onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <span className="capture-icon"><Camera size={28} /></span>
        <div>
          <h3 className="text-lg font-semibold text-white">{title}</h3>
          <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted">{description}</p>
        </div>
        <div className="mt-5 flex flex-wrap justify-center gap-3">
          <button type="button" className="button-primary" disabled={disabled} onClick={camera.start}>
            <Camera size={17} /> Use camera
          </button>
          <button type="button" className="button-secondary" disabled={disabled} onClick={() => inputRef.current?.click()}>
            <Upload size={17} /> Upload photo
          </button>
        </div>
        <p className="mt-4 text-xs text-faint">JPEG, PNG, or WebP · maximum 10 MB</p>
      </div>
      {camera.error && (
        <div className="capture-warning" role="alert">
          <CameraOff size={17} /> <span>{camera.error}</span>
        </div>
      )}
      <input
        ref={inputRef}
        className="sr-only"
        type="file"
        accept="image/jpeg,image/png,image/webp"
        onChange={(event) => accept(event.target.files?.[0])}
      />
    </div>
  );
}
