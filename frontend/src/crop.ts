import { Point } from './types';

/** A rectangle in screenshot pixel coordinates. */
export type Rect = { x: number; y: number; width: number; height: number };

export type Handle = 'n' | 's' | 'e' | 'w' | 'ne' | 'nw' | 'se' | 'sw' | 'move';

/** Smallest crop side, in screenshot pixels. */
export const MIN_CROP = 16;

const clamp = (value: number, min: number, max: number) =>
  Math.min(Math.max(value, min), max);

export const fullRect = (width: number, height: number): Rect => ({
  x: 0,
  y: 0,
  width,
  height,
});

export const isFullRect = (rect: Rect, width: number, height: number) =>
  rect.x <= 0 && rect.y <= 0 && rect.width >= width && rect.height >= height;

/** Rectangle spanned by two points, kept inside the image. */
export function rectFromPoints(a: Point, b: Point, width: number, height: number): Rect {
  const x1 = clamp(Math.min(a.x, b.x), 0, width);
  const y1 = clamp(Math.min(a.y, b.y), 0, height);
  const x2 = clamp(Math.max(a.x, b.x), 0, width);
  const y2 = clamp(Math.max(a.y, b.y), 0, height);
  return { x: x1, y: y1, width: x2 - x1, height: y2 - y1 };
}

/**
 * Moves or resizes `start` by the total pointer movement (dx, dy), always inside the
 * image and never smaller than MIN_CROP.
 */
export function resizeRect(
  start: Rect,
  handle: Handle,
  dx: number,
  dy: number,
  width: number,
  height: number,
): Rect {
  if (handle === 'move') {
    return {
      x: clamp(start.x + dx, 0, width - start.width),
      y: clamp(start.y + dy, 0, height - start.height),
      width: start.width,
      height: start.height,
    };
  }
  let left = start.x;
  let top = start.y;
  let right = start.x + start.width;
  let bottom = start.y + start.height;
  if (handle.includes('w')) left = clamp(left + dx, 0, right - MIN_CROP);
  if (handle.includes('e')) right = clamp(right + dx, left + MIN_CROP, width);
  if (handle.includes('n')) top = clamp(top + dy, 0, bottom - MIN_CROP);
  if (handle.includes('s')) bottom = clamp(bottom + dy, top + MIN_CROP, height);
  return { x: left, y: top, width: right - left, height: bottom - top };
}

/**
 * Which part of the rectangle is under `point`: a corner or edge (within `tolerance`),
 * its inside ('move') or null when the point is outside.
 */
export function hitHandle(rect: Rect, point: Point, tolerance: number): Handle | null {
  const right = rect.x + rect.width;
  const bottom = rect.y + rect.height;
  const inside =
    point.x >= rect.x - tolerance &&
    point.x <= right + tolerance &&
    point.y >= rect.y - tolerance &&
    point.y <= bottom + tolerance;
  if (!inside) return null;
  let vertical = '';
  if (Math.abs(point.y - rect.y) <= tolerance) vertical = 'n';
  else if (Math.abs(point.y - bottom) <= tolerance) vertical = 's';
  let horizontal = '';
  if (Math.abs(point.x - rect.x) <= tolerance) horizontal = 'w';
  else if (Math.abs(point.x - right) <= tolerance) horizontal = 'e';
  return (vertical + horizontal || 'move') as Handle;
}

/** Cropped copy of the image as a PNG; null if it cannot be produced. */
export async function cropBlob(blob: Blob, rect: Rect): Promise<Blob | null> {
  const bitmap = await createImageBitmap(blob);
  try {
    const x = clamp(Math.round(rect.x), 0, bitmap.width - 1);
    const y = clamp(Math.round(rect.y), 0, bitmap.height - 1);
    const width = clamp(Math.round(rect.width), 1, bitmap.width - x);
    const height = clamp(Math.round(rect.height), 1, bitmap.height - y);
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;
    ctx.drawImage(bitmap, x, y, width, height, 0, 0, width, height);
    return await new Promise<Blob | null>((resolve) => {
      canvas.toBlob(resolve, 'image/png');
    });
  } finally {
    bitmap.close();
  }
}
