"use client";

type UploadedFileBadgeProps = {
  filename: string;
  onRemoveAction?: () => void;
};

export function UploadedFileBadge({ filename, onRemoveAction }: UploadedFileBadgeProps) {
  return (
    <div className="inline-flex max-w-full items-center gap-2 rounded-xl border border-white/15 bg-slate-800/70 px-3 py-1.5 text-xs text-slate-200">
      <svg
        aria-hidden="true"
        viewBox="0 0 24 24"
        className="h-4 w-4 shrink-0 text-slate-300"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M7 3h7l5 5v13H7z" />
        <path d="M14 3v5h5" />
      </svg>
      <span className="truncate" title={filename}>
        {filename}
      </span>
      {onRemoveAction && (
        <button
          type="button"
          onClick={onRemoveAction}
          className="rounded-md px-1 text-slate-400 transition hover:bg-slate-700/80 hover:text-white"
          aria-label="Remove uploaded file"
        >
          x
        </button>
      )}
    </div>
  );
}
