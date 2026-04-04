"use client";

import { useRef, useState } from "react";
import type { ChangeEvent } from "react";

type FileUploadProps = {
  uploadUrl: string;
  className?: string;
  disabled?: boolean;
  onUploadSuccessAction?: (filename: string) => void;
  onUploadErrorAction?: (message: string) => void;
};

const ACCEPTED_FILE_TYPES =
  ".pdf,.txt,.md,.docx,application/pdf,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

export function FileUpload({
  uploadUrl,
  className,
  disabled = false,
  onUploadSuccessAction,
  onUploadErrorAction,
}: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const isDisabled = disabled || isUploading;

  const openFilePicker = () => {
    if (!isDisabled) {
      inputRef.current?.click();
    }
  };

  const uploadFile = async (file: File) => {
    setIsUploading(true);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(uploadUrl, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Upload failed");
      }

      onUploadSuccessAction?.(file.name);
    } catch {
      onUploadErrorAction?.("Failed to upload document");
    } finally {
      setIsUploading(false);
      if (inputRef.current) {
        inputRef.current.value = "";
      }
    }
  };

  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    await uploadFile(file);
  };

  return (
    <div className={className}>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_FILE_TYPES}
        onChange={handleFileChange}
        className="hidden"
        disabled={isDisabled}
      />
      <button
        type="button"
        onClick={openFilePicker}
        disabled={isDisabled}
        aria-label="Upload document"
        className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/15 bg-slate-800/80 text-lg font-semibold text-slate-100 transition hover:border-white/30 hover:bg-slate-700/80 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isUploading ? (
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-transparent" />
        ) : (
          "+"
        )}
      </button>
    </div>
  );
}
