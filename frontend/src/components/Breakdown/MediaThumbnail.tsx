import { useState } from 'react';
import { Image } from 'lucide-react';

interface MediaThumbnailProps {
  filePath: string;
  thumbnailPath: string | null;
  originalFilename: string;
}

export function MediaThumbnail({ filePath, thumbnailPath, originalFilename }: MediaThumbnailProps) {
  const [imgError, setImgError] = useState(false);
  const src = thumbnailPath || filePath;

  if (imgError || !src) {
    return (
      <div className="w-20 h-20 rounded-md border border-border/50 bg-muted flex items-center justify-center">
        <Image className="h-6 w-6 text-muted-foreground/40" />
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={originalFilename}
      onClick={() => window.open(filePath, '_blank')}
      onError={() => setImgError(true)}
      className="w-20 h-20 rounded-md border border-border/50 object-cover cursor-pointer hover:opacity-80 transition-opacity"
    />
  );
}
