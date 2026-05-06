"""State models shared by the MVC-style app modules."""

from dataclasses import dataclass, field
from queue import Queue


@dataclass
class SettingsState:
    """User-adjustable app settings."""

    music_vol: float = 1.0
    sfx_vol: float = 1.0


@dataclass
class GameState:
    """Runtime state for one typing match."""

    articles: list = field(default_factory=list)
    current_article_idx: int = 0
    current_index: int = 0
    mistakes: int = 0
    max_mistakes: int = 3
    bullets_loaded: int = 0
    chambers: list = field(default_factory=lambda: [False] * 6)
    game_active: bool = False
    is_frozen: bool = False
    is_resting: bool = False
    is_pre_game: bool = False
    pre_game_time: int = 5
    termination_time: int = 20
    can_exit: bool = False
    in_menu: bool = True
    in_transition: bool = False
    loading_progress: int = 0
    scroll_job: object = None
    roulette_revealed: bool = False
    time_left: int = 240
    timer_job: object = None
    current_bar_width: int = 40
    player_id: int = 1
    match_status: str = "Lost"
    leaderboard_saved: bool = False


@dataclass
class MenuState:
    """State owned by menus and overlay widgets."""

    in_ingame_menu: bool = False
    ingame_overlay_photo: object = None
    in_options_menu: bool = False
    options_previous_state: str = None
    music_scale_widget: object = None
    sfx_scale_widget: object = None


@dataclass
class MultiplayerState:
    """Socket lobby and multiplayer match state."""

    multiplayer_mode: bool = False
    is_host: bool = False
    player_name: str = "Player"
    host_socket: object = None
    server_socket: object = None
    client_threads: list = field(default_factory=list)
    connected_clients: list = field(default_factory=list)
    network_queue: Queue = field(default_factory=Queue)
    pending_article_indices: list = None
    multiplayer_status_text_id: object = None
    match_finished: bool = False


@dataclass
class StatsState:
    """Typing performance stats for the active match."""

    total_chars_typed: int = 0
    total_mistakes: int = 0
    total_typing_time: int = 0
    article_chars: int = 0
    article_mistakes: int = 0
    wpm_list: list = field(default_factory=list)
    acc_list: list = field(default_factory=list)


@dataclass
class LayoutState:
    """Screen dimensions and computed Canvas coordinates."""

    screen_w: int = 0
    screen_h: int = 0
    center_x: int = 0
    base_y: int = 0
    monitor_w: int = 0
    monitor_h: int = 0
    inner_screen_w: int = 0
    inner_screen_h: int = 0
    left_edge: int = 0
    first_box_cx: int = 0
    revolver_cx: int = 0
    clock_text_x: int = 0
    clock_text_y: int = 0
    clock_font_size: int = 20
    rank_font_size: int = 20


@dataclass
class AssetStore:
    """Loaded image assets kept alive for Tkinter."""

    bg_photo: object = None
    dead_bg_photo: object = None
    table_photo: object = None
    monitor_photo: object = None
    term_monitor_photo: object = None
    menu_monitor_photo: object = None
    kb_photo: object = None
    clock_photo: object = None
    rank_photo: object = None
    img_blood: object = None
    black_screen: object = None
    fade_photo: object = None
    blood_photo: object = None
    clock_text_photo: object = None
    rank_text_photo: object = None


@dataclass
class WidgetStore:
    """Tkinter root, canvas, and embedded text widgets."""

    root: object = None
    main_canvas: object = None
    text_display: object = None
    screen_text: object = None
    menu_screen_text: object = None
    text_window_id: object = None
    screen_text_window_id: object = None
    menu_screen_text_window_id: object = None
