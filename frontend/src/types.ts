export type Tool = 'pen' | 'rect' | 'text';

export type Point = { x: number; y: number };

/** A shape in screenshot pixel coordinates. */
export type Shape = {
  tool: Tool;
  points: Point[];
  width: number;
  text?: string;
};

export type Labels = {
  report: string;
  title: string;
  description: string;
  preview: string;
  editAnnotations: string;
  send: string;
  cancel: string;
  sending: string;
  success: string;
  error: string;
  noCapture: string;
  attach: string;
  pen: string;
  rectangle: string;
  text: string;
  undo: string;
  clear: string;
  done: string;
  titleRequired: string;
};

export type Props = {
  report_url: string;
  csrf_token?: string;
  labels: Labels;
  max_upload_mb: number;
};
