"""OpenReef's restrained macOS-inspired styling and icon helpers."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

ASSET_FOLDER = Path(__file__).resolve().parent / "assets"
PRIMARY_ACCENT = "#8e8e93"
RUNNING_ACCENT = "#d1d1d6"
WARNING_ACCENT = "#ff6961"
WORKFLOW_LEVEL_COLORS = (
    "#b14a45",
    "#da867a",
    "#b6cdad",
    "#5d8357",
    "#5483bb",
    "#2a52ce",
)


@lru_cache(maxsize=32)
def bootstrap_icon(name: str, color: str = "#ffffff", size: int = 32) -> QIcon:
    """Render a bundled Bootstrap SVG using the requested theme color."""
    source = ASSET_FOLDER / f"bi-{name}.svg"
    try:
        svg = source.read_text(encoding="utf-8").replace("currentColor", color)
    except OSError:
        return QIcon()
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def application_stylesheet(dark: bool) -> str:
    """Return OpenReef's neutral macOS-inspired theme and light counterpart."""
    if dark:
        body = "#111315"
        surface = "#1b1d1f"
        raised = "#222528"
        step_surface = "#17191b"
        selected_step = "#24272a"
        text = "#f2f2f7"
        muted = "#a8a8ad"
        border = "#303337"
        input_bg = "#17191b"
        input_text = "#f2f2f7"
        terminal = "#0b0d0e"
        scroll_handle = "#4b4e52"
        button_bg = "#202326"
        button_hover = "#2b2e31"
        button_pressed = "#181a1c"
        button_text = "#f2f2f7"
        disabled_text = "#6e7074"
        status_bg = "#151719"
        card_background = (
            "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "stop:0 #1e2023, stop:1 #181a1c)"
        )
    else:
        body = "#f2f2f7"
        surface = "#ffffff"
        raised = "#e5e5ea"
        step_surface = "#f7f7f9"
        text = "#1c1c1e"
        muted = "#6e6e73"
        border = "#d1d1d6"
        input_bg = "#ffffff"
        input_text = "#1c1c1e"
        terminal = "#f7f7f9"
        scroll_handle = "#aeaeb2"
        button_bg = "#e5e5ea"
        button_hover = "#d8d8dc"
        button_pressed = "#c7c7cc"
        button_text = "#1c1c1e"
        disabled_text = "#8e8e93"
        selected_step = "#e5e5ea"
        status_bg = "#ededf0"
        card_background = surface

    checkmark = (ASSET_FOLDER / "checkbox-check.svg").as_posix()
    level_1, level_2, level_3, level_4, level_5, level_6 = WORKFLOW_LEVEL_COLORS
    return f"""
* {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, sans-serif;
    font-size: 14px;
}}
QMainWindow, QWidget {{ background: {body}; color: {text}; }}
QLabel {{ background: transparent; }}
QStackedWidget, QStackedWidget > QWidget {{ background: transparent; }}
QFrame#appSidebar {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #1c1f22, stop:1 #141618);
    color: #f2f2f7;
    border-right: 1px solid #2a2d30;
}}
QLabel#trafficRed {{ background: #ff5f57; border-radius: 6px; }}
QLabel#trafficYellow {{ background: #febc2e; border-radius: 6px; }}
QLabel#trafficGreen {{ background: #28c840; border-radius: 6px; }}
QLabel#appTitle {{
    background: transparent;
    color: #f2f2f7;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 0.4px;
}}
QLabel#appCaption {{
    background: transparent;
    color: #8e8e93;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 1.2px;
}}
QLabel#sidebarLogo {{ background: transparent; border: 0; }}
QLabel#sidebarVersion {{ color: #77797d; font-size: 12px; font-weight: 500; padding: 8px; }}
QFrame#sidebarDivider {{ color: #303337; background: #303337; max-height: 1px; border: 0; }}
QLabel#sidebarSection {{
    color: #737377;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 0 10px 5px 10px;
}}
QPushButton#sidebarNav, QPushButton#sidebarLink {{
    background: transparent;
    color: #a8a8ad;
    border: 0;
    border-radius: 7px;
    padding: 10px 12px;
    text-align: left;
    font-size: 14px;
    font-weight: 500;
}}
QPushButton#sidebarNav:hover, QPushButton#sidebarLink:hover {{
    background: #25282b;
    color: #f2f2f7;
}}
QPushButton#sidebarNav:checked {{
    background: #303337;
    color: #ffffff;
    font-weight: 600;
}}
QMenuBar, QMenu, QStatusBar {{ background: #111315; color: #f2f2f7; }}
QMenuBar {{ border-bottom: 1px solid #292c2f; }}
QMenuBar::item {{ background: transparent; padding: 5px 9px; }}
QMenuBar::item:selected, QMenu::item:selected {{ background: #303030; }}
QStatusBar {{ border-top: 1px solid #292c2f; }}
QStackedWidget#workspaceStack {{ background: {body}; border: 0; }}

QGroupBox {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 12px;
    margin-top: 12px;
    padding: 14px 12px 12px 12px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 5px;
    color: {text};
}}
QFrame#collapsibleSection {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 10px;
}}
QToolButton#collapsibleHeader {{
    background: transparent;
    color: {text};
    border: 0;
    border-radius: 9px;
    padding: 7px 9px;
    min-height: 18px;
    font-weight: 650;
    text-align: left;
}}
QToolButton#collapsibleHeader:hover {{
    background: {button_hover};
    border: 0;
}}
QWidget#collapsibleContent {{ background: transparent; }}
QLabel#sectionSubheading {{
    color: {text};
    font-size: 11px;
    font-weight: 700;
    padding-top: 3px;
}}
QFrame#stageCard {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 8px;
}}
QFrame#stageCard[state="running"] {{ border: 1px solid #636366; }}
QFrame#stageCard[state="complete"], QFrame#stageCard[state="ready"] {{
    border: 1px solid #4a4a4d;
}}
QFrame#stageCard[state="failed"] {{ border: 1px solid {WARNING_ACCENT}; }}
QFrame#workflowGroup, QFrame#cropCheckpoint, QFrame#tilesetCheckpoint {{
    background: {card_background};
    border: 1px solid {border};
    border-radius: 12px;
}}
QFrame#workflowGroup[level="1"] {{ border: 2px solid {level_1}; }}
QFrame#cropCheckpoint[level="2"] {{ border: 2px solid {level_2}; }}
QFrame#workflowGroup[level="3"] {{ border: 2px solid {level_3}; }}
QFrame#workflowGroup[level="4"] {{ border: 2px solid {level_4}; }}
QFrame#workflowGroup[level="5"] {{ border: 2px solid {level_5}; }}
QFrame#tilesetCheckpoint[level="6"] {{ border: 2px solid {level_6}; }}
QFrame#workflowGroup[selected="true"] {{
    background: {raised};
    border-width: 3px;
}}
QFrame#workflowStep {{
    background: {step_surface};
    border: 1px solid {border};
    border-radius: 7px;
}}
QFrame#workflowStep[selected="true"] {{
    background: {selected_step};
    border: 1px solid #636366;
}}
QFrame#workflowStep[level="1"][selected="true"] {{ border-color: {level_1}; }}
QFrame#workflowStep[level="3"][selected="true"] {{ border-color: {level_3}; }}
QFrame#workflowStep[level="4"][selected="true"] {{ border-color: {level_4}; }}
QFrame#workflowStep[level="5"][selected="true"] {{ border-color: {level_5}; }}
QGroupBox#settingsCard[level="1"] {{ border-top: 2px solid {level_1}; }}
QGroupBox#settingsCard[level="3"] {{ border-top: 2px solid {level_3}; }}
QGroupBox#settingsCard[level="4"] {{ border-top: 2px solid {level_4}; }}
QGroupBox#settingsCard[level="5"] {{ border-top: 2px solid {level_5}; }}
QGroupBox#globalOptions {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 8px;
}}
QGroupBox#sourcePanel {{ border-top: 1px solid {border}; }}
QGroupBox#preparationPanel {{ border-top: 1px solid {border}; }}
QFrame#optionsDivider {{ color: {border}; }}
QLabel#globalOptionsTitle {{ font-size: 15px; font-weight: 700; }}
QLabel#compactTarget {{
    color: {text};
    background: {raised};
    border-radius: 8px;
    padding: 2px 7px;
    font-size: 10px;
    font-weight: 700;
}}
QLabel#workflowGroupSubtitle {{ color: {muted}; font-size: 11px; }}
QLabel#stageNumberBadge {{
    color: #16181a;
    background: #f1f1f3;
    border: 0;
    border-radius: 14px;
    font-size: 14px;
    font-weight: 700;
}}
QLabel#stageNumberBadge[level="1"] {{ background: {level_1}; color: #ffffff; }}
QLabel#stageNumberBadge[level="2"] {{ background: {level_2}; color: #191919; }}
QLabel#stageNumberBadge[level="3"] {{ background: {level_3}; color: #191919; }}
QLabel#stageNumberBadge[level="4"] {{ background: {level_4}; color: #ffffff; }}
QLabel#stageNumberBadge[level="5"] {{ background: {level_5}; color: #ffffff; }}
QLabel#stageNumberBadge[level="6"] {{ background: {level_6}; color: #ffffff; }}
QLabel#settingsExplanation {{
    color: {muted};
    font-size: 14px;
    line-height: 1.35;
    padding: 12px;
}}
QLabel#statusBadge {{
    color: {muted};
    background: {status_bg};
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 2px 7px;
    font-size: 10px;
    font-weight: 700;
}}
QLabel#statusBadge[state="complete"] {{ color: {text}; border-color: #57575b; }}
QLabel#statusBadge[state="running"] {{
    color: #ffffff;
    background: #48484a;
    border-color: #737377;
}}
QLabel#statusBadge[state="queued"] {{ color: {muted}; border-color: #505050; }}
QLabel#statusBadge[state="attention"] {{ color: #ffd60a; border-color: #8a6d00; }}
QLabel#statusBadge[state="failed"] {{ color: #ff8a8a; border-color: {WARNING_ACCENT}; }}
QPushButton, QToolButton {{
    background: {button_bg};
    color: {button_text};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 8px 12px;
    min-height: 18px;
}}
QPushButton:hover, QToolButton:hover {{ background: {button_hover}; border-color: #5a5a5a; }}
QPushButton:pressed, QToolButton:pressed {{ background: {button_pressed}; }}
QPushButton:disabled, QToolButton:disabled {{ color: {disabled_text}; background: {surface}; }}
QPushButton#primaryButton {{
    background: #f5f5f7;
    border-color: #ffffff;
    color: #151719;
    font-weight: 700;
}}
QPushButton#primaryButton:hover {{ background: #ffffff; border-color: #ffffff; }}
QPushButton#primaryButton:pressed {{ background: #d8d8dc; border-color: #d8d8dc; }}
QWidget#viewerControls QPushButton {{
    border-radius: 7px;
    padding: 4px 7px;
    min-height: 16px;
}}
QPushButton#navbarButton {{
    background: transparent;
    border: 1px solid #424242;
    color: #ffffff;
    padding: 7px 11px;
}}
QPushButton#navbarButton:hover {{ background: #303030; border-color: #5a5a5a; }}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background: {input_bg};
    color: {input_text};
    selection-background-color: #636366;
    selection-color: #ffffff;
    border: 1px solid {border};
    border-radius: 8px;
    padding: 7px 9px;
    min-height: 18px;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid #737377;
}}
QComboBox QAbstractItemView {{
    background: {surface};
    color: {text};
    border: 1px solid {border};
    selection-background-color: #636366;
    selection-color: #ffffff;
    outline: 0;
}}
QCheckBox {{ spacing: 7px; background: transparent; }}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    background: {input_bg};
    border: 1px solid #5a5a5a;
    border-radius: 3px;
}}
QCheckBox::indicator:checked {{
    background: #ffffff;
    border-color: #ffffff;
    image: url({checkmark});
}}
QCheckBox#workflowStageCheckbox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid #f2f2f7;
    border-radius: 1px;
}}
QCheckBox#workflowStageCheckbox::indicator:checked {{
    background: #ffffff;
    border-color: #111111;
    image: url({checkmark});
}}
QCheckBox::indicator:disabled {{ background: {raised}; border-color: {border}; }}

QTextEdit, QPlainTextEdit {{
    background: {terminal};
    color: {text};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 8px;
    font-family: Menlo, Monaco, Consolas, monospace;
}}
QPlainTextEdit#processingTerminal {{ font-size: 11px; }}
QScrollArea {{ border: 0; background: transparent; }}
QScrollArea#workspacePageScroll {{ background: {body}; }}
QScrollArea#viewerControlsScroll {{ background: {body}; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: {raised}; width: 11px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {scroll_handle}; border-radius: 5px; min-height: 28px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QSlider::groove:horizontal {{ height: 5px; background: {border}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    width: 16px;
    margin: -6px 0;
    border-radius: 8px;
    background: #8e8e93;
    border: 1px solid #aeaeb2;
}}
QProgressBar {{
    background: {raised};
    color: {text};
    border: 0;
    border-radius: 4px;
    text-align: center;
    min-height: 7px;
}}
QProgressBar::chunk {{ background: #f2f2f7; border-radius: 4px; }}
QProgressBar[state="running"]::chunk {{ background: {RUNNING_ACCENT}; }}
QProgressBar[level="1"]::chunk {{ background: {level_1}; }}
QProgressBar[level="3"]::chunk {{ background: {level_3}; }}
QProgressBar[level="4"]::chunk {{ background: {level_4}; }}
QProgressBar[level="5"]::chunk {{ background: {level_5}; }}
QProgressBar#workflowOverallProgress::chunk {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {level_1}, stop:0.18 {level_2}, stop:0.38 {level_3},
        stop:0.58 {level_4}, stop:0.78 {level_5}, stop:1 {level_6}
    );
}}

QLabel#heading {{ font-size: 21px; font-weight: 700; color: {text}; }}
QLabel#subtitle {{ color: {muted}; margin-bottom: 4px; }}
QLabel#pageTitle {{ font-size: 25px; font-weight: 700; color: {text}; }}
QLabel#pageSubtitle, QLabel#datasetSummary, QLabel#terminalHint, QLabel#stageOutput {{
    color: {muted};
}}
QLabel#fieldLabel, QLabel#stageNumber {{
    color: {muted};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.8px;
}}
QLabel#flowArrow, QLabel#workflowArrow {{ color: #8a8d91; font-size: 22px; }}
QLabel#workflowArrow[level="2"] {{ color: {level_2}; }}
QLabel#workflowArrow[level="3"] {{ color: {level_3}; }}
QLabel#workflowArrow[level="4"] {{ color: {level_4}; }}
QLabel#workflowArrow[level="5"] {{ color: {level_5}; }}
QLabel#workflowArrow[level="6"] {{ color: {level_6}; }}
QLabel#currentStage {{ color: {muted}; font-weight: 600; }}
QLabel#mediaPreview {{ background: {surface}; border: 1px solid {border}; border-radius: 8px; }}
QFrame#projectCard {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 12px;
}}
QFrame#measurementToolbar {{
    background: rgba(23, 25, 27, 232);
    border: 1px solid #414449;
    border-radius: 11px;
}}
QLabel#measurementScaleStatus {{
    color: #b8bbc0;
    font-size: 10px;
    font-weight: 650;
}}
QLabel#measurementHint {{ color: #a8a8ad; font-size: 10px; }}
QPushButton#measurementToolButton, QPushButton#measurementClearButton {{
    background: #25282b;
    color: #f2f2f7;
    border: 1px solid #44474b;
    border-radius: 7px;
    padding: 5px 8px;
    min-height: 16px;
    font-size: 11px;
}}
QPushButton#measurementToolButton:hover, QPushButton#measurementClearButton:hover {{
    background: #303438;
}}
QPushButton#measurementToolButton:checked {{
    background: #f2f2f7;
    color: #17191b;
    border-color: #ffffff;
}}
QPushButton#measurementClearButton {{ color: #b8bbc0; }}
QLabel#projectName {{ font-size: 18px; font-weight: 650; color: {text}; }}
QLabel#markerTagDetectedStatus {{
    color: {text};
    background: {status_bg};
    border: 1px solid {border};
    border-radius: 9px;
    padding: 12px 13px;
    font-size: 18px;
    font-weight: 700;
}}
QLabel#markerTagDetectedStatus[detected="true"] {{
    border-color: #6e6e73;
}}
QLabel#markerTagScaleStatus {{
    color: {muted};
    padding: 2px 4px;
    font-size: 12px;
}}
QToolTip {{
    background: #303030;
    color: #ececec;
    border: 1px solid #505050;
    padding: 5px;
}}
"""


def icon_color(dark: bool, selected: bool = False) -> str:
    if selected:
        return PRIMARY_ACCENT
    return "#a1a1a6" if dark else "#6e6e73"


def viewport_background(dark: bool) -> tuple[str, str]:
    return ("#2c2c2e", "#161618") if dark else ("#f2f2f7", "#d1d1d6")


def transparent_color() -> QColor:
    """Small convenience for callers creating transparent branded pixmaps."""
    return QColor(0, 0, 0, 0)
