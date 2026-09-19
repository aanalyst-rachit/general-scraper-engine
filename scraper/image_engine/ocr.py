from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OCRRegion:
    text: str
    confidence: float
    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True)
class OCRResult:
    text: str
    source_path: Path
    regions: tuple[OCRRegion, ...]


class TesseractOCR:
    def __init__(
        self,
        *,
        language: str = "eng",
        min_confidence: float = 0.0,
    ) -> None:
        language = language.strip()
        if not language:
            raise ValueError("language must not be empty")

        if min_confidence < 0 or min_confidence > 100:
            raise ValueError("min_confidence must be between 0 and 100")

        self.language = language
        self.min_confidence = float(min_confidence)

    def filter_regions(
        self,
        regions: tuple[OCRRegion, ...] | list[OCRRegion],
        *,
        image_height: int | None = None,
    ) -> tuple[OCRRegion, ...]:
        blocked_text = {
            "inter",
            "image",
            "capture:",
            "terms",
            "report",
        }

        filtered: list[OCRRegion] = []

        for region in regions:
            normalized = region.text.strip().lower()

            if normalized in blocked_text:
                continue

            if image_height is not None:
                if image_height <= 0:
                    raise ValueError("image_height must be > 0")

                footer_start = image_height * 0.90

                if region.top >= footer_start:
                    continue
            elif region.top >= 500:
                continue

            if region.confidence < 50.0:
                continue

            filtered.append(region)

        return tuple(filtered)

    def extract(self, image_path: str | Path) -> OCRResult:
        source = Path(image_path)

        if not source.is_file():
            raise FileNotFoundError(
                f"image does not exist: {source}"
            )

        import pytesseract
        from PIL import Image

        with Image.open(source) as image:
            text = pytesseract.image_to_string(
                image,
                lang=self.language,
            )

            data = pytesseract.image_to_data(
                image,
                lang=self.language,
                output_type=pytesseract.Output.DICT,
            )

        regions: list[OCRRegion] = []

        for index, raw_text in enumerate(data["text"]):
            region_text = raw_text.strip()
            if not region_text:
                continue

            confidence = float(data["conf"][index])
            if confidence < 0:
                continue

            if confidence < self.min_confidence:
                continue

            regions.append(
                OCRRegion(
                    text=region_text,
                    confidence=confidence,
                    left=int(data["left"][index]),
                    top=int(data["top"][index]),
                    width=int(data["width"][index]),
                    height=int(data["height"][index]),
                )
            )

        filtered_regions = self.filter_regions(
            regions,
            image_height=image.height,
        )

        return OCRResult(
            text=text,
            source_path=source,
            regions=filtered_regions,
        )
