import React, { useEffect, useRef, useState } from 'react';
import {
  Handle,
  Rect,
  cropBlob,
  fullRect,
  hitHandle,
  isFullRect,
  rectFromPoints,
  resizeRect,
} from './crop';
import { STROKE_PX, strokeWidthFor, toImagePoint } from './drawing';
import { Labels, Point } from './types';

type Props = {
  screenshot: Blob;
  labels: Labels;
  /** The cropped image, or null to keep the screenshot as it is. */
  onDone: (cropped: Blob | null) => void;
  onCancel: () => void;
};

type Drag = { handle: Handle | 'new'; origin: Point; start: Rect };

const HANDLE_PX = 12;
const HIT_PX = 14;

const CURSORS: Record<Handle, string> = {
  n: 'ns-resize',
  s: 'ns-resize',
  e: 'ew-resize',
  w: 'ew-resize',
  ne: 'nesw-resize',
  sw: 'nesw-resize',
  nw: 'nwse-resize',
  se: 'nwse-resize',
  move: 'move',
};

/** Size of one on-screen pixel, in screenshot pixels. */
const screenScale = (canvas: HTMLCanvasElement) => strokeWidthFor(canvas) / STROKE_PX;

function drawCrop(ctx: CanvasRenderingContext2D, rect: Rect, scale: number) {
  const { canvas } = ctx;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = 'rgba(0, 0, 0, 0.55)';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.clearRect(rect.x, rect.y, rect.width, rect.height);
  ctx.lineWidth = 2 * scale;
  ctx.strokeStyle = '#ffffff';
  ctx.strokeRect(rect.x, rect.y, rect.width, rect.height);

  const size = HANDLE_PX * scale;
  const xs = [rect.x, rect.x + rect.width / 2, rect.x + rect.width];
  const ys = [rect.y, rect.y + rect.height / 2, rect.y + rect.height];
  ctx.fillStyle = '#ffffff';
  ctx.strokeStyle = '#1b1b1b';
  ctx.lineWidth = scale;
  xs.forEach((x, column) => {
    ys.forEach((y, row) => {
      if (column === 1 && row === 1) return;
      ctx.fillRect(x - size / 2, y - size / 2, size, size);
      ctx.strokeRect(x - size / 2, y - size / 2, size, size);
    });
  });
}

/**
 * Lets the user keep only part of the screenshot before annotating it. The returned
 * image really contains only the chosen area; nothing else is kept.
 */
export function CropEditor({ screenshot, labels, onDone, onCancel }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const dragRef = useRef<Drag | null>(null);

  const [imageUrl, setImageUrl] = useState('');
  const [size, setSize] = useState({ width: 0, height: 0 });
  const [rect, setRect] = useState<Rect>(fullRect(0, 0));
  const [cursor, setCursor] = useState('crosshair');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const url = URL.createObjectURL(screenshot);
    setImageUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [screenshot]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx || size.width === 0) return;
    drawCrop(ctx, rect, screenScale(canvas));
  });

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onCancel();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onCancel]);

  const pointOf = (event: React.PointerEvent<HTMLCanvasElement>) =>
    toImagePoint(event.currentTarget, event.clientX, event.clientY);

  const onPointerDown = (event: React.PointerEvent<HTMLCanvasElement>) => {
    const canvas = event.currentTarget;
    event.preventDefault();
    const point = pointOf(event);
    const handle = hitHandle(rect, point, HIT_PX * screenScale(canvas));
    canvas.setPointerCapture(event.pointerId);
    dragRef.current = { handle: handle ?? 'new', origin: point, start: rect };
  };

  const onPointerMove = (event: React.PointerEvent<HTMLCanvasElement>) => {
    const canvas = event.currentTarget;
    const point = pointOf(event);
    const drag = dragRef.current;
    if (!drag) {
      const handle = hitHandle(rect, point, HIT_PX * screenScale(canvas));
      setCursor(handle ? CURSORS[handle] : 'crosshair');
      return;
    }
    if (drag.handle === 'new') {
      setRect(rectFromPoints(drag.origin, point, size.width, size.height));
    } else {
      setRect(
        resizeRect(
          drag.start,
          drag.handle,
          point.x - drag.origin.x,
          point.y - drag.origin.y,
          size.width,
          size.height,
        ),
      );
    }
  };

  const onPointerUp = () => {
    const drag = dragRef.current;
    dragRef.current = null;
    // A click or a tiny drag must not leave an unusable selection behind.
    if (drag && drag.handle === 'new' && (rect.width < 16 || rect.height < 16)) {
      setRect(drag.start);
    }
  };

  const apply = async () => {
    if (isFullRect(rect, size.width, size.height)) {
      onDone(null);
      return;
    }
    setBusy(true);
    try {
      onDone(await cropBlob(screenshot, rect));
    } catch {
      onDone(null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="snapnote-editor" role="dialog" aria-modal="true" aria-label={labels.crop}>
      <div className="snapnote-editor-toolbar">
        <span className="snapnote-crop-hint">{labels.cropHint}</span>
        <span className="snapnote-spacer" />
        <button
          type="button"
          className="snapnote-btn"
          disabled={isFullRect(rect, size.width, size.height)}
          onClick={() => setRect(fullRect(size.width, size.height))}
        >
          {labels.resetCrop}
        </button>
        <button type="button" className="snapnote-btn" onClick={onCancel}>
          {labels.cancel} (Esc)
        </button>
        <button type="button" className="snapnote-btn" onClick={() => onDone(null)}>
          {labels.skipCrop}
        </button>
        <button
          type="button"
          className="snapnote-btn snapnote-btn-primary"
          disabled={busy || size.width === 0}
          onClick={apply}
        >
          {labels.applyCrop}
        </button>
      </div>
      <div className="snapnote-editor-stage">
        {imageUrl && (
          <img
            className="snapnote-editor-image"
            src={imageUrl}
            alt=""
            draggable={false}
            onLoad={(event) => {
              const img = event.currentTarget;
              setSize({ width: img.naturalWidth, height: img.naturalHeight });
              setRect(fullRect(img.naturalWidth, img.naturalHeight));
            }}
          />
        )}
        {size.width > 0 && (
          <canvas
            ref={canvasRef}
            className="snapnote-editor-canvas snapnote-crop-canvas"
            // The cursor depends on what is under the pointer, so it can't be in the stylesheet.
            style={{ cursor }}
            width={size.width}
            height={size.height}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
          />
        )}
      </div>
    </div>
  );
}
