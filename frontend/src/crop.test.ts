import { describe, expect, it } from 'vitest';
import {
  MIN_CROP,
  fullRect,
  hitHandle,
  isFullRect,
  rectFromPoints,
  resizeRect,
} from './crop';

const W = 400;
const H = 200;
const start = { x: 100, y: 50, width: 200, height: 100 };

describe('rectFromPoints', () => {
  it('orders the corners and clamps to the image', () => {
    expect(rectFromPoints({ x: 300, y: 150 }, { x: 100, y: 50 }, W, H)).toEqual(start);
    expect(rectFromPoints({ x: -20, y: -5 }, { x: 500, y: 90 }, W, H)).toEqual({
      x: 0,
      y: 0,
      width: W,
      height: 90,
    });
  });
});

describe('resizeRect', () => {
  it('moves without leaving the image', () => {
    expect(resizeRect(start, 'move', 20, 10, W, H)).toMatchObject({ x: 120, y: 60 });
    expect(resizeRect(start, 'move', 999, 999, W, H)).toMatchObject({ x: 200, y: 100 });
    expect(resizeRect(start, 'move', -999, -999, W, H)).toMatchObject({ x: 0, y: 0 });
  });
  it('resizes from a corner', () => {
    expect(resizeRect(start, 'se', 50, 25, W, H)).toEqual({ x: 100, y: 50, width: 250, height: 125 });
    expect(resizeRect(start, 'nw', 10, 10, W, H)).toEqual({ x: 110, y: 60, width: 190, height: 90 });
  });
  it('resizes from an edge, leaving the other axis alone', () => {
    expect(resizeRect(start, 'e', 30, 99, W, H)).toEqual({ x: 100, y: 50, width: 230, height: 100 });
    expect(resizeRect(start, 'n', 99, -20, W, H)).toEqual({ x: 100, y: 30, width: 200, height: 120 });
  });
  it('keeps the minimum size and the image bounds', () => {
    expect(resizeRect(start, 'w', 999, 0, W, H)).toMatchObject({ x: 300 - MIN_CROP, width: MIN_CROP });
    expect(resizeRect(start, 's', 0, 999, W, H)).toMatchObject({ height: H - 50 });
    expect(resizeRect(start, 'e', -999, 0, W, H)).toMatchObject({ x: 100, width: MIN_CROP });
  });
});

describe('hitHandle', () => {
  it('detects corners, edges and the inside', () => {
    expect(hitHandle(start, { x: 100, y: 50 }, 5)).toBe('nw');
    expect(hitHandle(start, { x: 300, y: 150 }, 5)).toBe('se');
    expect(hitHandle(start, { x: 200, y: 52 }, 5)).toBe('n');
    expect(hitHandle(start, { x: 298, y: 100 }, 5)).toBe('e');
    expect(hitHandle(start, { x: 200, y: 100 }, 5)).toBe('move');
  });
  it('returns null outside', () => {
    expect(hitHandle(start, { x: 10, y: 10 }, 5)).toBeNull();
  });
});

describe('isFullRect', () => {
  it('is true only for the whole image', () => {
    expect(isFullRect(fullRect(W, H), W, H)).toBe(true);
    expect(isFullRect(start, W, H)).toBe(false);
  });
});
