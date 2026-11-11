import { describe, expect, it } from 'vitest';
import { containedRect, strokeWidthFor, toImagePoint } from './drawing';

const rect = (width: number, height: number, left = 0, top = 0) =>
  ({ width, height, left, top }) as DOMRect;

describe('containedRect', () => {
  it('letterboxes a wide image inside a tall box', () => {
    const box = containedRect(rect(100, 200), 400, 200);
    expect(box).toEqual({ left: 0, top: 75, width: 100, height: 50 });
  });
  it('pillarboxes a tall image inside a wide box', () => {
    const box = containedRect(rect(200, 100), 100, 200);
    expect(box).toEqual({ left: 75, top: 0, width: 50, height: 100 });
  });
});

function fakeCanvas(width: number, height: number, box: DOMRect) {
  return { width, height, getBoundingClientRect: () => box } as unknown as HTMLCanvasElement;
}

describe('toImagePoint / strokeWidthFor', () => {
  // 400x200 image shown in 100x200 box at (10, 20): scale 4, vertical offset 75.
  const canvas = fakeCanvas(400, 200, rect(100, 200, 10, 20));
  it('maps client coordinates to image pixels', () => {
    expect(toImagePoint(canvas, 10, 95)).toEqual({ x: 0, y: 0 });
    expect(toImagePoint(canvas, 60, 120)).toEqual({ x: 200, y: 100 });
  });
  it('keeps a 3px on-screen stroke', () => {
    expect(strokeWidthFor(canvas)).toBe(12);
  });
});
