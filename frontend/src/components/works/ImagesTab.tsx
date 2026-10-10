"use client";

// Proof-of-work photos. Image files need the login token, so they are
// downloaded with the API client and shown from a local object URL.

import { ImageOff, Upload } from "lucide-react";
import { useEffect, useState } from "react";
import { Can } from "@/components/Can";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Form";
import { Modal } from "@/components/ui/Modal";
import { EmptyState, ErrorState, Loading } from "@/components/ui/States";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { notify } from "@/lib/notify";
import type { Work, WorkImage } from "@/lib/types";
import { useApi } from "@/lib/useApi";

/** Photos uploaded for a work, with an upload button. */
export function ImagesTab({ work }: { work: Work }) {
  const [uploading, setUploading] = useState(false);
  const [viewing, setViewing] = useState<WorkImage | null>(null);
  const { data: images, error, loading, reload } = useApi<WorkImage[]>(`/works/${work.id}/images`);

  return (
    <Card
      title="Proof of work"
      description="Photos of the finished work."
      actions={
        <Can permission="works.upload_images">
          <Button size="sm" onClick={() => setUploading(true)}>
            <Upload className="size-4" aria-hidden />
            Upload photo
          </Button>
        </Can>
      }
    >
      {loading && <Loading />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {images && images.length === 0 && <EmptyState title="No photos yet" />}
      {images && images.length > 0 && (
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {images.map((image) => (
            <li key={image.id}>
              <button
                type="button"
                onClick={() => setViewing(image)}
                className="block w-full overflow-hidden rounded-lg border border-zinc-200 text-left hover:border-emerald-500"
              >
                <AuthImage image={image} className="aspect-square w-full object-cover" />
                <span className="block truncate px-2 py-1.5 text-xs text-zinc-600">
                  {image.description || formatDateTime(image.created_at)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      <Modal open={uploading} onClose={() => setUploading(false)} title="Upload photo">
        <UploadForm
          workId={work.id}
          onCancel={() => setUploading(false)}
          onDone={() => {
            setUploading(false);
            reload();
          }}
        />
      </Modal>
      <Modal open={viewing !== null} onClose={() => setViewing(null)} title={viewing?.description || "Photo"} wide>
        {viewing && (
          <>
            <AuthImage image={viewing} className="max-h-[70vh] w-full rounded-lg object-contain" />
            <p className="mt-2 text-xs text-zinc-500">Uploaded {formatDateTime(viewing.created_at)}</p>
          </>
        )}
      </Modal>
    </Card>
  );
}

/** Loads one image with the login token and shows it. */
function AuthImage({ image, className }: { image: WorkImage; className: string }) {
  const [source, setSource] = useState<{ id: string; url: string | null } | null>(null);

  useEffect(() => {
    let active = true;
    let url: string | null = null;
    api
      .blob(`/works/${image.work_id}/images/${image.id}/file`)
      .then((blob) => {
        url = URL.createObjectURL(blob);
        if (active) {
          setSource({ id: image.id, url });
        } else {
          URL.revokeObjectURL(url);
        }
      })
      .catch(() => active && setSource({ id: image.id, url: null }));
    // Free the memory used by the image when it is no longer shown.
    return () => {
      active = false;
      if (url) {
        URL.revokeObjectURL(url);
      }
    };
  }, [image.id, image.work_id]);

  if (!source || source.id !== image.id) {
    return <div className={`${className} animate-pulse bg-zinc-100`} />;
  }
  if (!source.url) {
    return (
      <div className={`${className} flex items-center justify-center bg-zinc-100 text-zinc-400`}>
        <ImageOff className="size-6" aria-label="Image could not be loaded" />
      </div>
    );
  }
  // A blob: URL from the API, so next/image cannot optimise it.
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={source.url} alt={image.description || "Proof of work photo"} className={className} />;
}

interface UploadFormProps {
  workId: string;
  onCancel: () => void;
  onDone: () => void;
}

/** Form to upload one photo with an optional description. */
function UploadForm({ workId, onCancel, onDone }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);

  /** Upload the photo (POST /works/{id}/images). */
  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!file) {
      return;
    }
    const form = new FormData();
    form.append("file", file);
    form.append("description", description);
    setBusy(true);
    const saved = await notify(api.upload<WorkImage>(`/works/${workId}/images`, form), "Photo uploaded");
    setBusy(false);
    if (saved) {
      onDone();
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input
        label="Photo"
        type="file"
        required
        accept="image/jpeg,image/png,image/webp"
        hint="JPEG, PNG or WEBP, up to 5 MB."
        onChange={(event) => setFile(event.target.files?.[0] || null)}
        className="file:mr-3 file:rounded-md file:border-0 file:bg-zinc-100 file:px-3 file:py-1 file:text-sm"
      />
      <Input
        label="Description"
        maxLength={255}
        hint="Optional, e.g. which part of the work it shows."
        value={description}
        onChange={(event) => setDescription(event.target.value)}
      />
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={busy} disabled={!file}>
          Upload
        </Button>
      </div>
    </form>
  );
}
