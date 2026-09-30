// Before/after camera: rear camera with live preview, stamps the capture time and suburb onto
// the image (never GPS), shrinks it and uploads. There's no endpoint yet to attach a photo
// to a job as "before" or "after" — stop after the upload works and show the photo_id.

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router";
import { getErrorMessageKey } from "../../api/errors";
import { useUploadPhoto } from "../../api/photos";
import type { Photo } from "../../api/types";
import { PATHS } from "../../app/paths";
import { ErrorBanner } from "../../components/ErrorBanner";
import { shrinkPhoto } from "../../shrinkPhoto";
import { Banner, Button, Card, Screen, ScreenHeader } from "../../ui";

/** Font size for the stamp text, relative to the canvas width so it scales with resolution. */
const STAMP_FONT_RATIO = 0.03;
const STAMP_PADDING_RATIO = 0.015;
const STAMP_BAR_HEIGHT_RATIO = 0.07;

/** Opens the rear camera. Audio is off because we only need a still frame. */
async function openRearCamera(): Promise<MediaStream> {
  return navigator.mediaDevices.getUserMedia({
    video: { facingMode: "environment" },
    audio: false,
  });
}

/**
 * Draws the video frame onto a canvas, then overlays a translucent bar with the capture time
 * and the suburb. No GPS coordinates are written; the server also strips EXIF on its side.
 */
function captureFrame(video: HTMLVideoElement, suburb: string): Promise<Blob> {
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext("2d")!;

  // Draw the camera frame
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  // Stamp bar at the bottom
  const barHeight = Math.round(canvas.height * STAMP_BAR_HEIGHT_RATIO);
  const barY = canvas.height - barHeight;
  ctx.fillStyle = "rgba(0, 0, 0, 0.55)";
  ctx.fillRect(0, barY, canvas.width, barHeight);

  // Stamp text
  const fontSize = Math.round(canvas.width * STAMP_FONT_RATIO);
  const padding = Math.round(canvas.width * STAMP_PADDING_RATIO);
  ctx.fillStyle = "#ffffff";
  ctx.font = `${fontSize}px sans-serif`;
  ctx.textBaseline = "middle";

  const textY = barY + barHeight / 2;
  const timestamp = new Date().toLocaleString();
  ctx.fillText(timestamp, padding, textY);

  const suburbText = suburb.trim();
  if (suburbText) {
    const suburbWidth = ctx.measureText(suburbText).width;
    ctx.fillText(suburbText, canvas.width - suburbWidth - padding, textY);
  }

  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("Canvas couldn't produce an image"))),
      "image/jpeg",
      0.9,
    );
  });
}

/** Stops every track on the stream so the camera light goes off. */
function stopStream(stream: MediaStream | null) {
  stream?.getTracks().forEach((track) => track.stop());
}

type CameraState = "starting" | "ready" | "error";

/** The live camera preview, capture, and upload flow. */
function CameraView({ suburb, backTo }: { suburb: string; backTo: string }) {
  const { t } = useTranslation();
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [cameraState, setCameraState] = useState<CameraState>("starting");
  const [capturedBlob, setCapturedBlob] = useState<Blob | null>(null);
  const [uploadedPhoto, setUploadedPhoto] = useState<Photo | null>(null);
  const uploadPhoto = useUploadPhoto();

  // Open the camera when the screen mounts, and close it when leaving
  useEffect(() => {
    let cancelled = false;

    async function startCamera() {
      try {
        const stream = await openRearCamera();
        if (cancelled) {
          stopStream(stream);
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }
        setCameraState("ready");
      } catch {
        if (!cancelled) setCameraState("error");
      }
    }

    startCamera();
    return () => {
      cancelled = true;
      stopStream(streamRef.current);
      streamRef.current = null;
    };
  }, []);

  /** Freezes the current frame with the stamp, then hands it to the uploader. */
  const handleCapture = useCallback(async () => {
    if (!videoRef.current) return;
    stopStream(streamRef.current);
    streamRef.current = null;

    try {
      const blob = await captureFrame(videoRef.current, suburb);
      const shrunk = await shrinkPhoto(blob).catch(() => blob);
      setCapturedBlob(shrunk);
      uploadPhoto.mutate(shrunk, { onSuccess: setUploadedPhoto });
    } catch {
      // If capture or shrink fails, restart the camera so the person can try again
      try {
        const stream = await openRearCamera();
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }
      } catch {
        setCameraState("error");
      }
    }
  }, [suburb, uploadPhoto]);

  /** Discards the captured frame and restarts the camera. */
  async function handleRetake() {
    setCapturedBlob(null);
    setUploadedPhoto(null);
    uploadPhoto.reset();
    try {
      const stream = await openRearCamera();
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCameraState("ready");
    } catch {
      setCameraState("error");
    }
  }

  // Camera couldn't start: show the reason and a way back
  if (cameraState === "error") {
    return (
      <Screen>
        <ScreenHeader backTo={backTo} title={t("camera.title")} />
        <Banner tone="warning" title={t("camera.noCameraTitle")}>
          <p className="small">{t("camera.noCameraBody")}</p>
        </Banner>
      </Screen>
    );
  }

  // Photo uploaded: show the result
  if (uploadedPhoto) {
    return (
      <Screen>
        <ScreenHeader backTo={backTo} title={t("camera.title")} />
        <Card tone="lime">
          <p className="section-title">{t("camera.uploaded")}</p>
          <p className="small">{t("camera.photoId", { id: uploadedPhoto.photo_id })}</p>
        </Card>
        <img className="job-photo" src={uploadedPhoto.url} alt={t("camera.uploaded")} />
        <Button variant="secondary" isBlock onClick={handleRetake}>
          {t("camera.retake")}
        </Button>
      </Screen>
    );
  }

  // Captured but still uploading
  if (capturedBlob) {
    return (
      <Screen>
        <ScreenHeader backTo={backTo} title={t("camera.title")} />
        <img
          className="job-photo"
          src={URL.createObjectURL(capturedBlob)}
          alt={t("camera.uploaded")}
        />
        {uploadPhoto.isPending && <p className="small muted">{t("camera.uploading")}</p>}
        {uploadPhoto.isError && <ErrorBanner error={uploadPhoto.error} />}
        <Button variant="secondary" isBlock onClick={handleRetake} disabled={uploadPhoto.isPending}>
          {t("camera.retake")}
        </Button>
      </Screen>
    );
  }

  // Live preview
  return (
    <Screen>
      <ScreenHeader backTo={backTo} title={t("camera.title")} subtitle={t("camera.subtitle")} />
      <div className="camera-preview">
        <video ref={videoRef} playsInline muted className="camera-preview__video" />
        {cameraState === "starting" && (
          <p className="camera-preview__loading">{t("app.loading")}</p>
        )}
      </div>
      <Button isBlock icon="camera" onClick={handleCapture} disabled={cameraState !== "ready"}>
        {t("camera.capture")}
      </Button>
    </Screen>
  );
}

export default function CameraScreen() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const suburb = searchParams.get("suburb") ?? "";
  const jobId = searchParams.get("jobId");
  // Return to the job screen if opened from one, otherwise to the feed
  const backTo = jobId ? `/jobs/${encodeURIComponent(jobId)}` : PATHS.feed;

  return <CameraView suburb={suburb} backTo={backTo} />;
}
