// Before/after camera: rear camera with live preview, stamps the capture time and suburb onto
// the image (never GPS), shrinks it and uploads. There's no endpoint yet to attach a photo
// to a job as "before" or "after" — stop after the upload works and show the photo_id.

import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { generatePath, useSearchParams } from "react-router";
import { useUploadPhoto } from "../../api/photos";
import type { Photo } from "../../api/types";
import { CAMERA_JOB_PARAM, CAMERA_SUBURB_PARAM, PATHS } from "../../app/paths";
import { ErrorBanner } from "../../components/ErrorBanner";
import { formatDateTime } from "../../format";
import { shrinkPhoto } from "../../shrinkPhoto";
import { Banner, Button, Card, Screen, ScreenHeader } from "../../ui";

/** Font size for the stamp text, relative to the canvas width so it scales with resolution. */
const STAMP_FONT_RATIO = 0.03;
const STAMP_PADDING_RATIO = 0.015;
const STAMP_BAR_HEIGHT_RATIO = 0.07;
const STAMP_BAR_COLOUR = "rgba(0, 0, 0, 0.55)";
const STAMP_TEXT_COLOUR = "#ffffff";
const JPEG_QUALITY = 0.9;

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
 * Rejects when the browser can't turn the canvas into a JPEG.
 */
function captureFrame(video: HTMLVideoElement, captureTimeText: string, suburb: string): Promise<Blob> {
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext("2d")!;

  // Draw the camera frame
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  // Stamp bar at the bottom
  const barHeight = Math.round(canvas.height * STAMP_BAR_HEIGHT_RATIO);
  const barY = canvas.height - barHeight;
  ctx.fillStyle = STAMP_BAR_COLOUR;
  ctx.fillRect(0, barY, canvas.width, barHeight);

  // Stamp text
  const fontSize = Math.round(canvas.width * STAMP_FONT_RATIO);
  const padding = Math.round(canvas.width * STAMP_PADDING_RATIO);
  ctx.fillStyle = STAMP_TEXT_COLOUR;
  ctx.font = `${fontSize}px sans-serif`;
  ctx.textBaseline = "middle";

  const textY = barY + barHeight / 2;
  ctx.fillText(captureTimeText, padding, textY);

  const suburbText = suburb.trim();
  if (suburbText) {
    const suburbWidth = ctx.measureText(suburbText).width;
    ctx.fillText(suburbText, canvas.width - suburbWidth - padding, textY);
  }

  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("Canvas couldn't produce an image"))),
      "image/jpeg",
      JPEG_QUALITY,
    );
  });
}

/** Stops every track on the stream so the camera light goes off. */
function stopStream(stream: MediaStream | null) {
  stream?.getTracks().forEach((track) => track.stop());
}

/**
 * A temporary URL for showing a photo that's only in memory, freed when the photo changes or
 * the screen closes. Null while there's no photo.
 */
function useObjectUrl(blob: Blob | null) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!blob) {
      setObjectUrl(null);
      return;
    }
    const newObjectUrl = URL.createObjectURL(blob);
    setObjectUrl(newObjectUrl);
    return () => URL.revokeObjectURL(newObjectUrl);
  }, [blob]);

  return objectUrl;
}

type CameraState = "starting" | "ready" | "error";

/** The live camera preview, capture, and upload flow. */
function CameraView({ suburb, backTo }: { suburb: string; backTo: string }) {
  const { t, i18n } = useTranslation();
  const videoRef = useRef<HTMLVideoElement>(null);
  const [cameraState, setCameraState] = useState<CameraState>("starting");
  const [capturedBlob, setCapturedBlob] = useState<Blob | null>(null);
  const [uploadedPhoto, setUploadedPhoto] = useState<Photo | null>(null);
  const [hasCaptureFailed, setHasCaptureFailed] = useState(false);
  const uploadPhoto = useUploadPhoto();
  const capturedPhotoUrl = useObjectUrl(capturedBlob);
  const isPreviewing = capturedBlob === null;

  // The camera is open exactly while the live preview is on screen: on arrival and after each
  // retake. The <video> exists by the time this runs, because the preview rendered first.
  useEffect(() => {
    if (!isPreviewing) {
      return;
    }
    let isCancelled = false;
    let stream: MediaStream | null = null;

    async function startCamera() {
      try {
        stream = await openRearCamera();
        if (isCancelled) {
          stopStream(stream);
          return;
        }
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }
        if (!isCancelled) setCameraState("ready");
      } catch {
        if (!isCancelled) setCameraState("error");
      }
    }

    startCamera();
    return () => {
      isCancelled = true;
      stopStream(stream);
    };
  }, [isPreviewing]);

  /**
   * Stamps the current frame and starts the upload. The frame is drawn while the camera is
   * still running; leaving the preview then closes the camera. If the frame can't be made,
   * the preview stays open so the person can try again.
   */
  async function capturePhoto() {
    const video = videoRef.current;
    if (!video || video.videoWidth === 0) return;
    setHasCaptureFailed(false);

    try {
      const captureTimeText = formatDateTime(new Date().toISOString(), i18n.language);
      const stampedPhoto = await captureFrame(video, captureTimeText, suburb);
      const shrunkPhoto = await shrinkPhoto(stampedPhoto).catch(() => stampedPhoto);
      setCapturedBlob(shrunkPhoto);
      uploadPhoto.mutate(shrunkPhoto, { onSuccess: setUploadedPhoto });
    } catch {
      setHasCaptureFailed(true);
    }
  }

  /** Discards the captured photo and goes back to the live preview, which reopens the camera. */
  function retakePhoto() {
    uploadPhoto.reset();
    setUploadedPhoto(null);
    setHasCaptureFailed(false);
    setCameraState("starting");
    setCapturedBlob(null);
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
        <Button variant="secondary" isBlock onClick={retakePhoto}>
          {t("camera.retake")}
        </Button>
      </Screen>
    );
  }

  // Captured but still uploading
  if (!isPreviewing) {
    return (
      <Screen>
        <ScreenHeader backTo={backTo} title={t("camera.title")} />
        {capturedPhotoUrl && <img className="job-photo" src={capturedPhotoUrl} alt={t("camera.uploaded")} />}
        {uploadPhoto.isPending && <p className="small muted">{t("camera.uploading")}</p>}
        {uploadPhoto.isError && <ErrorBanner error={uploadPhoto.error} />}
        <Button variant="secondary" isBlock onClick={retakePhoto} disabled={uploadPhoto.isPending}>
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
      {hasCaptureFailed && <Banner tone="warning" title={t("errors.generic")} />}
      <Button isBlock icon="camera" onClick={capturePhoto} disabled={cameraState !== "ready"}>
        {t("camera.capture")}
      </Button>
    </Screen>
  );
}

export default function CameraScreen() {
  const [searchParams] = useSearchParams();
  const suburb = searchParams.get(CAMERA_SUBURB_PARAM) ?? "";
  const jobId = searchParams.get(CAMERA_JOB_PARAM);
  // Return to the job screen if opened from one, otherwise to the feed
  const backTo = jobId ? generatePath(PATHS.job, { jobId }) : PATHS.feed;

  return <CameraView suburb={suburb} backTo={backTo} />;
}
