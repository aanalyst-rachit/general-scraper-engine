from __future__ import annotations

from pathlib import Path

from PIL import Image

from scraper.image_engine.capture import CapturedFrame, FrameCapture
from scraper.image_engine.composition import FrameComposer
from scraper.image_engine.validation import FrameValidator


def test_frame_capture_captures_multiple_frames(tmp_path: Path) -> None:
    class FakePage:
        def screenshot(self, *, path: str, full_page: bool) -> None:
            assert full_page is False

            Image.new(
                "RGB",
                (640, 480),
                "white",
            ).save(path)

    capture = FrameCapture(tmp_path)

    frames = capture.capture(
        FakePage(),
        count=3,
    )

    assert len(frames) == 3
    assert all(isinstance(frame, CapturedFrame) for frame in frames)
    assert all(frame.path.is_file() for frame in frames)
    assert [frame.index for frame in frames] == [0, 1, 2]


def test_frame_validator_accepts_valid_image(tmp_path: Path) -> None:
    image_path = tmp_path / "valid.png"

    Image.new(
        "RGB",
        (640, 480),
        "white",
    ).save(image_path)

    result = FrameValidator().validate(image_path)

    assert result.valid is True
    assert result.width == 640
    assert result.height == 480
    assert result.reason == ""


def test_frame_validator_rejects_small_image(tmp_path: Path) -> None:
    image_path = tmp_path / "small.png"

    Image.new(
        "RGB",
        (100, 100),
        "white",
    ).save(image_path)

    result = FrameValidator().validate(image_path)

    assert result.valid is False
    assert result.reason == "image is too small"


def test_frame_validator_rejects_missing_file(tmp_path: Path) -> None:
    image_path = tmp_path / "missing.png"

    result = FrameValidator().validate(image_path)

    assert result.valid is False
    assert result.reason == "file does not exist"


def test_frame_composer_combines_frames(tmp_path: Path) -> None:
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    output = tmp_path / "combined.png"

    Image.new(
        "RGB",
        (640, 480),
        "white",
    ).save(first)

    Image.new(
        "RGB",
        (640, 360),
        "white",
    ).save(second)

    result = FrameComposer(spacing=20).compose(
        [first, second],
        output,
    )

    assert result == output
    assert output.is_file()

    with Image.open(output) as image:
        assert image.width == 640
        assert image.height == 860


def test_street_view_opens_location() -> None:
    from scraper.image_engine.street_view import StreetViewBrowser

    class FakePage:
        def __init__(self) -> None:
            self.goto_args = None
            self.url = "https://www.google.com/maps/search/?api=1&query=Delhi"

        def goto(
            self,
            url: str,
            *,
            wait_until: str,
            timeout: float,
        ) -> None:
            self.goto_args = (url, wait_until, timeout)

    page = FakePage()
    browser = StreetViewBrowser(page, timeout=20)

    result = browser.open_location("Delhi")

    assert "Delhi" in page.goto_args[0]
    assert page.goto_args[1] == "domcontentloaded"
    assert page.goto_args[2] == 20000
    assert result == page.url


def test_street_view_opens_street_view() -> None:
    from scraper.image_engine.street_view import StreetViewBrowser

    class FakePage:
        def __init__(self) -> None:
            self.goto_args = None
            self.url = (
                "https://www.google.com/maps/@"
                "?api=1&map_action=pano"
                "&viewpoint=Delhi"
            )

        def goto(
            self,
            url: str,
            *,
            wait_until: str,
            timeout: float,
        ) -> None:
            self.goto_args = (url, wait_until, timeout)

    page = FakePage()
    browser = StreetViewBrowser(page, timeout=20)

    result = browser.open_street_view("Delhi")

    assert "map_action=pano" in page.goto_args[0]
    assert "viewpoint=Delhi" in page.goto_args[0]
    assert page.goto_args[1] == "domcontentloaded"
    assert page.goto_args[2] == 20000
    assert result == page.url


def test_street_view_extracts_panoid_from_real_url() -> None:
    from scraper.image_engine.street_view import StreetViewBrowser

    url = (
        "https://www.google.com/maps/"
        "@27.8862234,79.9136217,172a,43.5y,87.77h,98.43t/"
        "data=!3m7!1e1!3m5!1sJj4ZrcCOhRs8kfTee_4x6Q!2e0!"
        "6shttps:%2F%2Fstreetviewpixels-pa.googleapis.com%2Fv1%2Fthumbnail"
        "%3Fcb_client%3Dmaps_sv.tactile"
        "%26w%3D900%26h%3D600"
        "%26pitch%3D-8.426615797914963"
        "%26panoid%3DJj4ZrcCOhRs8kfTee_4x6Q"
        "%26yaw%3D87.7657214145002"
        "!7i16384!8i8192"
    )

    assert (
        StreetViewBrowser.extract_panoid(url)
        == "Jj4ZrcCOhRs8kfTee_4x6Q"
    )


def test_street_view_extracts_camera_angles() -> None:
    from scraper.image_engine.street_view import StreetViewBrowser

    url = (
        "https://www.google.com/maps/"
        "@27.8862234,79.9136217,172a,43.5y,87.77h,98.43t/"
        "data=!3m7!1e1!3m5!1sJj4ZrcCOhRs8kfTee_4x6Q!2e0!"
        "6shttps:%2F%2Fstreetviewpixels-pa.googleapis.com%2Fv1%2Fthumbnail"
        "%3Fcb_client%3Dmaps_sv.tactile"
        "%26w%3D900%26h%3D600"
        "%26pitch%3D-8.426615797914963"
        "%26panoid%3DJj4ZrcCOhRs8kfTee_4x6Q"
        "%26yaw%3D87.7657214145002"
        "!7i16384!8i8192"
    )

    assert (
        StreetViewBrowser.extract_yaw(url)
        == 87.7657214145002
    )

    assert (
        StreetViewBrowser.extract_pitch(url)
        == -8.426615797914963
    )


def test_street_view_builds_thumbnail_url() -> None:
    from scraper.image_engine.street_view import StreetViewBrowser

    url = StreetViewBrowser.build_thumbnail_url(
        panoid="Jj4ZrcCOhRs8kfTee_4x6Q",
        yaw=90,
        pitch=-8.4,
        width=900,
        height=600,
    )

    assert (
        "streetviewpixels-pa.googleapis.com/v1/thumbnail"
        in url
    )
    assert "panoid=Jj4ZrcCOhRs8kfTee_4x6Q" in url
    assert "yaw=90.0" in url
    assert "pitch=-8.4" in url
    assert "w=900" in url
    assert "h=600" in url


def test_street_view_generates_frame_angles() -> None:
    from scraper.image_engine.street_view import StreetViewBrowser

    angles = StreetViewBrowser.frame_angles(
        start_yaw=87.7657214145002,
        step=45,
        count=8,
    )

    assert len(angles) == 8
    assert angles[0] == 87.7657214145002
    assert angles[1] == 132.7657214145002
    assert angles[-1] == 402.7657214145002 % 360




def test_image_pipeline_validates_captured_frames(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scraper.image_engine.image_pipeline import ImagePipeline
    from scraper.image_engine.street_view import StreetViewFrame

    first = tmp_path / "street_view_000.png"
    second = tmp_path / "street_view_001.png"

    Image.new("RGB", (640, 480), "white").save(first)
    Image.new("RGB", (640, 480), "white").save(second)

    class FakePage:
        pass

    class FakeSession:
        def __enter__(self):
            return FakePage()

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeBrowser:
        def __init__(self, *args, **kwargs):
            pass

        def session(self):
            return FakeSession()

    class FakeResolved:
        latitude = 27.8827709
        longitude = 79.9137236

    class FakeResolver:
        def __init__(self, *args, **kwargs):
            pass

        def resolve(self, location):
            assert location == "Sadar Bazar, Shahjahanpur"
            return FakeResolved()

    class FakePano:
        panoid = "test-panoid"

    class FakeDiscovery:
        def __init__(self, *args, **kwargs):
            pass

        def search(self, latitude, longitude):
            assert latitude == 27.8827709
            assert longitude == 79.9137236
            return FakePano()

    class FakeStreetView:
        def __init__(self, *args, **kwargs):
            pass

        def capture_panoid(self, panoid, output_dir, *, prefix):
            assert panoid == "test-panoid"
            assert output_dir == tmp_path
            assert prefix == "street_view"

            return [
                StreetViewFrame(
                    path=first,
                    panoid=panoid,
                    yaw=0.0,
                    pitch=0.0,
                    width=640,
                    height=480,
                ),
                StreetViewFrame(
                    path=second,
                    panoid=panoid,
                    yaw=45.0,
                    pitch=0.0,
                    width=640,
                    height=480,
                ),
            ]

    monkeypatch.setattr(
        "scraper.image_engine.image_pipeline.ImageEngineBrowser",
        FakeBrowser,
    )
    monkeypatch.setattr(
        "scraper.image_engine.image_pipeline.GoogleMapsLocationResolver",
        FakeResolver,
    )
    monkeypatch.setattr(
        "scraper.image_engine.image_pipeline.StreetViewPanoDiscovery",
        FakeDiscovery,
    )
    monkeypatch.setattr(
        "scraper.image_engine.image_pipeline.StreetViewBrowser",
        FakeStreetView,
    )

    frames = ImagePipeline(tmp_path).run(
        "Sadar Bazar, Shahjahanpur",
    )

    assert len(frames) == 2
    assert all(frame.path.is_file() for frame in frames)


def test_image_pipeline_rejects_invalid_captured_frame(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scraper.image_engine.image_pipeline import ImagePipeline
    from scraper.image_engine.street_view import StreetViewFrame

    valid = tmp_path / "street_view_000.png"
    invalid = tmp_path / "street_view_001.png"

    Image.new("RGB", (640, 480), "white").save(valid)
    invalid.write_bytes(b"not-an-image")

    class FakePage:
        pass

    class FakeSession:
        def __enter__(self):
            return FakePage()

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeBrowser:
        def __init__(self, *args, **kwargs):
            pass

        def session(self):
            return FakeSession()

    class FakeResolved:
        latitude = 27.8827709
        longitude = 79.9137236

    class FakeResolver:
        def __init__(self, *args, **kwargs):
            pass

        def resolve(self, location):
            return FakeResolved()

    class FakePano:
        panoid = "test-panoid"

    class FakeDiscovery:
        def __init__(self, *args, **kwargs):
            pass

        def search(self, latitude, longitude):
            return FakePano()

    class FakeStreetView:
        def __init__(self, *args, **kwargs):
            pass

        def capture_panoid(self, panoid, output_dir, *, prefix):
            return [
                StreetViewFrame(
                    path=valid,
                    panoid=panoid,
                    yaw=0.0,
                    pitch=0.0,
                    width=640,
                    height=480,
                ),
                StreetViewFrame(
                    path=invalid,
                    panoid=panoid,
                    yaw=45.0,
                    pitch=0.0,
                    width=640,
                    height=480,
                ),
            ]

    monkeypatch.setattr(
        "scraper.image_engine.image_pipeline.ImageEngineBrowser",
        FakeBrowser,
    )
    monkeypatch.setattr(
        "scraper.image_engine.image_pipeline.GoogleMapsLocationResolver",
        FakeResolver,
    )
    monkeypatch.setattr(
        "scraper.image_engine.image_pipeline.StreetViewPanoDiscovery",
        FakeDiscovery,
    )
    monkeypatch.setattr(
        "scraper.image_engine.image_pipeline.StreetViewBrowser",
        FakeStreetView,
    )

    try:
        ImagePipeline(tmp_path).run("Sadar Bazar, Shahjahanpur")
    except RuntimeError as exc:
        assert "invalid captured frame" in str(exc)
    else:
        raise AssertionError(
            "ImagePipeline should reject an invalid captured frame"
        )


def test_image_preprocessor_creates_ocr_ready_image(
    tmp_path: Path,
) -> None:
    from scraper.image_engine.preprocessing import ImagePreprocessor

    source = tmp_path / "source.png"
    output = tmp_path / "processed.png"

    image = Image.new("RGB", (900, 600), "gray")

    for x in range(100, 800):
        for y in range(200, 400):
            image.putpixel((x, y), (120, 120, 120))

    image.save(source)

    result = ImagePreprocessor().process(
        source,
        output,
    )

    assert result == output
    assert output.is_file()

    with Image.open(output) as processed:
        assert processed.width == 900
        assert processed.height == 600
        assert processed.mode == "RGB"


def test_image_pipeline_preprocesses_validated_frames(
    tmp_path: Path,
) -> None:
    from scraper.image_engine.image_pipeline import ImagePipeline
    from scraper.image_engine.street_view import StreetViewFrame

    class FakeBrowserSession:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return None

    class FakeBrowser:
        def __init__(self, browser_factory, *, timeout):
            pass

        def session(self):
            return FakeBrowserSession()

    class FakeResolver:
        def __init__(self, page, *, timeout):
            pass

        def resolve(self, location):
            from scraper.image_engine.location_resolver import ResolvedLocation

            return ResolvedLocation(
                query=location,
                latitude=27.88,
                longitude=79.91,
                url="https://example.com/maps",
            )

    class FakeDiscovery:
        def __init__(self, *, radius_m, timeout):
            pass

        def search(self, latitude, longitude):
            from scraper.image_engine.pano_discovery import PanoLocation

            return PanoLocation(
                panoid="test-pano",
                latitude=latitude,
                longitude=longitude,
            )

    class FakeStreetView:
        def __init__(self, page, *, timeout):
            pass

        def capture_panoid(self, panoid, output_dir, *, prefix):
            from PIL import Image

            source = Path(output_dir) / "street_view_000.png"
            Image.new("RGB", (640, 480), "gray").save(source)

            return [
                StreetViewFrame(
                    path=source,
                    panoid=panoid,
                    yaw=0.0,
                    pitch=0.0,
                    width=640,
                    height=480,
                )
            ]

    import scraper.image_engine.image_pipeline as pipeline_module

    pipeline_module.ImageEngineBrowser = FakeBrowser
    pipeline_module.GoogleMapsLocationResolver = FakeResolver
    pipeline_module.StreetViewPanoDiscovery = FakeDiscovery
    pipeline_module.StreetViewBrowser = FakeStreetView

    result = ImagePipeline(tmp_path).run("test location")

    assert len(result) == 1
    assert result[0].path.name == "processed_street_view_000.png"
    assert result[0].path.is_file()
