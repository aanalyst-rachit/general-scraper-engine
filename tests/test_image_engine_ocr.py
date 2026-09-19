from pathlib import Path

from PIL import Image, ImageDraw


def test_tesseract_ocr_extracts_text(tmp_path: Path) -> None:
    from scraper.image_engine.ocr import TesseractOCR

    source = tmp_path / "text.png"

    image = Image.new("RGB", (900, 300), "white")
    draw = ImageDraw.Draw(image)
    draw.text((100, 100), "Sadar Bazar", fill="black")
    image.save(source)

    ocr = TesseractOCR(language="eng")
    result = ocr.extract(source)

    assert result.text.strip()
    assert "Sadar" in result.text


def test_tesseract_ocr_returns_text_regions(tmp_path: Path) -> None:
    from scraper.image_engine.ocr import TesseractOCR

    source = tmp_path / "regions.png"

    image = Image.new("RGB", (1200, 400), "white")
    draw = ImageDraw.Draw(image)
    draw.text((100, 120), "Sadar Bazar", fill="black")
    image.save(source)

    ocr = TesseractOCR(language="eng")
    result = ocr.extract(source)

    assert result.text.strip()
    assert result.regions

    region = result.regions[0]
    assert region.text.strip()
    assert region.confidence >= 0
    assert region.width > 0
    assert region.height > 0


def test_tesseract_ocr_regions_have_valid_bounds(tmp_path: Path) -> None:
    from scraper.image_engine.ocr import TesseractOCR

    source = tmp_path / "bounds.png"

    image = Image.new("RGB", (1200, 400), "white")
    draw = ImageDraw.Draw(image)
    draw.text((100, 120), "Sadar Bazar", fill="black")
    image.save(source)

    ocr = TesseractOCR(language="eng+hin")
    result = ocr.extract(source)

    for region in result.regions:
        assert region.left >= 0
        assert region.top >= 0
        assert region.left + region.width <= 1200
        assert region.top + region.height <= 400


def test_tesseract_ocr_can_filter_low_confidence_regions(
    tmp_path: Path,
) -> None:
    from scraper.image_engine.ocr import TesseractOCR

    source = tmp_path / "filter.png"

    image = Image.new("RGB", (1200, 400), "white")
    draw = ImageDraw.Draw(image)
    draw.text((100, 120), "Sadar Bazar", fill="black")
    image.save(source)

    ocr = TesseractOCR(
        language="eng+hin",
        min_confidence=50.0,
    )

    result = ocr.extract(source)

    assert result.regions

    assert all(
        region.confidence >= 50.0
        for region in result.regions
    )


def test_tesseract_ocr_rejects_invalid_confidence_thresholds() -> None:
    from scraper.image_engine.ocr import TesseractOCR

    TesseractOCR(language="eng", min_confidence=0)
    TesseractOCR(language="eng", min_confidence=100)

    import pytest

    with pytest.raises(ValueError):
        TesseractOCR(language="eng", min_confidence=-1)

    with pytest.raises(ValueError):
        TesseractOCR(language="eng", min_confidence=101)


def test_ocr_filter_removes_known_google_ui_text() -> None:
    from scraper.image_engine.ocr import OCRRegion, TesseractOCR

    regions = (
        OCRRegion("Bahadurganj", 92.0, 100, 100, 120, 30),
        OCRRegion("Rd", 95.0, 230, 100, 30, 30),
        OCRRegion("INTER", 96.0, 500, 500, 60, 25),
        OCRRegion("image", 68.0, 500, 550, 60, 25),
        OCRRegion("capture:", 94.0, 570, 550, 80, 25),
        OCRRegion("Terms", 33.0, 700, 550, 60, 25),
        OCRRegion("Report", 37.0, 800, 550, 60, 25),
    )

    ocr = TesseractOCR(language="eng")

    filtered = ocr.filter_regions(regions)

    texts = [region.text for region in filtered]

    assert "Bahadurganj" in texts
    assert "Rd" in texts

    assert "INTER" not in texts
    assert "image" not in texts
    assert "capture:" not in texts
    assert "Terms" not in texts
    assert "Report" not in texts


def test_ocr_filter_preserves_hindi_place_text() -> None:
    from scraper.image_engine.ocr import OCRRegion, TesseractOCR

    regions = (
        OCRRegion("सदर", 93.0, 100, 100, 60, 30),
        OCRRegion("बाज़ार", 84.0, 170, 100, 90, 30),
        OCRRegion("INTER", 96.0, 500, 500, 60, 25),
    )

    ocr = TesseractOCR(language="eng+hin")

    filtered = ocr.filter_regions(regions)

    texts = [region.text for region in filtered]

    assert "सदर" in texts
    assert "बाज़ार" in texts
    assert "INTER" not in texts


def test_ocr_filter_removes_low_quality_footer_fragments() -> None:
    from scraper.image_engine.ocr import OCRRegion, TesseractOCR

    regions = (
        OCRRegion("Bahadurganj", 92.0, 100, 100, 120, 30),
        OCRRegion("Rd", 95.0, 230, 100, 30, 30),
        OCRRegion("hjaha", 40.0, 300, 100, 50, 30),
        OCRRegion("सदर", 93.0, 100, 150, 60, 30),
        OCRRegion("बाज़ार", 84.0, 170, 150, 90, 30),
        OCRRegion("Jun", 81.0, 100, 550, 30, 25),
        OCRRegion("2026Google", 51.0, 140, 550, 100, 25),
        OCRRegion("India", 33.0, 250, 550, 50, 25),
        OCRRegion("Pi", 37.0, 320, 550, 20, 25),
        OCRRegion("provi", 52.0, 350, 550, 40, 25),
    )

    ocr = TesseractOCR(language="eng+hin")

    filtered = ocr.filter_regions(regions)

    texts = [region.text for region in filtered]

    assert "Bahadurganj" in texts
    assert "Rd" in texts
    assert "सदर" in texts
    assert "बाज़ार" in texts

    assert "hjaha" not in texts
    assert "Jun" not in texts
    assert "2026Google" not in texts
    assert "India" not in texts
    assert "Pi" not in texts
    assert "provi" not in texts


def test_ocr_filter_uses_relative_footer_position() -> None:
    from scraper.image_engine.ocr import OCRRegion, TesseractOCR

    regions = (
        OCRRegion("Bahadurganj", 92.0, 100, 100, 120, 30),
        OCRRegion("सदर", 93.0, 100, 150, 60, 30),
        OCRRegion("Jun", 81.0, 100, 650, 30, 25),
    )

    ocr = TesseractOCR(language="eng+hin")

    filtered = ocr.filter_regions(
        regions,
        image_height=700,
    )

    texts = [region.text for region in filtered]

    assert "Bahadurganj" in texts
    assert "सदर" in texts
    assert "Jun" not in texts


def test_ocr_filter_rejects_invalid_image_height() -> None:
    import pytest

    from scraper.image_engine.ocr import OCRRegion, TesseractOCR

    regions = (
        OCRRegion("Sadar", 90.0, 100, 100, 60, 30),
    )

    ocr = TesseractOCR(language="eng")

    with pytest.raises(ValueError):
        ocr.filter_regions(regions, image_height=0)

    with pytest.raises(ValueError):
        ocr.filter_regions(regions, image_height=-100)


def test_tesseract_ocr_extract_returns_filtered_regions(
    tmp_path: Path,
) -> None:
    from scraper.image_engine.ocr import TesseractOCR

    source = tmp_path / "filtered.png"

    image = Image.new("RGB", (1200, 700), "white")
    draw = ImageDraw.Draw(image)

    draw.text((100, 100), "Bahadurganj Rd", fill="black")
    draw.text((100, 150), "सदर बाज़ार", fill="black")

    image.save(source)

    ocr = TesseractOCR(
        language="eng+hin",
        min_confidence=0.0,
    )

    result = ocr.extract(source)

    texts = [region.text for region in result.regions]

    assert result.regions
    assert "Bahadurganj" in texts or "Bahadurganj Rd" in result.text


def test_tesseract_ocr_extract_filters_regions(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import pytesseract

    from scraper.image_engine.ocr import TesseractOCR

    source = tmp_path / "mocked.png"

    image = Image.new("RGB", (1200, 700), "white")
    image.save(source)

    mocked_data = {
        "text": [
            "Bahadurganj",
            "Rd",
            "INTER",
            "image",
            "सदर",
            "बाज़ार",
            "Jun",
        ],
        "conf": [
            "92",
            "95",
            "96",
            "68",
            "93",
            "84",
            "81",
        ],
        "left": [100, 230, 500, 500, 100, 170, 100],
        "top": [100, 100, 500, 550, 150, 150, 650],
        "width": [120, 30, 60, 60, 60, 90, 30],
        "height": [30, 30, 25, 25, 30, 30, 25],
    }

    monkeypatch.setattr(
        pytesseract,
        "image_to_string",
        lambda *args, **kwargs: "Bahadurganj Rd\\nसदर बाज़ार\\nJun",
    )

    monkeypatch.setattr(
        pytesseract,
        "image_to_data",
        lambda *args, **kwargs: mocked_data,
    )

    ocr = TesseractOCR(
        language="eng+hin",
        min_confidence=0.0,
    )

    result = ocr.extract(source)

    texts = [region.text for region in result.regions]

    assert texts == [
        "Bahadurganj",
        "Rd",
        "सदर",
        "बाज़ार",
    ]
