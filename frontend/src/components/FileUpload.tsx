import { useState, useRef, useCallback } from 'react';

const ALLOWED_TYPES = ['.pdf', '.md', '.docx', '.txt'];
const MAX_SIZE = 50 * 1024 * 1024; // 50MB

interface Props {
  knowledgeBaseId: string;
  onUploaded: () => void;
}

export default function FileUpload({ knowledgeBaseId, onUploaded }: Props) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const upload = useCallback(
    async (file: File) => {
      const ext = '.' + file.name.split('.').pop()!.toLowerCase();
      if (!ALLOWED_TYPES.includes(ext)) {
        setError(`不支持的文件类型，仅支持：${ALLOWED_TYPES.join(' ')}`);
        return;
      }
      if (file.size > MAX_SIZE) {
        setError('文件大小不能超过 50MB');
        return;
      }

      setError('');
      setUploading(true);
      setProgress(0);

      try {
        const { documentApi } = await import('../api/client');
        await documentApi.upload(knowledgeBaseId, file, (p) => setProgress(p));
        setProgress(100);
        setTimeout(() => {
          setUploading(false);
          setProgress(0);
          onUploaded();
        }, 500);
      } catch {
        setError('上传失败，请重试');
        setUploading(false);
        setProgress(0);
      }
    },
    [knowledgeBaseId, onUploaded]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) upload(file);
    },
    [upload]
  );

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) upload(file);
    e.target.value = '';
  };

  return (
    <div className="w-full">
      <div
        className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all ${
          dragging
            ? 'border-primary-500 bg-primary-50'
            : 'border-gray-300 hover:border-primary-400 bg-gray-50 hover:bg-primary-50/30'
        } ${uploading ? 'pointer-events-none opacity-70' : 'cursor-pointer'}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => !uploading && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ALLOWED_TYPES.join(',')}
          className="hidden"
          onChange={handleFileChange}
        />
        {uploading ? (
          <div className="flex flex-col items-center gap-3">
            <svg className="animate-spin h-8 w-8 text-primary-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <div className="w-48 h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary-500 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-sm text-gray-500">上传中 {progress}%</p>
          </div>
        ) : (
          <>
            <div className="mx-auto w-12 h-12 bg-white rounded-full flex items-center justify-center mb-3 shadow-sm">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-6 w-6 text-primary-500"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
            </div>
            <p className="text-sm font-medium text-gray-700">
              拖拽文件到此处，或 <span className="text-primary-600">点击选择</span>
            </p>
            <p className="mt-1.5 text-xs text-gray-400">
              支持 {ALLOWED_TYPES.join(' ')}，最大 50MB
            </p>
          </>
        )}
      </div>
      {error && (
        <p className="mt-2 text-sm text-red-500 flex items-center gap-1">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {error}
        </p>
      )}
    </div>
  );
}
