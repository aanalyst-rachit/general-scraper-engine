from __future__ import annotations

from pathlib import Path

from scraper.image_engine.browser import ImageEngineBrowser, default_browser_factory
from scraper.image_engine.location_resolver import GoogleMapsLocationResolver
from scraper.image_engine.pano_discovery import StreetViewPanoDiscovery
from scraper.image_engine.preprocessing import ImagePreprocessor
from scraper.image_engine.street_view import StreetViewBrowser, StreetViewFrame
from scraper.image_engine.validation import FrameValidator


class ImagePipeline:
    def __init__(
        self,
        output_dir: str | Path,
        *,
        timeout: float = 30.0,
        radius_m: int = 100,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.timeout = float(timeout)
        self.radius_m = int(radius_m)

    def run(self, location: str) -> list[StreetViewFrame]:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        browser = ImageEngineBrowser(
            default_browser_factory,
            timeout=self.timeout,
        )

        with browser.session() as page:
            print("1. Resolving location...")
            resolver = GoogleMapsLocationResolver(
                page,
                timeout=self.timeout,
            )
            resolved = resolver.resolve(location)

            print(f"   LATITUDE: {resolved.latitude}")
            print(f"   LONGITUDE: {resolved.longitude}")

            print("2. Discovering nearest Street View pano...")
            discovery = StreetViewPanoDiscovery(
                radius_m=self.radius_m,
                timeout=self.timeout,
            )
            pano = discovery.search(
                resolved.latitude,
                resolved.longitude,
            )

            if pano is None:
                raise RuntimeError(
                    "No Street View panorama found near the requested location"
                )

            print(f"   PANO ID: {pano.panoid}")

            print("3. Capturing Street View frames...")
            street_view = StreetViewBrowser(
                page,
                timeout=self.timeout,
            )

            frames = street_view.capture_panoid(
                pano.panoid,
                self.output_dir,
                prefix="street_view",
            )

            validator = FrameValidator()

            for frame in frames:
                result = validator.validate(frame.path)

                if not result.valid:
                    raise RuntimeError(
                        f"invalid captured frame: {frame.path} "
                        f"({result.reason})"
                    )

            print(f"4. CAPTURED: {len(frames)} frames")
            print(f"5. VALIDATED: {len(frames)} frames")

            processor = ImagePreprocessor()
            processed_frames: list[StreetViewFrame] = []

            for frame in frames:
                processed_path = (
                    self.output_dir / f"processed_{frame.path.name}"
                )

                processor.process(
                    frame.path,
                    processed_path,
                )

                processed_frames.append(
                    StreetViewFrame(
                        path=processed_path,
                        panoid=frame.panoid,
                        yaw=frame.yaw,
                        pitch=frame.pitch,
                        width=frame.width,
                        height=frame.height,
                    )
                )

            print(f"6. PREPROCESSED: {len(processed_frames)} frames")

            return processed_frames
