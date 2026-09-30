// Photo uploads: POST /api/photos. The server strips the photo's metadata (GPS included)
// and answers with a signed link.

import { useMutation } from "@tanstack/react-query";
import { postFormData } from "./client";
import type { Photo } from "./types";

/** The multipart field the server reads the photo from. */
const PHOTO_FIELD_NAME = "photo";
/** Only a label for the upload: the server re-encodes every photo as JPEG whatever it's called. */
const PHOTO_FILE_NAME = "photo.jpg";

/**
 * POST /api/photos: uploads one photo and returns its `photo_id` (send it with the job) and a
 * signed `url` for <img>. Shrink it on the phone first (longest side about 1280 px, JPEG about
 * 0.7): the server refuses files over 3 MB. 429 after 30 uploads in a day.
 */
export function useUploadPhoto() {
  return useMutation({
    mutationFn: (photo: Blob) => {
      const formData = new FormData();
      formData.append(PHOTO_FIELD_NAME, photo, PHOTO_FILE_NAME);
      return postFormData<Photo>("/api/photos", formData);
    },
  });
}
