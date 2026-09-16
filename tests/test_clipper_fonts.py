from app.clipper.fonts import DEFAULT_SUBTITLE_FONT, FONTS_DIR, SUBTITLE_FONTS, font_family


def test_exactly_ten_fonts_available():
    assert len(SUBTITLE_FONTS) == 10


def test_default_font_is_valid_entry():
    assert DEFAULT_SUBTITLE_FONT in SUBTITLE_FONTS


def test_every_font_file_exists_on_disk():
    for entry in SUBTITLE_FONTS.values():
        assert (FONTS_DIR / entry["file"]).is_file()


def test_font_family_falls_back_to_default_for_unknown_id():
    assert font_family("does-not-exist") == font_family(DEFAULT_SUBTITLE_FONT)


def test_font_family_returns_embedded_family_name():
    assert font_family("bebas-neue") == "Bebas Neue"
