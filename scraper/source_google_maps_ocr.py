from __future__ import annotations

from scraper.discovery import SearchRequest
from scraper.models import Lead
from scraper.image_engine.image_pipeline import ImagePipeline
from scraper.image_engine.ocr import TesseractOCR


class GoogleMapsOCRAdapter:
    id = "google_maps_ocr"

    def __init__(
        self,
        output_dir: str = "data/image_engine",
        *,
        timeout: float = 30.0,
        radius_m: int = 100,
        language: str = "eng+hin",
    ) -> None:
        self.pipeline = ImagePipeline(
            output_dir,
            timeout=timeout,
            radius_m=radius_m,
        )
        self.ocr = TesseractOCR(language=language)

    def search(self, request: SearchRequest) -> list[Lead]:
        if not request.keyword.strip() or request.limit <= 0:
            return []

        location = request.location.strip() or request.keyword.strip()
        frames = self.pipeline.run(location)

        results: list[Lead] = []

        for frame in frames:
            ocr_result = self.ocr.extract(frame.path)

            text = " ".join(
                region.text
                for region in ocr_result.regions
            ).strip()

            if not text:
                continue

            results.append(
                Lead(
                    description=text,
                    location=location,
                    source_url=str(frame.path),
                    source_name=self.id,
                    source_id=frame.panoid,
                    search_context=request.keyword,
                    raw_data={
                        "panoid": frame.panoid,
                        "yaw": frame.yaw,
                        "pitch": frame.pitch,
                        "width": frame.width,
                        "height": frame.height,
                        "ocr_regions": [
                            {
                                "text": region.text,
                                "confidence": region.confidence,
                                "left": region.left,
                                "top": region.top,
                                "width": region.width,
                                "height": region.height,
                            }
                            for region in ocr_result.regions
                        ],
                    },
                )
            )

            if len(results) >= request.limit:
                break

        return results

    def close(self) -> None:
        pass
