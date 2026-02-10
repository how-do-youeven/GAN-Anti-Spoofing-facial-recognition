"""
CropImage - from Silent-Face-Anti-Spoofing (minivision-ai).
Creates patches from original image using bbox and scale.
"""
import cv2
import numpy as np


class CropImage:
    """Create patch from original input image by using bbox coordinate."""

    @staticmethod
    def _get_new_box(src_w: int, src_h: int, bbox: list, scale: float):
        x, y, box_w, box_h = bbox[0], bbox[1], bbox[2], bbox[3]
        if scale is not None:
            scale = min((src_h - 1) / box_h, min((src_w - 1) / box_w, scale))
        new_width = box_w * scale
        new_height = box_h * scale
        center_x = box_w / 2 + x
        center_y = box_h / 2 + y
        left_top_x = center_x - new_width / 2
        left_top_y = center_y - new_height / 2
        right_bottom_x = center_x + new_width / 2
        right_bottom_y = center_y + new_height / 2
        if left_top_x < 0:
            right_bottom_x -= left_top_x
            left_top_x = 0
        if left_top_y < 0:
            right_bottom_y -= left_top_y
            left_top_y = 0
        if right_bottom_x > src_w - 1:
            left_top_x -= right_bottom_x - src_w + 1
            right_bottom_x = src_w - 1
        if right_bottom_y > src_h - 1:
            left_top_y -= right_bottom_y - src_h + 1
            right_bottom_y = src_h - 1
        return (
            int(left_top_x),
            int(left_top_y),
            int(right_bottom_x),
            int(right_bottom_y),
        )

    def crop(
        self,
        org_img: np.ndarray,
        bbox: list,
        scale: float,
        out_w: int,
        out_h: int,
        crop: bool = True,
    ) -> np.ndarray:
        """Crop and resize face region. bbox: [left, top, width, height]."""
        if not crop or scale is None:
            return cv2.resize(org_img, (out_w, out_h))
        src_h, src_w = org_img.shape[0], org_img.shape[1]
        left_top_x, left_top_y, right_bottom_x, right_bottom_y = self._get_new_box(
            src_w, src_h, bbox, scale
        )
        img = org_img[
            left_top_y : right_bottom_y + 1,
            left_top_x : right_bottom_x + 1,
        ]
        if img.size == 0:
            return cv2.resize(org_img, (out_w, out_h))
        return cv2.resize(img, (out_w, out_h))
