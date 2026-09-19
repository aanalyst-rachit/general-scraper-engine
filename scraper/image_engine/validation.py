from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FrameValidation:
    path: Path
    valid: bool
    width: int
    height: int
    reason: str = ""


class FrameValidator:
    def __init__(
        self,
        *,
        min_width: int = 320,
        min_height: int = 240,
    ) -> None:
        if min_width <= 0:
            raise ValueError("min_width must be > 0")

        if min_height <= 0:
            raise ValueError("min_height must be > 0")

        self.min_width = min_width
        self.min_height = min_height

    def validate(self, path: str | Path) -> FrameValidation:
        image_path = Path(path)

        if not image_path.is_file():
            return FrameValidation(
                path=image_path,
                valid=False,
                width=0,
                height=0,
                reason="file does not exist",
            )

        try:
            from PIL import Image

            with Image.open(image_path) as image:
                width, height = image.size

        except Exception as exc:
            return FrameValidation(
                path=image_path,
                valid=False,
                width=0,
                height=0,
                reason=f"invalid image: {exc}",
            )

        if width < self.min_width or height < self.min_height:
            return FrameValidation(
                path=image_path,
                valid=False,
                width=width,
                height=height,
                reason="image is too small",
            )

        return FrameValidation(
            path=image_path,
            valid=True,
            width=width,
            height=height,
        )
