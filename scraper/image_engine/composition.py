from __future__ import annotations

from pathlib import Path


class FrameComposer:
    def __init__(
        self,
        *,
        spacing: int = 20,
    ) -> None:
        if spacing < 0:
            raise ValueError("spacing must be >= 0")

        self.spacing = spacing

    def compose(
        self,
        frame_paths: list[str | Path],
        output_path: str | Path,
    ) -> Path:
        if not frame_paths:
            raise ValueError("frame_paths must not be empty")

        from PIL import Image

        images: list[Image.Image] = []

        try:
            for frame_path in frame_paths:
                path = Path(frame_path)

                if not path.is_file():
                    raise FileNotFoundError(
                        f"frame does not exist: {path}"
                    )

                image = Image.open(path).convert("RGB")
                images.append(image)

            target_width = max(
                image.width
                for image in images
            )

            resized: list[Image.Image] = []

            for image in images:
                if image.width == target_width:
                    resized.append(image)
                    continue

                ratio = target_width / image.width
                height = max(
                    1,
                    round(image.height * ratio),
                )

                resized.append(
                    image.resize(
                        (target_width, height),
                        Image.Resampling.LANCZOS,
                    )
                )

            total_height = (
                sum(image.height for image in resized)
                + self.spacing * (len(resized) - 1)
            )

            canvas = Image.new(
                "RGB",
                (target_width, total_height),
                "white",
            )

            y = 0

            for image in resized:
                canvas.paste(image, (0, y))
                y += image.height + self.spacing

            destination = Path(output_path)
            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            canvas.save(
                destination,
                format="PNG",
            )

            return destination

        finally:
            for image in images:
                image.close()
