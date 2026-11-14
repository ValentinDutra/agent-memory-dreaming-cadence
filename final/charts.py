"""Small hand-written SVG charts for P7b, standard library only."""

import math
from html import escape

COLORS = {
    "never": "#7f7f7f",
    "every-50": "#c6dbef",
    "every-20": "#9ecae1",
    "every-10": "#6baed6",
    "every-5": "#3182bd",
    "every-1": "#08519c",
    "triggered-phrases-any": "#d95f02",
}
FONT = 'font-family="Helvetica, Arial, sans-serif"'


def nice_ticks(low: float, high: float, count: int = 5) -> list[float]:
    raw_step = (high - low) / count or 1
    magnitude = 10 ** math.floor(math.log10(raw_step))
    step = next(multiple * magnitude for multiple in (1, 2, 2.5, 5, 10) if multiple * magnitude >= raw_step)
    first = math.ceil(low / step - 1e-9) * step
    return [first + index * step for index in range(int((high - first) / step + 1e-9) + 1)]


def label(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".")


def text(x: float, y: float, content: str, size: int = 12, anchor: str = "middle", rotate: bool = False, weight: str = "normal") -> str:
    transform = f' transform="rotate(-90 {x:.1f} {y:.1f})"' if rotate else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" {FONT}{transform}>{escape(content)}</text>'


def line(x1: float, y1: float, x2: float, y2: float, color: str = "#000", width: float = 1, dash: str = "") -> str:
    dash_attribute = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="{width}"{dash_attribute}/>'


def document(width: int, height: int, parts: list[str]) -> str:
    body = "\n".join(parts)
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n<rect width="100%" height="100%" fill="white"/>\n{body}\n</svg>\n'


class Frame:
    """A plot area with linear x and y scales, its grid, ticks and axis titles."""

    def __init__(self, left: float, top: float, width: float, height: float, x_range: tuple[float, float], y_range: tuple[float, float]):
        self.left, self.top, self.width, self.height = left, top, width, height
        self.x_range, self.y_range = x_range, y_range

    def x(self, value: float) -> float:
        low, high = self.x_range
        return self.left + (value - low) / (high - low) * self.width

    def y(self, value: float) -> float:
        low, high = self.y_range
        return self.top + self.height - (value - low) / (high - low) * self.height

    def axes(self, title: str, x_title: str, y_title: str, x_ticks: list[float] | None, y_ticks: list[float]) -> list[str]:
        bottom = self.top + self.height
        parts = [text(self.left + self.width / 2, self.top - 10, title, size=14, weight="bold")]
        for value in y_ticks:
            parts.append(line(self.left, self.y(value), self.left + self.width, self.y(value), "#e5e5e5"))
            parts.append(text(self.left - 6, self.y(value) + 4, label(value), size=11, anchor="end"))
        for value in x_ticks or []:
            parts.append(line(self.x(value), self.top, self.x(value), bottom, "#e5e5e5"))
            parts.append(text(self.x(value), bottom + 16, label(value), size=11))
        parts.append(line(self.left, bottom, self.left + self.width, bottom))
        parts.append(line(self.left, self.top, self.left, bottom))
        parts.append(text(self.left + self.width / 2, bottom + 36, x_title))
        parts.append(text(self.left - 44, self.top + self.height / 2, y_title, rotate=True))
        return parts


def legend(left: float, top: float, entries: list[tuple[str, str, str]]) -> list[str]:
    """entries: (label, color, shape) with shape "circle", "diamond", "line" or "dashed"."""
    parts = []
    for index, (name, color, shape) in enumerate(entries):
        y = top + index * 18
        if shape in ("line", "dashed"):
            parts.append(line(left, y, left + 16, y, color, 2, "5,3" if shape == "dashed" else ""))
        else:
            parts.append(marker(left + 8, y, color, shape))
        parts.append(text(left + 22, y + 4, name, size=11, anchor="start"))
    return parts


def marker(x: float, y: float, color: str, shape: str) -> str:
    if shape == "diamond":
        return f'<polygon points="{x:.1f},{y - 7:.1f} {x + 7:.1f},{y:.1f} {x:.1f},{y + 7:.1f} {x - 7:.1f},{y:.1f}" fill="{color}" stroke="#000" stroke-width="0.8"/>'
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{color}" stroke="#000" stroke-width="0.8"/>'


def cost_accuracy_chart(panels: list[tuple[str, dict]], connected: tuple[str, ...], apart: str, x_title: str, y_title: str) -> str:
    """One panel per count. Each panel maps policy -> ((x, x_low, x_high), (y, y_low, y_high)), y in percent.

    The policies in `connected` are joined in that order; `apart` is drawn as a diamond, not joined.
    """
    points = [point for _, panel in panels for point in panel.values()]
    x_high = max(x_interval[2] for x_interval, _ in points) * 1.05
    y_low = math.floor(min(y_interval[1] for _, y_interval in points) / 10) * 10
    panel_width, panel_height, margin = 380, 330, 70
    width, height = margin + len(panels) * (panel_width + margin) + 150, panel_height + 110
    parts = []
    for index, (title, panel) in enumerate(panels):
        frame = Frame(margin + index * (panel_width + margin), 40, panel_width, panel_height, (0, x_high), (y_low, 100))
        parts += frame.axes(title, x_title, y_title, nice_ticks(0, x_high), nice_ticks(y_low, 100))
        joined = [panel[policy] for policy in connected if policy in panel]
        path = " ".join(f"{frame.x(x[0]):.1f},{frame.y(y[0]):.1f}" for x, y in joined)
        parts.append(f'<polyline points="{path}" fill="none" stroke="#3182bd" stroke-width="1.5"/>')
        for policy, (x, y) in panel.items():
            parts.append(line(frame.x(x[1]), frame.y(y[0]), frame.x(x[2]), frame.y(y[0]), "#444"))
            parts.append(line(frame.x(x[0]), frame.y(y[1]), frame.x(x[0]), frame.y(y[2]), "#444"))
            parts.append(marker(frame.x(x[0]), frame.y(y[0]), COLORS[policy], "diamond" if policy == apart else "circle"))
    entries = [(policy, COLORS[policy], "circle") for policy in connected] + [(apart, COLORS[apart], "diamond")]
    parts += legend(width - 160, 60, entries)
    return document(width, height, parts)


def grouped_bar_chart(title: str, groups: list[str], series: list[str], values: dict, y_title: str) -> str:
    """values: (series, group) -> (mean, low, high) in percent, or missing. One cluster of bars per group, with whiskers."""
    bar_width, gap, margin = 11, 26, 70
    cluster = len(series) * bar_width
    width = margin + len(groups) * (cluster + gap) + 190
    frame = Frame(margin, 40, len(groups) * (cluster + gap), 300, (0, 1), (0, 100))
    parts = frame.axes(title, "", y_title, None, nice_ticks(0, 100))
    for group_index, group in enumerate(groups):
        cluster_left = margin + gap / 2 + group_index * (cluster + gap)
        parts.append(text(cluster_left + cluster / 2, frame.top + frame.height + 16, group, size=11))
        for series_index, name in enumerate(series):
            if (name, group) not in values:
                continue
            mean, low, high = values[name, group]
            x = cluster_left + series_index * bar_width
            parts.append(f'<rect x="{x:.1f}" y="{frame.y(mean):.1f}" width="{bar_width - 1}" height="{frame.y(0) - frame.y(mean):.1f}" fill="{COLORS[name]}"/>')
            parts.append(line(x + bar_width / 2, frame.y(low), x + bar_width / 2, frame.y(high), "#000"))
    parts += legend(width - 175, 60, [(name, COLORS[name], "circle") for name in series])
    return document(width, 400, parts)


def stretch_chart(title: str, stretches: list[str], series: dict[str, list[float]], y_title: str) -> str:
    """series: label -> one value per stretch (points of accuracy). Solid lines for official, dashed for the rest."""
    every_value = [value for values in series.values() for value in values]
    y_low, y_high = min(0, math.floor(min(every_value))), math.ceil(max(every_value)) + 1
    frame = Frame(70, 40, 360, 260, (-0.5, len(stretches) - 0.5), (y_low, y_high))
    parts = frame.axes(title, "", y_title, None, nice_ticks(y_low, y_high))
    for index, stretch in enumerate(stretches):
        parts.append(text(frame.x(index), frame.top + frame.height + 16, stretch, size=11))
    palette = ("#08519c", "#d95f02", "#1b9e77", "#7570b3")
    entries = []
    for index, (name, values) in enumerate(series.items()):
        color, dash = palette[index // 2 % len(palette)], "" if index % 2 == 0 else "5,3"
        for position in range(len(values) - 1):
            parts.append(line(frame.x(position), frame.y(values[position]), frame.x(position + 1), frame.y(values[position + 1]), color, 2, dash))
        for position, value in enumerate(values):
            parts.append(marker(frame.x(position), frame.y(value), color, "circle"))
        entries.append((name, color, "dashed" if dash else "line"))
    parts += legend(450, 60, entries)
    return document(720, 360, parts)
