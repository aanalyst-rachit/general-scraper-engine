from __future__ import annotations

from pathlib import Path


class ImagePreprocessor:
    def __init__(
        self,
        *,
        contrast: float = 1.15,
        sharpness: float = 1.2,
    ) -> None:
        if contrast <= 0:
            raise ValueError("contrast must be > 0")

        if sharpness <= 0:
            raise ValueError("sharpness must be > 0")

        self.contrast = float(contrast)
        self.sharpness = float(sharpness)

    def process(
        self,
        source_path: str | Path,
        output_path: str | Path,
    ) -> Path:
        source = Path(source_path)

        if not source.is_file():
            raise FileNotFoundError(
                f"source image does not exist: {source}"
            )

        from PIL import Image, ImageEnhance

        with Image.open(source) as image:
            processed = image.convert("RGB")

            processed = ImageEnhance.Contrast(
                processed
            ).enhance(self.contrast)

            processed = ImageEnhance.Sharpness(
                processed
            ).enhance(self.sharpness)

            destination = Path(output_path)
            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            processed.save(
                destination,
                format="PNG",
            )

        return destination
