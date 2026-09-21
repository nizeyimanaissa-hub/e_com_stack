from app.routers.trains import _parse_line_name


def test_parse_line_name_with_space():
    assert _parse_line_name("ICE 76") == ("ICE", "76")


def test_parse_line_name_without_space():
    assert _parse_line_name("RE4 (82016)") == ("RE", "4 (82016)")


def test_parse_line_name_unparseable():
    assert _parse_line_name("123") == ("UNKNOWN", "123")
