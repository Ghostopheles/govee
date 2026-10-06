from govee.shared import GoveeColor, create_color


def test_white():
    c = GoveeColor.white()
    assert (c.r, c.g, c.b) == (255, 255, 255)


def test_red():
    c = GoveeColor.red()
    assert (c.r, c.g, c.b) == (255, 0, 0)


def test_green():
    c = GoveeColor.green()
    assert (c.r, c.g, c.b) == (0, 255, 0)


def test_blue():
    c = GoveeColor.blue()
    assert (c.r, c.g, c.b) == (0, 0, 255)


def test_gold():
    c = GoveeColor.gold()
    assert (c.r, c.g, c.b) == (255, 215, 0)


def test_purple():
    c = GoveeColor.purple()
    assert (c.r, c.g, c.b) == (102, 36, 126)


def test_to_bgr_red():
    # red = r=255 g=0 b=0 → BGR int = 0x0000FF
    assert GoveeColor.red().to_bgr() == 0x0000FF


def test_to_bgr_blue():
    # blue = r=0 g=0 b=255 → BGR int = 0xFF0000
    assert GoveeColor.blue().to_bgr() == 0xFF0000


def test_to_bgr_green():
    # green = r=0 g=255 b=0 → BGR int = 0x00FF00
    assert GoveeColor.green().to_bgr() == 0x00FF00


def test_to_dict_matches_create_color():
    c = GoveeColor(10, 20, 30)
    assert c.to_dict() == create_color(10, 20, 30)
