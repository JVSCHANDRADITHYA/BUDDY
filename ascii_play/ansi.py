"""
ascii_play.ansi
~~~~~~~~~~~~~~~
ANSI/VT100 escape sequence helpers.
All functions return strings — callers write them to stdout.
"""

def cursor_hide()  -> str: return "\033[?25l"
def cursor_show()  -> str: return "\033[?25h"
def clear_screen() -> str: return "\033[2J\033[H"
def move_home()    -> str: return "\033[H"
def alt_screen()   -> str: return "\033[?1049h"
def normal_screen()-> str: return "\033[?1049l"
def reset()        -> str: return "\033[0m"

def rgb_fg(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"

def rgb_bg(r: int, g: int, b: int) -> str:
    return f"\033[48;2;{r};{g};{b}m"

def move_to(row: int, col: int = 0) -> str:
    return f"\033[{row};{col}H"
