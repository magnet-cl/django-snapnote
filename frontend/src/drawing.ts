import { Point, Shape } from './types';

export const ANNOTATION_COLOR = '#e5383b';
export const STROKE_PX = 3;
const TEXT_SIZE_FACTOR = 6;

export function drawShape(ctx: CanvasRenderingContext2D, shape: Shape) {
  const { tool, points, width, text } = shape;
  if (points.length === 0) return;

  ctx.save();
  ctx.strokeStyle = ANNOTATION_COLOR;
  ctx.fillStyle = ANNOTATION_COLOR;
  ctx.lineWidth = width;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';

  if (tool === 'pen') {
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    points.slice(1).forEach((p) => ctx.lineTo(p.x, p.y));
    if (points.length === 1) ctx.lineTo(points[0].x + 0.01, points[0].y);
    ctx.stroke();
  } else if (tool === 'rect' && points.length > 1) {
    const [a, b] = [points[0], points[points.length - 1]];
    ctx.strokeRect(a.x, a.y, b.x - a.x, b.y - a.y);
  } else if (tool === 'text' && text) {
    ctx.font = `bold ${width * TEXT_SIZE_FACTOR}px sans-serif`;
    ctx.textBaseline = 'top';
    ctx.lineWidth = width;
    ctx.strokeStyle = '#ffffff';
    ctx.strokeText(text, points[0].x, points[0].y);
    ctx.fillText(text, points[0].x, points[0].y);
  }
  ctx.restore();
}

export function drawShapes(ctx: CanvasRenderingContext2D, shapes: Shape[]) {
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  shapes.forEach((shape) => drawShape(ctx, shape));
}

export function textFontSize(width: number) {
  return width * TEXT_SIZE_FACTOR;
}

/**
 * Rectangle (in element CSS pixels) that an image with object-fit: contain
 * really occupies inside its element.
 */
export function containedRect(
  rect: DOMRect,
  naturalWidth: number,
  naturalHeight: number,
) {
  const scale = Math.min(
    rect.width / naturalWidth,
    rect.height / naturalHeight,
  );
  const width = naturalWidth * scale;
  const height = naturalHeight * scale;
  return {
    left: (rect.width - width) / 2,
    top: (rect.height - height) / 2,
    width,
    height,
  };
}

/** Maps a pointer position to screenshot pixel coordinates. */
export function toImagePoint(
  canvas: HTMLCanvasElement,
  clientX: number,
  clientY: number,
): Point {
  const rect = canvas.getBoundingClientRect();
  const box = containedRect(rect, canvas.width, canvas.height);
  const scale = canvas.width / box.width;
  return {
    x: (clientX - rect.left - box.left) * scale,
    y: (clientY - rect.top - box.top) * scale,
  };
}

/** On-screen stroke of STROKE_PX, expressed in screenshot pixels. */
export function strokeWidthFor(canvas: HTMLCanvasElement) {
  const rect = canvas.getBoundingClientRect();
  const box = containedRect(rect, canvas.width, canvas.height);
  return (STROKE_PX * canvas.width) / box.width;
}

/** Renders only the shapes on a transparent PNG; null if there are none. */
export function renderAnnotationLayer(
  shapes: Shape[],
  width: number,
  height: number,
): Promise<Blob | null> {
  if (shapes.length === 0) return Promise.resolve(null);
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  if (!ctx) return Promise.resolve(null);
  drawShapes(ctx, shapes);
  return new Promise((resolve) => {
    canvas.toBlob(resolve, 'image/png');
  });
}
