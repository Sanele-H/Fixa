"""Pitch charts for the simulation: static PNGs in the light theme of the data-viz palette.

Colours follow the ranker, never its position, so each ranker keeps its colour on every
chart. Text uses the ink colours, never a series colour. Axes are placed at fixed
positions so bar thickness and corner rounding come out at exact sizes.
"""

import functools
from collections.abc import Callable
from pathlib import Path

from matplotlib import rc_context
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.ticker import PercentFormatter

SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
TEXT_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"
# Categorical slots 1-3, validated as a set (all pairs) for colour-vision deficiency.
SERIES_COLORS = ["#2a78d6", "#eb6834", "#1baf7a"]
FONT_FAMILIES = ["Segoe UI", "Helvetica", "Arial", "DejaVu Sans"]

DPI = 200
PIXEL_IN = 1 / 96  # one CSS pixel, the unit the mark specs use
FIGURE_WIDTH_IN = 8.0
FIGURE_PADDING_IN = 0.3
TITLE_BAND_IN = 1.2  # title plus a two-line subtitle, clear of the top tick label
SHARE_AXIS_MAX = 1.0
AXIS_BAND_IN = 0.55
RIGHT_MARGIN_IN = 0.7  # room for end labels
BAR_LABEL_MARGIN_IN = 2.0  # room for ranker names left of the bars
LINE_LABEL_MARGIN_IN = 0.7
BAR_ROW_IN = 0.55
BAR_THICKNESS_IN = 22 * PIXEL_IN  # bars stay under 24 px thick
BAR_CORNER_IN = 4 * PIXEL_IN  # rounded data-end
VALUE_LABEL_GAP_IN = 6 * PIXEL_IN
LINE_WIDTH_PT = 2 * 72 * PIXEL_IN  # 2 px lines
MARKER_SIZE_PT = 9 * 72 * PIXEL_IN  # end dots of at least 8 px
MARKER_RING_PT = 2 * 72 * PIXEL_IN  # 2 px surface ring around end dots
HAIRLINE_PT = 72 * PIXEL_IN
TITLE_SIZE_PT = 13
SUBTITLE_SIZE_PT = 9.5
LABEL_SIZE_PT = 10
TICK_SIZE_PT = 9


def with_chart_font(draw_chart: Callable) -> Callable:
    """Runs a chart function with the system sans font, without changing global settings.

    Fonts are picked when matplotlib draws, so the whole chart (saving included) runs
    inside the setting.
    """

    @functools.wraps(draw_chart)
    def draw_with_chart_font(*args, **kwargs):
        with rc_context({"font.family": "sans-serif", "font.sans-serif": FONT_FAMILIES}):
            return draw_chart(*args, **kwargs)

    return draw_with_chart_font


@with_chart_font
def draw_bar_chart(
    path: Path,
    title: str,
    subtitle: str,
    bars: list[tuple[str, float, str]],
    format_value: Callable[[float], str],
) -> None:
    """Draws horizontal share bars from 0 to 100%, one per (label, share, colour), top down.

    Each bar has its value (written by format_value) at the tip and its label on the
    left. The x-axis ticks are whole percentages.
    """
    plot_height_in = len(bars) * BAR_ROW_IN
    figure, axes = create_figure(title, subtitle, plot_height_in, BAR_LABEL_MARGIN_IN)
    axes.set_xlim(0, SHARE_AXIS_MAX)
    axes.set_ylim(len(bars) - 0.5, -0.5)
    x_units_per_in = SHARE_AXIS_MAX / get_axes_width_in(BAR_LABEL_MARGIN_IN)
    y_units_per_in = len(bars) / plot_height_in
    for row, (_, value, color) in enumerate(bars):
        draw_rounded_bar(axes, row, value, color, x_units_per_in, y_units_per_in)
        axes.text(
            value + VALUE_LABEL_GAP_IN * x_units_per_in,
            row,
            format_value(value),
            va="center",
            color=TEXT_PRIMARY,
            fontsize=LABEL_SIZE_PT,
        )
    axes.set_yticks(range(len(bars)), [label for label, _, _ in bars])
    axes.tick_params(axis="y", labelcolor=TEXT_PRIMARY, labelsize=LABEL_SIZE_PT)
    axes.xaxis.set_major_formatter(PercentFormatter(xmax=SHARE_AXIS_MAX, decimals=0))
    axes.grid(axis="x", color=GRIDLINE, linewidth=HAIRLINE_PT)
    axes.axvline(0, color=BASELINE, linewidth=HAIRLINE_PT)
    save_figure(figure, path)


@with_chart_font
def draw_step_chart(
    path: Path,
    title: str,
    subtitle: str,
    lines: list[tuple[str, list[float], str]],
    x_label: str,
) -> None:
    """Draws one cumulative step line per (label, share by day, colour), from day 0.

    Each line ends in a ringed dot labelled with its final value, and a legend names them.
    """
    figure, axes = create_figure(title, subtitle, BAR_ROW_IN * 5, LINE_LABEL_MARGIN_IN)
    last_day = max(len(shares) for _, shares, _ in lines) - 1
    for label, shares, color in lines:
        days = list(range(len(shares)))
        axes.plot(
            days,
            shares,
            drawstyle="steps-post",
            color=color,
            linewidth=LINE_WIDTH_PT,
            solid_joinstyle="round",
            solid_capstyle="round",
            label=label,
        )
        draw_end_dot(axes, days[-1], shares[-1], color)
    axes.set_xlim(0, last_day)
    axes.set_ylim(0, 1.0)
    axes.yaxis.set_major_formatter(PercentFormatter(xmax=1.0, decimals=0))
    axes.set_xlabel(x_label, color=TEXT_MUTED, fontsize=TICK_SIZE_PT)
    axes.grid(axis="y", color=GRIDLINE, linewidth=HAIRLINE_PT)
    axes.axhline(0, color=BASELINE, linewidth=HAIRLINE_PT)
    legend = axes.legend(loc="center right", frameon=False, fontsize=LABEL_SIZE_PT)
    for text in legend.get_texts():
        text.set_color(TEXT_SECONDARY)
    save_figure(figure, path)


def create_figure(
    title: str, subtitle: str, plot_height_in: float, left_margin_in: float
) -> tuple[Figure, Axes]:
    """Creates a figure with a title band, one plot area and room for the x-axis."""
    figure_height_in = TITLE_BAND_IN + plot_height_in + AXIS_BAND_IN
    figure = Figure(figsize=(FIGURE_WIDTH_IN, figure_height_in), dpi=DPI, facecolor=SURFACE)
    axes = figure.add_axes(
        (
            left_margin_in / FIGURE_WIDTH_IN,
            AXIS_BAND_IN / figure_height_in,
            get_axes_width_in(left_margin_in) / FIGURE_WIDTH_IN,
            plot_height_in / figure_height_in,
        )
    )
    style_axes(axes)
    padding_x = FIGURE_PADDING_IN / FIGURE_WIDTH_IN
    figure.text(
        padding_x,
        1 - FIGURE_PADDING_IN / figure_height_in,
        title,
        va="top",
        color=TEXT_PRIMARY,
        fontsize=TITLE_SIZE_PT,
        fontweight="semibold",
    )
    figure.text(
        padding_x,
        1 - (FIGURE_PADDING_IN + 0.3) / figure_height_in,
        subtitle,
        va="top",
        color=TEXT_SECONDARY,
        fontsize=SUBTITLE_SIZE_PT,
        linespacing=1.4,
    )
    return figure, axes


def style_axes(axes: Axes) -> None:
    """Makes the axes recessive: no box, muted ticks, no tick marks."""
    axes.set_facecolor(SURFACE)
    axes.set_axisbelow(True)
    for spine in axes.spines.values():
        spine.set_visible(False)
    axes.tick_params(length=0, labelcolor=TEXT_MUTED, labelsize=TICK_SIZE_PT, pad=6)


def get_axes_width_in(left_margin_in: float) -> float:
    """Returns the plot area's width for a given left margin."""
    return FIGURE_WIDTH_IN - left_margin_in - RIGHT_MARGIN_IN


def draw_rounded_bar(
    axes: Axes, row: float, value: float, color: str, x_units_per_in: float, y_units_per_in: float
) -> None:
    """Draws a bar from zero with a 4 px rounded data-end and a square end at the baseline.

    Rounding happens in data units, so mutation_aspect corrects for the axes' different
    x and y scales to keep the corners circular.
    """
    thickness = BAR_THICKNESS_IN * y_units_per_in
    corner = BAR_CORNER_IN * x_units_per_in
    bottom = row - thickness / 2
    axes.add_patch(
        FancyBboxPatch(
            (0, bottom),
            value,
            thickness,
            boxstyle=f"round,pad=0,rounding_size={corner}",
            mutation_aspect=y_units_per_in / x_units_per_in,
            facecolor=color,
            edgecolor="none",
        )
    )
    axes.add_patch(
        Rectangle((0, bottom), min(value, 2 * corner), thickness, facecolor=color, edgecolor="none")
    )


def draw_end_dot(axes: Axes, day: int, share: float, color: str) -> None:
    """Draws a ringed dot at a line's end and labels it with the final share."""
    axes.plot(
        [day],
        [share],
        marker="o",
        markersize=MARKER_SIZE_PT,
        markerfacecolor=color,
        markeredgecolor=SURFACE,
        markeredgewidth=MARKER_RING_PT,
        clip_on=False,
        zorder=3,
    )
    axes.annotate(
        f"{share:.0%}",
        xy=(day, share),
        xytext=(9, 0),
        textcoords="offset points",
        va="center",
        color=TEXT_PRIMARY,
        fontsize=LABEL_SIZE_PT,
        annotation_clip=False,
    )


def save_figure(figure: Figure, path: Path) -> None:
    """Saves a figure as a PNG with the chart surface as its background."""
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=DPI, facecolor=SURFACE)
