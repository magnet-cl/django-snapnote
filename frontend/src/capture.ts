const SHARE_NOTICE_DELAY_MS = 300;

/**
 * Captures the current tab as a PNG blob. Returns null if the user cancels
 * or the browser doesn't support it.
 */
export async function captureScreen(): Promise<Blob | null> {
  if (!navigator.mediaDevices?.getDisplayMedia) {
    return null;
  }

  let stream: MediaStream | null = null;
  try {
    stream = await navigator.mediaDevices.getDisplayMedia({
      video: { displaySurface: 'browser' },
      audio: false,
      // Chromium only; ignored elsewhere.
      preferCurrentTab: true,
    } as DisplayMediaStreamOptions);

    const video = document.createElement('video');
    video.muted = true;
    video.srcObject = stream;
    await video.play();
    // Wait for the "sharing" notice to disappear from the frame.
    await new Promise((resolve) => {
      setTimeout(resolve, SHARE_NOTICE_DELAY_MS);
    });

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d')?.drawImage(video, 0, 0);
    return await new Promise<Blob | null>((resolve) => {
      canvas.toBlob(resolve, 'image/png');
    });
  } catch {
    return null;
  } finally {
    stream?.getTracks().forEach((track) => track.stop());
  }
}
