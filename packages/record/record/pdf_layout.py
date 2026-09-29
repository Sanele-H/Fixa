"""The look of every record PDF: an embedded Unicode font, headings, tables, a progress bar,
photos and a QR code, with a footer on every page.

DejaVu Sans is embedded (see fonts/LICENSE_DEJAVU), so names and customers' words in any
South African language print correctly, not just Latin-1.
"""

import io
import re
from pathlib import Path

import qrcode
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from fpdf.fonts import FontFace

FONTS_PATH = Path(__file__).resolve().parent / "fonts"
FONT_FAMILY = "DejaVu"
INK = (11, 11, 11)
SECONDARY_INK = (82, 81, 78)
MUTED_INK = (137, 135, 129)
HAIRLINE = (225, 224, 217)
WHITE = (255, 255, 255)
TABLE_HEADING_FILL = (240, 239, 236)
ACCENT = (42, 120, 214)  # Fixa blue, as in the pitch charts
MARGIN_MM = 18
BOTTOM_MARGIN_MM = 18
TITLE_SIZE_PT = 18
HEADING_SIZE_PT = 13
BODY_SIZE_PT = 10
NOTE_SIZE_PT = 8.5
LINE_HEIGHT_MM = 5.2
PARAGRAPH_GAP_MM = 2.5
SECTION_GAP_MM = 6
MIN_SECTION_ROOM_MM = 40  # a heading needs this much room below it on its page
PROGRESS_BAR_HEIGHT_MM = 5
MARKER_LABEL_WIDTH_MM = 34
QR_QUIET_MODULES = 2  # white border around the QR code, in modules
PHONE_NUMBER_PATTERN = re.compile(r"\+?\d[\d\s-]{6,}\d")
HIDDEN_NUMBER_TEXT = "[number hidden]"


class RecordPdf(FPDF):
    """An A4 record PDF with the Fixa look and a footer line on every page.

    text_log keeps every piece of text written, in order. The embedded font stores text
    as glyph ids, so this is how tests (and anyone checking) can read what a PDF says.
    """

    def __init__(self, footer_text: str, title: str) -> None:
        super().__init__(format="A4")
        self.footer_text = footer_text
        self.text_log: list[str] = []
        self.set_margins(MARGIN_MM, MARGIN_MM, MARGIN_MM)
        self.set_auto_page_break(auto=True, margin=BOTTOM_MARGIN_MM)
        self.add_font(FONT_FAMILY, "", FONTS_PATH / "DejaVuSans.ttf")
        self.add_font(FONT_FAMILY, "B", FONTS_PATH / "DejaVuSans-Bold.ttf")
        self.set_title(title)
        self.set_creator("Fixa")
        self.add_page()

    def footer(self) -> None:
        """Writes the footer text and the page number at the bottom of every page."""
        self.set_y(-BOTTOM_MARGIN_MM + 6)
        self.set_font(FONT_FAMILY, size=NOTE_SIZE_PT)
        self.set_text_color(*MUTED_INK)
        self.cell(0, 4, f"{self.footer_text}   ·   Page {self.page_no()} of {{nb}}")

    def write_title(self, text: str) -> None:
        """Writes the document title."""
        self.write_block(text, TITLE_SIZE_PT, INK, bold=True, line_height_mm=8)

    def write_heading(self, text: str, room_needed_mm: float = MIN_SECTION_ROOM_MM) -> None:
        """Writes a section heading, on a new page if less than room_needed_mm is left."""
        if self.get_y() > self.h - BOTTOM_MARGIN_MM - room_needed_mm:
            self.add_page()
        self.ln(SECTION_GAP_MM)
        self.write_block(text, HEADING_SIZE_PT, INK, bold=True, line_height_mm=6.5)

    def write_text(self, text: str, bold: bool = False) -> None:
        """Writes a paragraph of body text."""
        self.write_block(text, BODY_SIZE_PT, INK, bold=bold)

    def write_note(self, text: str) -> None:
        """Writes a paragraph of small, quieter text."""
        self.write_block(text, NOTE_SIZE_PT, SECONDARY_INK, line_height_mm=4.2)

    def write_block(
        self,
        text: str,
        size_pt: float,
        color: tuple[int, int, int],
        bold: bool = False,
        line_height_mm: float = LINE_HEIGHT_MM,
        width_mm: float = 0,
    ) -> None:
        """Writes wrapped text (full width unless width_mm is set), then a small gap."""
        self.text_log.append(text)
        self.set_font(FONT_FAMILY, style="B" if bold else "", size=size_pt)
        self.set_text_color(*color)
        self.multi_cell(
            width_mm, line_height_mm, text, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT
        )
        self.ln(PARAGRAPH_GAP_MM)

    def write_table(
        self, headings: list[str], rows: list[list[str]], column_widths_mm: list[float]
    ) -> None:
        """Writes a table with a shaded heading row; long cells wrap and pages break cleanly."""
        self.set_font(FONT_FAMILY, size=NOTE_SIZE_PT + 0.5)
        self.set_text_color(*INK)
        self.set_draw_color(*HAIRLINE)
        heading_style = FontFace(emphasis="BOLD", fill_color=TABLE_HEADING_FILL)
        self.set_fill_color(*WHITE)  # tables otherwise reuse the last fill colour
        with self.table(
            col_widths=column_widths_mm,
            width=sum(column_widths_mm),
            align="LEFT",
            text_align="LEFT",
            line_height=4.6,
            headings_style=heading_style,
            borders_layout="HORIZONTAL_LINES",
            cell_fill_mode="NONE",
        ) as table:
            for cells in [headings, *rows]:
                table_row = table.row()
                for cell_text in cells:
                    self.text_log.append(cell_text)
                    table_row.cell(cell_text)
        self.ln(PARAGRAPH_GAP_MM)

    def draw_progress_bar(self, share: float, markers: list[tuple[float, str]]) -> None:
        """Draws a filled bar for a share from 0 to 1, with labelled tick marks under it."""
        width_mm = self.w - 2 * MARGIN_MM
        top_mm = self.get_y()
        self.set_fill_color(*TABLE_HEADING_FILL)
        self.rect(MARGIN_MM, top_mm, width_mm, PROGRESS_BAR_HEIGHT_MM, style="F")
        self.set_fill_color(*ACCENT)
        self.rect(MARGIN_MM, top_mm, width_mm * min(share, 1.0), PROGRESS_BAR_HEIGHT_MM, style="F")
        self.set_font(FONT_FAMILY, size=NOTE_SIZE_PT)
        self.set_text_color(*SECONDARY_INK)
        self.set_draw_color(*INK)
        for marker_share, label in markers:
            x_mm = MARGIN_MM + width_mm * marker_share
            self.line(x_mm, top_mm - 1, x_mm, top_mm + PROGRESS_BAR_HEIGHT_MM + 1)
            label_x_mm = min(
                max(x_mm - MARKER_LABEL_WIDTH_MM / 2, MARGIN_MM),
                MARGIN_MM + width_mm - MARKER_LABEL_WIDTH_MM,
            )
            self.set_xy(label_x_mm, top_mm + PROGRESS_BAR_HEIGHT_MM + 1.5)
            self.cell(MARKER_LABEL_WIDTH_MM, 4, label, align="C")
        self.set_xy(MARGIN_MM, top_mm + PROGRESS_BAR_HEIGHT_MM + 7)
        self.ln(PARAGRAPH_GAP_MM)

    def draw_qr_code(self, url: str, x_mm: float, y_mm: float, size_mm: float) -> None:
        """Draws a QR code for a link as vector squares, and makes the square clickable."""
        qr_code = qrcode.QRCode(border=QR_QUIET_MODULES)
        qr_code.add_data(url)
        qr_code.make(fit=True)
        matrix = qr_code.get_matrix()
        module_mm = size_mm / len(matrix)
        self.set_fill_color(*INK)
        for row_index, row in enumerate(matrix):
            for start, length in find_dark_runs(row):
                self.rect(
                    x_mm + start * module_mm,
                    y_mm + row_index * module_mm,
                    length * module_mm,
                    module_mm,
                    style="F",
                )
        self.link(x_mm, y_mm, size_mm, size_mm, url)

    def draw_photo(
        self, image_bytes: bytes, x_mm: float, y_mm: float, width_mm: float, height_mm: float
    ) -> bool:
        """Draws a photo inside a box, keeping its shape. False if the bytes aren't an image."""
        try:
            self.image(
                io.BytesIO(image_bytes),
                x=x_mm,
                y=y_mm,
                w=width_mm,
                h=height_mm,
                keep_aspect_ratio=True,
            )
        except Exception:  # fpdf2 raises several error types for unreadable images
            return False
        return True


def find_dark_runs(row: list[bool]) -> list[tuple[int, int]]:
    """Returns (start, length) for each run of dark modules in a QR row."""
    runs = []
    start = None
    for index, is_dark in enumerate([*row, False]):
        if is_dark and start is None:
            start = index
        elif not is_dark and start is not None:
            runs.append((start, index - start))
            start = None
    return runs


def hide_phone_numbers(text: str) -> str:
    """Replaces anything that looks like a phone number with "[number hidden]"."""
    return PHONE_NUMBER_PATTERN.sub(HIDDEN_NUMBER_TEXT, text)


def format_date(day) -> str:
    """Formats a date as DD/MM/YYYY, the format the merSETA form asks for."""
    return day.strftime("%d/%m/%Y")
