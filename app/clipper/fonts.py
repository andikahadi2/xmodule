from pathlib import Path

FONTS_DIR = Path(__file__).parent / "fonts"

# (id, display label, font family name as embedded in the .ttf, file name)
_FONTS = [
    ("anton", "Anton (Bold Display)", "Anton", "Anton-Regular.ttf"),
    ("archivo-black", "Archivo Black", "Archivo Black", "ArchivoBlack-Regular.ttf"),
    ("bebas-neue", "Bebas Neue", "Bebas Neue", "BebasNeue-Regular.ttf"),
    ("lato-bold", "Lato Bold", "Lato", "Lato-Bold.ttf"),
    ("montserrat", "Montserrat", "Montserrat", "Montserrat-Variable.ttf"),
    ("open-sans", "Open Sans", "Open Sans", "OpenSans-Variable.ttf"),
    ("oswald", "Oswald", "Oswald", "Oswald-Variable.ttf"),
    ("permanent-marker", "Permanent Marker", "Permanent Marker", "PermanentMarker-Regular.ttf"),
    ("poppins-bold", "Poppins Bold", "Poppins", "Poppins-Bold.ttf"),
    ("roboto", "Roboto", "Roboto", "Roboto-Variable.ttf"),
]

SUBTITLE_FONTS: dict[str, dict[str, str]] = {
    font_id: {"label": label, "family": family, "file": filename}
    for font_id, label, family, filename in _FONTS
}

DEFAULT_SUBTITLE_FONT = "anton"


def font_family(font_id: str) -> str:
    entry = SUBTITLE_FONTS.get(font_id) or SUBTITLE_FONTS[DEFAULT_SUBTITLE_FONT]
    return entry["family"]
