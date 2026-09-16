import pytest

from dealdesk.integrations.youtube import _parse_duration, video_id_from_url


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ&t=42s",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ?si=abc",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
        "youtube.com/watch?v=dQw4w9WgXcQ",
        "dQw4w9WgXcQ",
        "  https://www.youtube.com/live/dQw4w9WgXcQ  ",
    ],
)
def test_video_id_from_url(url):
    assert video_id_from_url(url) == "dQw4w9WgXcQ"


@pytest.mark.parametrize("url", ["https://instagram.com/p/abc/", "https://youtube.com/", "not a url", ""])
def test_video_id_rejects(url):
    assert video_id_from_url(url) is None


def test_parse_duration():
    assert _parse_duration("PT1H2M3S") == 3723
    assert _parse_duration("PT45S") == 45
    assert _parse_duration("PT3M") == 180
    assert _parse_duration("") == 0
