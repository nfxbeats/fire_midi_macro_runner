from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List


@dataclass(frozen=True)
class OledRegion:
    """
    Fire OLED update region.

    The Akai Fire OLED update SysEx includes:
      start_band, end_band  (bands are 8 pixels tall; 0..7 for 64px height)
      start_col,  end_col   (0..127 for 128px width)

    Most use-cases just send full screen: bands 0..7, cols 0..127.
    """
    start_band: int = 0
    end_band: int = 7
    start_col: int = 0
    end_col: int = 127


class AkaiFireBitmap:
    """
    Maintains a framebuffer for the Akai Fire 128x64 monochrome OLED and emits
    a SysEx message to update the display.

    Key constraints / quirks:
      - MIDI SysEx data bytes must be 7-bit clean (0..127), so the OLED bitmap
        is packed using 7 bits per "byte" rather than 8.
      - The device's expected bit ordering is not linear; it uses a 'bit mutate'
        mapping (a small lookup table) and a tiling scheme of 8x7 pixels.
    """

    # OLED geometry
    WIDTH: int = 128
    HEIGHT: int = 64

    # Transfer bitmap size:
    # The OLED has 128*64 = 8192 pixels. We encode 7 pixels per MIDI-safe byte:
    # ceil(8192 / 7) = 1171 bytes.
    BITMAP_BYTES: int = 1171

    # SysEx constants (Akai manufacturer + Fire "write OLED" command 0x0E)
    SYSEX_AKAI: int = 0x47
    SYSEX_DEVICE: int = 0x7F
    SYSEX_MODEL: int = 0x43
    SYSEX_CMD_WRITE_OLED: int = 0x0E

    # For the OLED write payload, we send 4 bytes of region header
    # (start_band, end_band, start_col, end_col) + bitmap bytes.
    REGION_HEADER_BYTES: int = 4

    # This mapping reorders bits inside each 8x7 tile. The original code stores it
    # as bitMutate[x_mod_7][y_mod_8], i.e. shape [7][8]. We'll keep that convention.
    #
    # NOTE: If you prefer the SEGGER table orientation [8][7], transpose it once here
    # and adjust indexing accordingly. The important thing is to match how rb is computed.
    BIT_MUTATE: List[List[int]] = [
        [13, 0, 1, 2, 3, 4, 5, 6],
        [19, 20, 7, 8, 9, 10, 11, 12],
        [25, 26, 27, 14, 15, 16, 17, 18],
        [31, 32, 33, 34, 21, 22, 23, 24],
        [37, 38, 39, 40, 41, 28, 29, 30],
        [43, 44, 45, 46, 47, 48, 35, 36],
        [49, 50, 51, 52, 53, 54, 55, 42],
    ]

    def __init__(self, font_file_name: str):
        # User-provided BitmapFont that knows how to rasterize glyphs by calling set_pixel(x,y,c)
        self.fnt = BitmapFont(font_file_name)

        # Instance-owned framebuffer (avoid class-level shared state)
        self._bitmap: List[int] = [0] * self.BITMAP_BYTES

    # ----------------------------
    # Public API
    # ----------------------------

    def clear(self) -> None:
        """Clear the framebuffer."""
        # Fast clear (keeps list object stable)
        for i in range(self.BITMAP_BYTES):
            self._bitmap[i] = 0

    def show(self, port, region: OledRegion = OledRegion()) -> None:
        """
        Send the current framebuffer to the device via a MIDI output port.

        `port` is expected to be a mido output port (or compatible) that supports port.send(msg).
        """
        payload = self._build_payload(region)
        msg = self._build_sysex_message(payload)
        port.send(msg)

    def set_pixel(self, x: int, y: int, on: int) -> None:
        """
        Set/clear one pixel in the framebuffer.

        x: 0..127
        y: 0..63
        on: nonzero => set pixel, 0 => clear
        """
        if not (0 <= x < self.WIDTH and 0 <= y < self.HEIGHT):
            return

        byte_index, bit_mask = self._pixel_to_buffer_location(x, y)

        if on:
            self._bitmap[byte_index] |= bit_mask
        else:
            # Keep values 7-bit clean (defensive). bit_mask is <= 0x40 anyway.
            self._bitmap[byte_index] &= (~bit_mask) & 0x7F

    def horizontal_line(self, x: int, y: int, w: int) -> None:
        """Draw a horizontal line starting at (x,y) of width w."""
        # Clamp minimal work; set_pixel itself bounds-checks.
        for dx in range(w):
            self.set_pixel(x + dx, y, 1)

    def vertical_line(self, x: int, y: int, h: int) -> None:
        """Draw a vertical line starting at (x,y) of height h."""
        for dy in range(h):
            self.set_pixel(x, y + dy, 1)

    def print_at(self, x: int, y: int, text: str) -> None:
        """
        Render text using the provided bitmap font into the framebuffer.

        BitmapFont is expected to call the provided callback as:
          callback(px, py, on)
        """
        self.fnt.print_at(x, y, text, self.set_pixel)

    # ----------------------------
    # Internal helpers
    # ----------------------------

    def _build_payload(self, region: OledRegion) -> bytearray:
        """
        Build OLED write payload:
          [start_band, end_band, start_col, end_col] + bitmap_bytes
        """
        payload = bytearray(self.REGION_HEADER_BYTES + self.BITMAP_BYTES)
        payload[0] = region.start_band & 0x7F
        payload[1] = region.end_band & 0x7F
        payload[2] = region.start_col & 0x7F
        payload[3] = region.end_col & 0x7F

        # Copy bitmap into payload
        payload[4:] = bytes(self._bitmap)
        return payload

    def _build_sysex_message(self, payload: bytearray):
        """
        Construct the final SysEx message (mido.Message('sysex', ...)).

        The original code does:
          data = [0x47, 0x7f, 0x43, 0x0E, hh, ll, start_band, end_band, start_col, end_col] + bitmap

        Note: mido.Message('sysex', data=...) expects *no* leading 0xF0 and *no* trailing 0xF7.
        """
        import mido  # local import to keep the class usable even if mido isn't installed at import time

        payload_len = len(payload)
        hh = (payload_len >> 7) & 0x7F
        ll = payload_len & 0x7F

        msg_data = bytearray(
            [
                self.SYSEX_AKAI,
                self.SYSEX_DEVICE,
                self.SYSEX_MODEL,
                self.SYSEX_CMD_WRITE_OLED,
                hh,
                ll,
            ]
        )
        msg_data.extend(payload)

        return mido.Message("sysex", data=msg_data)

    def _pixel_to_buffer_location(self, x: int, y: int) -> tuple[int, int]:
        """
        Convert (x,y) to:
          (byte_index_in_bitmap, bit_mask)

        This follows the same idea as your original code:
          - Split Y into a band (8 rows tall) and a row-within-band (0..7)
          - Offset X by 128 * band to linearize the bands
          - Use the bit mutate table to pick a remapped bit position (rb)
          - Compute:
              p = (x2//7)*8 + (rb//7)
              mask = 1<<(rb%7)
        """
        # Banding: each band is 8 pixels tall
        band = y // 8
        y_in_band = y % 8

        # Linearize bands into X dimension (0..1023)
        x2 = x + 128 * band

        # Remapped bit position within a 7x8 tile
        x_mod_7 = x2 % 7
        rb = self.BIT_MUTATE[x_mod_7][y_in_band]

        # Map into the packed bitmap:
        # - Every 7 pixels in x2 correspond to an 8-byte group (one per row in the band)
        # - rb//7 selects which of those 8 bytes
        # - rb%7 selects which bit inside the 7-bit-safe data byte
        byte_index = (x2 // 7) * 8 + (rb // 7)
        bit_mask = 1 << (rb % 7)

        # byte_index is within [0..1170] for the full 128x64 range
        return byte_index, bit_mask


def _make_bitmap_without_font() -> AkaiFireBitmap:
    """
    Create AkaiFireBitmap without calling __init__.

    Useful when we only want bitmap drawing/show and do not need BitmapFont.
    """
    bmp = AkaiFireBitmap.__new__(AkaiFireBitmap)
    bmp._bitmap = [0] * AkaiFireBitmap.BITMAP_BYTES
    return bmp


def _nearest_resize_gray(src_pixels: List[int], src_w: int, src_h: int, dst_w: int, dst_h: int) -> List[int]:
    out = [0] * (dst_w * dst_h)
    for y in range(dst_h):
        sy = min(src_h - 1, (y * src_h) // dst_h)
        for x in range(dst_w):
            sx = min(src_w - 1, (x * src_w) // dst_w)
            out[y * dst_w + x] = src_pixels[sy * src_w + sx]
    return out


def _load_image_gray(path: str | Path) -> tuple[int, int, List[int]]:
    """Load image file (PNG/JPG/etc.) as grayscale 8-bit pixels."""
    p = str(path)

    try:
        from PIL import Image  # type: ignore

        img = Image.open(p).convert("L")
        w, h = img.size
        return w, h, list(img.tobytes())
    except Exception:
        # fallback for PNG using pypng
        try:
            import png  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "Failed to load image. Install Pillow (`pip install pillow`) "
                "or (for PNG fallback) pypng (`pip install pypng`)."
            ) from exc

        reader = png.Reader(filename=p)
        width, height, rows, meta = reader.read()
        rows = list(rows)
        planes = meta.get("planes", 1)
        alpha = bool(meta.get("alpha", False))
        greyscale = bool(meta.get("greyscale", False))

        gray: List[int] = []
        for row in rows:
            row = list(row)
            if greyscale:
                if alpha and planes >= 2:
                    gray.extend([row[i] for i in range(0, len(row), 2)])
                else:
                    gray.extend(row)
            else:
                step = planes
                for i in range(0, len(row), step):
                    r = row[i]
                    g = row[i + 1] if i + 1 < len(row) else r
                    b = row[i + 2] if i + 2 < len(row) else r
                    gray.append((299 * r + 587 * g + 114 * b) // 1000)
        return width, height, gray


def show_image_file(
    port,
    image_path: str | Path,
    threshold: int = 127,
    invert: bool = False,
    region: OledRegion = OledRegion(),
) -> None:
    """
    Load a PNG/JPG image file, fit to 128x64, and send it to the Fire OLED.

    - `port`: mido output port instance (supports `send(msg)`)
    - `image_path`: file path (PNG/JPG/etc.)
    - `threshold`: grayscale threshold for 1-bit conversion
    - `invert`: invert output pixels
    """
    w, h, gray = _load_image_gray(image_path)
    resized = _nearest_resize_gray(gray, w, h, AkaiFireBitmap.WIDTH, AkaiFireBitmap.HEIGHT)

    bmp = _make_bitmap_without_font()
    t = max(0, min(255, threshold))

    for y in range(AkaiFireBitmap.HEIGHT):
        row_off = y * AkaiFireBitmap.WIDTH
        for x in range(AkaiFireBitmap.WIDTH):
            on = 1 if resized[row_off + x] >= t else 0
            if invert:
                on ^= 1
            if on:
                bmp.set_pixel(x, y, 1)

    bmp.show(port, region)


def show_image_file_on_port_name(
    port_name: str,
    image_path: str | Path,
    threshold: int = 127,
    invert: bool = False,
    region: OledRegion = OledRegion(),
) -> None:
    """Convenience helper: open a MIDI output by name and display image file."""
    import mido  # type: ignore

    with mido.open_output(port_name) as out_port:
        show_image_file(out_port, image_path, threshold=threshold, invert=invert, region=region)


def pick_fire_midi_port(port_name_arg: str | None = None) -> str:
    """Pick an Akai Fire MIDI output name (or validate an explicit one)."""
    import mido  # type: ignore

    names = mido.get_output_names()
    if not names:
        raise RuntimeError("No MIDI output ports found.")

    if port_name_arg:
        if port_name_arg in names:
            return port_name_arg
        raise RuntimeError(f"MIDI output port not found: {port_name_arg}")

    for n in names:
        low = n.lower()
        if "fire" in low and "midi" in low:
            return n
    for n in names:
        if "fire" in n.lower():
            return n

    raise RuntimeError(
        "Could not auto-detect Akai Fire MIDI output port. Use an explicit --port value."
    )


def bit_from_linear_framebuffer(framebuffer: bytes, x: int, y: int, width: int) -> int:
    idx = y * width + x
    byte = framebuffer[idx // 8]
    shift = 7 - (idx % 8)
    return (byte >> shift) & 0x01


def show_linear_framebuffer(
    port,
    framebuffer: bytes,
    width: int = AkaiFireBitmap.WIDTH,
    height: int = AkaiFireBitmap.HEIGHT,
    region: OledRegion = OledRegion(),
) -> None:
    """Show an MSB-first, row-major 1-bit framebuffer on the Fire OLED."""
    bmp = _make_bitmap_without_font()

    for y in range(min(height, AkaiFireBitmap.HEIGHT)):
        for x in range(min(width, AkaiFireBitmap.WIDTH)):
            if bit_from_linear_framebuffer(framebuffer, x, y, width):
                bmp.set_pixel(x, y, 1)

    bmp.show(port, region)


def show_linear_framebuffer_on_port_name(
    port_name: str,
    framebuffer: bytes,
    width: int = AkaiFireBitmap.WIDTH,
    height: int = AkaiFireBitmap.HEIGHT,
    region: OledRegion = OledRegion(),
) -> None:
    """Convenience helper: open MIDI port by name and show a linear framebuffer."""
    import mido  # type: ignore

    with mido.open_output(port_name) as out_port:
        show_linear_framebuffer(out_port, framebuffer, width=width, height=height, region=region)


def infer_char_size(path: Path, atlas_w: int, atlas_h: int) -> tuple[int, int]:
    import re

    match = re.match(r"^(\d+)x(\d+)_", path.name)
    if match:
        return int(match.group(1)), int(match.group(2))
    return atlas_w // 16, atlas_h // 16


def get_font_char_size(font_path: str | Path) -> tuple[int, int]:
    p = Path(font_path)
    atlas_w, atlas_h, _ = _load_image_gray(p)
    return infer_char_size(p, atlas_w, atlas_h)


def build_glyph_table(
    font_path: str | Path,
    threshold: int = 127,
    invert: bool = False,
) -> tuple[int, int, dict[int, List[int]]]:
    p = Path(font_path)
    atlas_w, atlas_h, gray = _load_image_gray(p)
    char_w, char_h = infer_char_size(p, atlas_w, atlas_h)

    if atlas_w < char_w * 16 or atlas_h < char_h * 16:
        raise RuntimeError(
            f"PNG atlas too small for inferred char size {char_w}x{char_h}: {atlas_w}x{atlas_h}"
        )

    t = max(0, min(255, threshold))
    glyphs: dict[int, List[int]] = {}
    for code in range(256):
        gx = (code % 16) * char_w
        gy = (code // 16) * char_h
        bits: List[int] = []
        for y in range(char_h):
            row_off = (gy + y) * atlas_w
            for x in range(char_w):
                v = gray[row_off + gx + x]
                bit = 1 if v >= t else 0
                if invert:
                    bit ^= 1
                bits.append(bit)
        glyphs[code] = bits

    return char_w, char_h, glyphs


def render_text_into_pixels(
    pixels: List[int],
    text: str,
    x0: int,
    y0: int,
    char_w: int,
    char_h: int,
    glyphs: dict[int, List[int]],
    width: int = AkaiFireBitmap.WIDTH,
    height: int = AkaiFireBitmap.HEIGHT,
) -> None:
    x_cursor = x0

    for ch in text:
        code = ord(ch)
        glyph = glyphs.get(code, glyphs.get(ord("?"), [0] * (char_w * char_h)))
        for gy in range(char_h):
            py = y0 + gy
            if py >= height:
                continue
            for gx in range(char_w):
                px = x_cursor + gx
                if px >= width:
                    continue
                if glyph[gy * char_w + gx]:
                    pixels[py * width + px] = 1
        x_cursor += char_w
        if x_cursor >= width:
            break


def _pack_pixels_msb(pixels: List[int]) -> bytes:
    out = bytearray()
    for i in range(0, len(pixels), 8):
        byte = 0
        for b in range(8):
            byte <<= 1
            if i + b < len(pixels):
                byte |= pixels[i + b]
        out.append(byte)
    return bytes(out)


def render_text_framebuffer_from_glyphs(
    text: str,
    char_w: int,
    char_h: int,
    glyphs: dict[int, List[int]],
    width: int = AkaiFireBitmap.WIDTH,
    height: int = AkaiFireBitmap.HEIGHT,
) -> bytes:
    pixels = [0] * (width * height)
    render_text_into_pixels(pixels, text, 0, 0, char_w, char_h, glyphs, width=width, height=height)
    return _pack_pixels_msb(pixels)


def render_wrapped_text_framebuffer_from_glyphs(
    text: str,
    char_w: int,
    char_h: int,
    glyphs: dict[int, List[int]],
    width: int = AkaiFireBitmap.WIDTH,
    height: int = AkaiFireBitmap.HEIGHT,
) -> bytes:
    pixels = [0] * (width * height)

    chars_per_line = max(1, width // max(1, char_w))
    max_lines = max(1, height // max(1, char_h))

    # Normalize explicit line breaks first, then character-wrap each segment.
    # This preserves spaces exactly as provided in the text.
    segments = text.splitlines() if text else [""]
    lines: List[str] = []

    for segment in segments:
        if segment == "":
            lines.append("")
            continue

        for i in range(0, len(segment), chars_per_line):
            lines.append(segment[i : i + chars_per_line])

    y = 0
    for line in lines[:max_lines]:
        render_text_into_pixels(
            pixels,
            line,
            0,
            y,
            char_w,
            char_h,
            glyphs,
            width=width,
            height=height,
        )
        y += char_h

    return _pack_pixels_msb(pixels)


def render_font_preview_framebuffer(
    font_name: str,
    text: str,
    char_w: int,
    char_h: int,
    glyphs: dict[int, List[int]],
    width: int = AkaiFireBitmap.WIDTH,
    height: int = AkaiFireBitmap.HEIGHT,
) -> bytes:
    pixels = [0] * (width * height)
    chars_per_line = max(1, width // max(1, char_w))
    name_text = font_name[:chars_per_line]
    hello_text = text[:chars_per_line]

    if char_h * 2 + 1 <= height:
        render_text_into_pixels(pixels, name_text, 0, 0, char_w, char_h, glyphs, width=width, height=height)
        render_text_into_pixels(
            pixels, hello_text, 0, char_h + 1, char_w, char_h, glyphs, width=width, height=height
        )
    else:
        one_line = f"{name_text} {hello_text}"[:chars_per_line]
        render_text_into_pixels(pixels, one_line, 0, 0, char_w, char_h, glyphs, width=width, height=height)

    return _pack_pixels_msb(pixels)


def render_text_from_font_atlas(
    font_path: str | Path,
    text: str,
    threshold: int = 127,
    invert: bool = False,
    include_font_name: bool = False,
    word_wrap: bool = True,
) -> bytes:
    p = Path(font_path)
    char_w, char_h, glyphs = build_glyph_table(p, threshold=threshold, invert=invert)

    if include_font_name:
        return render_font_preview_framebuffer(p.stem, text, char_w, char_h, glyphs)

    if word_wrap:
        return render_wrapped_text_framebuffer_from_glyphs(text, char_w, char_h, glyphs)

    return render_text_framebuffer_from_glyphs(text, char_w, char_h, glyphs)


def show_text_from_font_atlas(
    port,
    font_path: str | Path,
    text: str,
    threshold: int = 127,
    invert: bool = False,
    include_font_name: bool = False,
    word_wrap: bool = True,
    region: OledRegion = OledRegion(),
) -> None:
    framebuffer = render_text_from_font_atlas(
        font_path,
        text,
        threshold=threshold,
        invert=invert,
        include_font_name=include_font_name,
        word_wrap=word_wrap,
    )
    show_linear_framebuffer(port, framebuffer, region=region)


def show_text_from_font_atlas_on_port_name(
    port_name: str,
    font_path: str | Path,
    text: str,
    threshold: int = 127,
    invert: bool = False,
    include_font_name: bool = False,
    word_wrap: bool = False,
    region: OledRegion = OledRegion(),
) -> None:
    import mido  # type: ignore

    with mido.open_output(port_name) as out_port:
        show_text_from_font_atlas(
            out_port,
            font_path,
            text,
            threshold=threshold,
            invert=invert,
            include_font_name=include_font_name,
            word_wrap=word_wrap,
            region=region,
        )