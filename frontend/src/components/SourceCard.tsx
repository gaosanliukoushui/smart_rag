import { type Source, type StreamSource } from '../api/client';

type SourceItem = Source | StreamSource;

interface Props {
  sources: SourceItem[];
}

const formatScore = (s?: number) => s != null ? (s * 100).toFixed(0) + '%' : null;

const getText = (src: SourceItem): string => {
  return 'chunk_text' in src ? src.chunk_text : src.text;
};

const getTitle = (src: SourceItem): string => {
  return 'document_title' in src ? src.document_title : '';
};

export default function SourceCard({ sources }: Props) {
  if (!sources.length) return null;

  return (
    <div className="mt-3">
      <p className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wide">
        引用来源 ({sources.length})
      </p>
      <div className="flex flex-col gap-2">
        {sources.map((src, i) => (
          <div
            key={i}
            className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-sm"
          >
            <div className="flex items-center justify-between gap-2 mb-1.5">
              <span className="font-medium text-gray-700 truncate flex-1 min-w-0">
                {getTitle(src) || `来源 ${i + 1}`}
              </span>
              {formatScore(src.score) && (
                <span className="flex-shrink-0 text-xs text-gray-400 bg-white px-1.5 py-0.5 rounded border border-gray-200">
                  相似度 {formatScore(src.score)}
                </span>
              )}
            </div>
            <p className="text-gray-600 text-xs leading-relaxed line-clamp-3">
              {getText(src)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
