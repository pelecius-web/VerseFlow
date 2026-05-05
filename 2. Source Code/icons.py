"""icons.py — VerseFlow Icon Utility

Provides high-fidelity SVG rendering for application icons to ensure
cross-platform consistency and High-DPI support.
"""

import logging

from PyQt6.QtCore import QByteArray, Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer

def _render_svg(svg_str: str, size: int) -> QIcon:
    try:
        renderer = QSvgRenderer(QByteArray(svg_str.encode('utf-8')))
        if not renderer.isValid():
            return QIcon()
            
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        
        return QIcon(pixmap)
    except Exception as e:
        logging.getLogger("VerseFlow").error("Failed to render SVG icon: %s", e)
        return QIcon()

def get_trash_icon(color: str = "#e05c4b", size: int = 24) -> QIcon:
    """
    Generates a QIcon from an embedded SVG trash can.
    
    Args:
        color: Stroke color for the icon (default matches destructive red theme).
        size: Pixel size for the rendered pixmap.
    """
    svg_template = f'''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" 
         stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <polyline points="3 6 5 6 21 6"></polyline>
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"></path>
      <line x1="10" y1="11" x2="10" y2="17"></line>
      <line x1="14" y1="11" x2="14" y2="17"></line>
      <path d="M8 6h8v2H8z"></path>
    </svg>
    '''
    return _render_svg(svg_template, size)

def get_new_icon(color: str = "#c8a03c", size: int = 16) -> QIcon:
    svg_template = f'''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" 
         stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
      <polyline points="14 2 14 8 20 8"></polyline>
      <line x1="12" y1="18" x2="12" y2="12"></line>
      <line x1="9" y1="15" x2="15" y2="15"></line>
    </svg>
    '''
    return _render_svg(svg_template, size)

def get_open_icon(color: str = "#c8a03c", size: int = 16) -> QIcon:
    svg_template = f'''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" 
         stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
    </svg>
    '''
    return _render_svg(svg_template, size)

def get_save_icon(color: str = "#c8a03c", size: int = 16) -> QIcon:
    svg_template = f'''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" 
         stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
      <polyline points="17 21 17 13 7 13 7 21"></polyline>
      <polyline points="7 3 7 8 15 8"></polyline>
    </svg>
    '''
    return _render_svg(svg_template, size)

def get_save_as_icon(color: str = "#c8a03c", size: int = 16) -> QIcon:
    svg_template = f'''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" 
         stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
      <polyline points="17 21 17 13 7 13 7 21"></polyline>
      <polyline points="7 3 7 8 15 8"></polyline>
      <circle cx="12" cy="17" r="1.5" fill="{color}"></circle>
    </svg>
    '''
    return _render_svg(svg_template, size)

def get_metadata_icon(color: str = "#c8a03c", size: int = 16) -> QIcon:
    svg_template = f'''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" 
         stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <line x1="4" y1="21" x2="4" y2="14"></line>
      <line x1="4" y1="10" x2="4" y2="3"></line>
      <line x1="12" y1="21" x2="12" y2="12"></line>
      <line x1="12" y1="8" x2="12" y2="3"></line>
      <line x1="20" y1="21" x2="20" y2="16"></line>
      <line x1="20" y1="12" x2="20" y2="3"></line>
      <line x1="1" y1="14" x2="7" y2="14"></line>
      <line x1="9" y1="8" x2="15" y2="8"></line>
      <line x1="17" y1="16" x2="23" y2="16"></line>
    </svg>
    '''
    return _render_svg(svg_template, size)

def get_arrow_right_icon(color: str = "#c8a03c", size: int = 24) -> QIcon:
    svg_template = f'''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" 
         stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <line x1="5" y1="12" x2="19" y2="12"></line>
      <polyline points="12 5 19 12 12 19"></polyline>
    </svg>
    '''
    return _render_svg(svg_template, size)

def get_arrow_up_icon(color: str = "#c8a03c", size: int = 24) -> QIcon:
    svg_template = f'''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" 
         stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <line x1="12" y1="19" x2="12" y2="5"></line>
      <polyline points="5 12 12 5 19 12"></polyline>
    </svg>
    '''
    return _render_svg(svg_template, size)

def get_arrow_down_icon(color: str = "#c8a03c", size: int = 24) -> QIcon:
    svg_template = f'''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" 
         stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <line x1="12" y1="5" x2="12" y2="19"></line>
      <polyline points="19 12 12 19 5 12"></polyline>
    </svg>
    '''
    return _render_svg(svg_template, size)

def get_close_icon(color: str = "#ffd966", size: int = 24) -> QIcon:
    svg_template = f'''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" 
         stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
      <line x1="18" y1="6" x2="6" y2="18"></line>
      <line x1="6" y1="6" x2="18" y2="18"></line>
    </svg>
    '''
    return _render_svg(svg_template, size)

def get_play_icon(color: str = "#c8a03c", size: int = 24) -> QIcon:
    svg_template = f'''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" 
         stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <polygon points="5 3 19 12 5 21 5 3"></polygon>
    </svg>
    '''
    return _render_svg(svg_template, size)

def get_stop_icon(color: str = "#e05c4b", size: int = 24) -> QIcon:
    svg_template = f'''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" 
         stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <rect x="6" y="6" width="12" height="12"></rect>
    </svg>
    '''
    return _render_svg(svg_template, size)

def get_return_icon(color: str = "#c8a03c", size: int = 16) -> QIcon:
    svg_template = f'''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" 
         stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <polyline points="9 18 15 12 9 6"></polyline>
    </svg>
    '''
    return _render_svg(svg_template, size)

def get_queue_icon(color: str = "#4caf7d", size: int = 20) -> QIcon:
    """Plus icon for adding to queue (green)."""
    svg_template = f'''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" 
         stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
      <line x1="12" y1="5" x2="12" y2="19"></line>
      <line x1="5" y1="12" x2="19" y2="12"></line>
    </svg>
    '''
    return _render_svg(svg_template, size)

def get_playlist_icon(color: str = "#c8a03c", size: int = 20) -> QIcon:
    """List icon for adding to playlist (gold)."""
    svg_template = f'''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
         stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <line x1="8" y1="6" x2="21" y2="6"></line>
      <line x1="8" y1="12" x2="21" y2="12"></line>
      <line x1="8" y1="18" x2="21" y2="18"></line>
      <line x1="3" y1="6" x2="3.01" y2="6"></line>
      <line x1="3" y1="12" x2="3.01" y2="12"></line>
      <line x1="3" y1="18" x2="3.01" y2="18"></line>
    </svg>
    '''
    return _render_svg(svg_template, size)


def get_chevron_left_icon(color: str = "#c8a03c", size: int = 16) -> QIcon:
    """Chevron left icon for Back button."""
    svg_template = f'''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
         stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <polyline points="15 18 9 12 15 6"></polyline>
    </svg>
    '''
    return _render_svg(svg_template, size)


def get_folder_icon(color: str = "#4caf7d", size: int = 20) -> QIcon:
    """Folder icon for playlist queue groups."""
    svg_template = f'''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
         stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
    </svg>
    '''
    return _render_svg(svg_template, size)
