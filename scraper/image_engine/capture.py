from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CapturedFrame:
    path: Path
    index: int


class FrameCapture:
    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)

    def capture(
        self,
        page: object,
        *,
        count: int = 1,
        prefix: str = "frame",
    ) -> list[CapturedFrame]:
        if count <= 0:
            raise ValueError("count must be > 0")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        frames: list[CapturedFrame] = []

        for index in range(count):
            path = self.output_dir / f"{prefix}_{index:03d}.png"

            page.screenshot(
                path=str(path),
                full_page=False,
            )

            frames.append(
                CapturedFrame(
                    path=path,
                    index=index,
                )
            )

        return frames
