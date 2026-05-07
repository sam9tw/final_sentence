"""View layer for Final Sentence."""

import tkinter as tk
import tkinter.font as tkFont

from PIL import Image, ImageTk

from .image_tools import create_rotated_text_image
from .paths import image_path


class GameView:
    """Tkinter view helpers for menus, HUD, and scenes."""

    def __init__(
        self,
        game,
        menu,
        multiplayer,
        stats,
        layout,
        assets,
        widgets,
        settings,
        leaderboard,
        audio,
        callbacks,
        text_width,
        start_index,
        prefix_spaces,
        multiplayer_rules,
    ):
        # Store references needed by the view layer.
        self.game = game
        self.menu = menu
        self.multiplayer = multiplayer
        self.stats = stats
        self.layout = layout
        self.assets = assets
        self.widgets = widgets
        self.settings = settings
        self.leaderboard = leaderboard
        self.audio = audio
        self.callbacks = callbacks
        self.text_width = text_width
        self.start_index = start_index
        self.prefix_spaces = prefix_spaces
        self.multiplayer_rules = multiplayer_rules

    def build_root(self):
        # Create the main Tk window and base canvas.
        self.widgets.root = tk.Tk()
        self.widgets.root.title("Final Sentence")
        self.widgets.root.attributes("-fullscreen", True)
        self.widgets.root.update_idletasks()
        self.layout.screen_w = self.widgets.root.winfo_screenwidth()
        self.layout.screen_h = self.widgets.root.winfo_screenheight()
        self.layout.center_x = self.layout.screen_w // 2
        self.layout.base_y = int(self.layout.screen_h * 0.20)
        self.layout.monitor_w = int(self.layout.screen_w * 0.5)
        self.layout.monitor_h = int(self.layout.screen_h * 0.45)
        self.layout.inner_screen_w = int(self.layout.monitor_w * 0.35)
        self.layout.inner_screen_h = int(self.layout.monitor_h * 0.51)
        self.widgets.main_canvas = tk.Canvas(
            self.widgets.root,
            width=self.layout.screen_w,
            height=self.layout.screen_h,
            highlightthickness=0,
            bg="#111111",
            bd=0,
        )
        self.widgets.main_canvas.pack(fill=tk.BOTH, expand=True)

    def load_assets(self):
        # Load image assets and cache them for Tkinter.
        img_bg = Image.open(image_path("room.png")).resize((self.layout.screen_w, self.layout.screen_h))
        self.assets.bg_photo = ImageTk.PhotoImage(img_bg)
        table_h = int(self.layout.screen_h * 0.25)
        img_table = Image.open(image_path("table.png")).resize((self.layout.screen_w, table_h))
        self.assets.table_photo = ImageTk.PhotoImage(img_table)
        img_monitor = Image.open(image_path("screen.png")).resize((self.layout.monitor_w, self.layout.monitor_h))
        self.assets.monitor_photo = ImageTk.PhotoImage(img_monitor)

        orig_kb = Image.open(image_path("kb.png"))
        orig_kw, orig_kh = orig_kb.size
        kb_w = int(self.layout.screen_w * 0.35)
        kb_h = int(kb_w * (orig_kh / orig_kw))
        self.assets.kb_photo = ImageTk.PhotoImage(orig_kb.resize((kb_w, kb_h)))

        orig_clock = Image.open(image_path("clock.png"))
        orig_cw, orig_ch = orig_clock.size
        clock_w = int(self.layout.screen_w * 0.2)
        clock_h = int(clock_w * (orig_ch / orig_cw))
        self.assets.clock_photo = ImageTk.PhotoImage(orig_clock.resize((clock_w, clock_h)))

        orig_rank = Image.open(image_path("rank.png"))
        orig_rw, orig_rh = orig_rank.size
        rank_w = int(self.layout.screen_w * 0.15)
        rank_h = int(rank_w * (orig_rh / orig_rw))
        self.assets.rank_photo = ImageTk.PhotoImage(orig_rank.resize((rank_w, rank_h)))
        self.layout.rank_font_size = int(rank_h * 0.55)
        self.assets.rank_text_photo = create_rotated_text_image(
            str(self.game.player_id),
            self.layout.rank_font_size,
            "#1a1a1a",
            -10,
            font_file="timesbd.ttf",
        )

        orig_blood = Image.open(image_path("dead.png")).convert("RGB")
        self.assets.img_blood = orig_blood.resize((self.layout.screen_w, self.layout.screen_h))
        self.assets.dead_bg_photo = ImageTk.PhotoImage(self.assets.img_blood)
        self.assets.black_screen = Image.new("RGB", (self.layout.screen_w, self.layout.screen_h), (0, 0, 0))

    def bind_root_events(self):
        # Connect top-level Tk events to controller callbacks.
        self.widgets.root.bind("<Button-1>", self.callbacks["global_click"])
        self.widgets.root.bind("<Escape>", self.callbacks["global_escape"])

    def create_canvas_button(self, cx, cy, width, height, text_str, action, ui_tag="menu_btn"):
        # Create a Canvas-backed button with hover and click behavior.
        bg_id = self.widgets.main_canvas.create_rectangle(
            cx - width / 2,
            cy - height / 2,
            cx + width / 2,
            cy + height / 2,
            fill="#000000",
            outline="",
            tags=ui_tag,
        )
        txt_id = self.widgets.main_canvas.create_text(
            cx,
            cy,
            text=text_str,
            font=("Courier New", 35, "bold"),
            fill="#ffffff",
            tags=ui_tag,
        )

        def on_enter(_event):
            self.widgets.main_canvas.itemconfigure(bg_id, fill="#FF8C00")
            self.widgets.main_canvas.itemconfigure(txt_id, fill="#FFD000")

        def on_leave(_event):
            self.widgets.main_canvas.itemconfigure(bg_id, fill="#000000")
            self.widgets.main_canvas.itemconfigure(txt_id, fill="#ffffff")

        def on_click(_event):
            action()

        for item_id in (bg_id, txt_id):
            self.widgets.main_canvas.tag_bind(item_id, "<Enter>", on_enter)
            self.widgets.main_canvas.tag_bind(item_id, "<Leave>", on_leave)
            self.widgets.main_canvas.tag_bind(item_id, "<Button-1>", on_click)

    def draw_revolver(self, rotation_index=0):
        # Render the roulette cylinder HUD.
        self.widgets.main_canvas.delete("revolver")
        if not self.game.roulette_revealed:
            return
        cx = self.layout.revolver_cx
        cy = self.layout.base_y - 45
        self.widgets.main_canvas.create_oval(cx - 28, cy - 28, cx + 28, cy + 28, fill="#1a1a1a", outline="#0a0a0a", width=2, tags="revolver")
        self.widgets.main_canvas.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill="#0a0a0a", tags="revolver")
        import math

        for i in range(6):
            angle = math.radians(i * 60 - 90)
            bx = cx + 16 * math.cos(angle)
            by = cy + 16 * math.sin(angle)
            logical_index = (i - rotation_index) % 6
            loaded = self.game.chambers[logical_index]
            self.widgets.main_canvas.create_oval(bx - 6, by - 6, bx + 6, by + 6, fill="#050505", outline="#2a2a2a", tags="revolver")
            if loaded:
                self.widgets.main_canvas.create_oval(bx - 4, by - 4, bx + 4, by + 4, fill="#aa1111", outline="#ff4444", tags="revolver")

    def draw_lives(self):
        # Render mistake boxes beside the typing area.
        self.widgets.main_canvas.delete("lives")
        cy = self.layout.base_y - 45
        for i in range(self.game.max_mistakes):
            cx = self.layout.first_box_cx + (i * 40)
            if i < self.game.mistakes:
                bg_color = "#550000"
                outline_color = "#880000"
                char = "X"
            else:
                bg_color = "#111111"
                outline_color = "#5a4a36"
                char = ""
            self.widgets.main_canvas.create_rectangle(cx - 16, cy - 16, cx + 16, cy + 16, fill=bg_color, outline=outline_color, width=2, tags="lives")
            if char:
                self.widgets.main_canvas.create_text(cx, cy, text=char, fill="#ff4444", font=("Courier New", 18, "bold"), tags="lives")

    def draw_feedback_hud(self):
        # Render combo, judgement, and remote progress text.
        self.widgets.main_canvas.delete("feedback_hud")
        combo_color = "#ffd54a" if self.game.current_combo > 0 else "#8e8a80"
        self.widgets.main_canvas.create_text(
            self.layout.center_x,
            max(30, self.layout.base_y - 70),
            text=f"{self.game.last_judgement}   Combo x{self.game.current_combo}",
            font=("Courier New", 20, "bold"),
            fill=combo_color,
            tags="feedback_hud",
        )
        if self.multiplayer.multiplayer_mode and self.multiplayer.remote_progress:
            lines = [f"{name}: {percent:>5.1f}%" for name, percent in self.multiplayer.remote_progress.items()]
            self.widgets.main_canvas.create_text(
                self.layout.screen_w - 120,
                max(90, self.layout.base_y + 10),
                text="\n".join(lines),
                font=("Courier New", 14, "bold"),
                fill="#72d477",
                justify="right",
                tags="feedback_hud",
            )

    def update_clock_display(self):
        # Update the tilted desk clock text.
        mins = self.game.time_left // 60
        secs = self.game.time_left % 60
        time_str = f"{mins:02d}:{secs:02d}"
        self.widgets.main_canvas.delete("clock_text")
        self.assets.clock_text_photo = create_rotated_text_image(time_str, self.layout.clock_font_size, "#ffffff", 2, font_file="courbd.ttf")
        self.widgets.main_canvas.create_image(self.layout.clock_text_x, self.layout.clock_text_y, image=self.assets.clock_text_photo, anchor="center", tags="clock_text")

    def build_game_scene(self):
        # Build the in-game widgets and scene art.
        self.game.in_menu = False
        self.widgets.main_canvas.delete("menu_ui", "menu_btn", "options_ui", "multiplayer_ui", "lobby_ui", "leaderboard_ui")
        self.widgets.main_canvas.delete("all")
        overlay = Image.new("RGBA", (self.layout.screen_w, self.layout.screen_h), (0, 0, 0, 255))
        self.assets.fade_photo = ImageTk.PhotoImage(overlay)

        self.widgets.main_canvas.config(bg="#111111")
        if self.assets.bg_photo:
            self.widgets.main_canvas.create_image(0, 0, image=self.assets.bg_photo, anchor="nw", tags="bg")
        if self.assets.table_photo:
            self.widgets.main_canvas.create_image(0, self.layout.screen_h - int(self.layout.screen_h * 0.25), image=self.assets.table_photo, anchor="nw", tags="table")
        if self.assets.monitor_photo:
            self.widgets.main_canvas.create_image(self.layout.screen_w // 2, self.layout.screen_h - 150, image=self.assets.monitor_photo, anchor="s", tags="monitor")
        if self.assets.kb_photo:
            self.widgets.main_canvas.create_image(self.layout.screen_w // 2, self.layout.screen_h - 10, image=self.assets.kb_photo, anchor="s", tags="kb")
        self._create_clock_and_rank()
        self._create_typing_widgets()
        self.widgets.main_canvas.create_text(self.layout.center_x, self.layout.screen_h * 0.95, text="--點擊畫面任意位置離開--", font=("Courier New", 16, "bold"), fill="#ffffff", tags="exit_prompt", state="hidden")
        self.widgets.main_canvas.create_image(0, 0, image=self.assets.fade_photo, anchor="nw", tags="fade_overlay")
        self.widgets.text_display.bind("<Key>", self.callbacks["keypress"])
        self.widgets.root.bind("<FocusIn>", lambda _event: self.widgets.text_display.focus_set() if self.game.game_active else None)

    def _create_clock_and_rank(self):
        # Place the desk clock and rank plaque.
        if self.assets.clock_photo:
            cw, ch = Image.open(image_path("clock.png")).size
            clock_x = -int(self.layout.screen_w * 0.05) + 90
            clock_y = (self.layout.screen_h - int(self.layout.screen_h * 0.25)) - int(int(self.layout.screen_w * 0.2) * (ch / cw) * 0.5)
            self.widgets.main_canvas.create_image(clock_x, clock_y, image=self.assets.clock_photo, anchor="nw", tags="clock")
            self.layout.clock_text_x = clock_x + int(self.layout.screen_w * 0.2) * 0.52
            self.layout.clock_text_y = clock_y + int(int(self.layout.screen_w * 0.2) * (ch / cw)) * 0.52
            self.layout.clock_font_size = int(int(int(self.layout.screen_w * 0.2) * (ch / cw)) * 0.3)
        if self.assets.rank_photo:
            rw, rh = Image.open(image_path("rank.png")).size
            rank_w = int(self.layout.screen_w * 0.15)
            rank_h = int(rank_w * (rh / rw))
            rank_x = self.layout.screen_w - rank_w + int(rank_w * 0.09)
            rank_y = (self.layout.screen_h - int(self.layout.screen_h * 0.25)) - int(rank_h * 0.6)
            self.widgets.main_canvas.create_image(rank_x, rank_y, anchor="nw", image=self.assets.rank_photo, tags="rank")
            rank_text_x = rank_x + rank_w * 0.52
            rank_text_y = rank_y + rank_h * 0.52
            if self.assets.rank_text_photo:
                self.widgets.main_canvas.create_image(rank_text_x, rank_text_y, image=self.assets.rank_text_photo, anchor="center", tags="rank_text")

    def _create_typing_widgets(self):
        # Create typing text boxes and compute HUD anchors.
        self.widgets.text_display = tk.Text(
            self.widgets.main_canvas,
            font=("Courier New", 20, "bold"),
            bg="#161311",
            bd=0,
            highlightthickness=0,
            width=self.text_width,
            height=6,
            spacing1=2,
            spacing2=0,
            spacing3=2,
            padx=25,
            pady=10,
            insertbackground="#ffffff",
            insertwidth=4,
        )
        self.widgets.root.update_idletasks()
        tw = self.widgets.text_display.winfo_reqwidth()
        self.layout.left_edge = self.layout.center_x - (tw // 2)
        my_font = tkFont.Font(family="Courier New", size=20, weight="bold")
        char_width = my_font.measure("A")
        real_text_left_x = self.layout.left_edge + 25 + (self.start_index * char_width)
        self.layout.first_box_cx = real_text_left_x + 16
        self.layout.revolver_cx = real_text_left_x - 38
        self.widgets.text_window_id = self.widgets.main_canvas.create_window(self.layout.center_x, self.layout.base_y, window=self.widgets.text_display, anchor="n", state="hidden")
        self.widgets.text_display.tag_config("correct", foreground="#72d477")
        self.widgets.text_display.tag_config("pending", foreground="#A07431")
        self.widgets.text_display.tag_config("error", foreground="#ff4444")
        self.widgets.text_display.tag_config("wrong_bg", background="#770000")
        self.widgets.text_display.tag_config("current_line_bg", background="#423d3a")
        self.widgets.text_display.tag_config("loading_bar_bg", foreground="#222222")
        self.widgets.text_display.tag_config("loading_bar_fill", foreground="#d28c00")
        current_tags = self.widgets.text_display.bindtags()
        new_tags = tuple(tag for tag in current_tags if tag != "Text")
        self.widgets.text_display.bindtags(new_tags)

        self.widgets.screen_text = tk.Text(
            self.widgets.main_canvas,
            font=("Courier New", 8, "bold"),
            bg="#050505",
            fg="#72d477",
            bd=0,
            highlightthickness=0,
            padx=10,
            pady=10,
            state=tk.DISABLED,
        )
        self.widgets.screen_text.bindtags(new_tags)
        self.widgets.screen_text.tag_config("tag_won", background="#72d477", foreground="#000000")
        self.widgets.screen_text.tag_config("tag_dead", background="#ff4444", foreground="#000000")
        self.widgets.screen_text_window_id = self.widgets.main_canvas.create_window(
            self.layout.center_x,
            self.layout.screen_h - 150 - int(self.layout.monitor_h * 0.58),
            window=self.widgets.screen_text,
            anchor="center",
            width=self.layout.inner_screen_w,
            height=self.layout.inner_screen_h,
        )

    def show_main_menu(self):
        # Render the main menu scene and buttons.
        self.widgets.main_canvas.delete("all")
        self.widgets.main_canvas.config(bg="#000000")
        self.audio.play_music_loop()
        if self.assets.table_photo:
            self.widgets.main_canvas.create_image(0, self.layout.screen_h - int(self.layout.screen_h * 0.25), image=self.assets.table_photo, anchor="nw", tags="menu_ui")
        self._draw_menu_monitor()
        self._draw_menu_title()
        btn_width = 500
        btn_height = 80
        self.create_canvas_button(self.layout.screen_w * 0.25, self.layout.screen_h * 0.40, btn_width, btn_height, "Single Player", self.callbacks["single_player"], ui_tag="menu_btn")
        self.create_canvas_button(self.layout.screen_w * 0.25, self.layout.screen_h * 0.51, btn_width, btn_height, "Multiplayer", self.callbacks["show_multiplayer_menu"], ui_tag="menu_btn")
        self.create_canvas_button(self.layout.screen_w * 0.25, self.layout.screen_h * 0.62, btn_width, btn_height, "Missions", self.callbacks["show_missions"], ui_tag="menu_btn")
        self.create_canvas_button(self.layout.screen_w * 0.25, self.layout.screen_h * 0.73, btn_width, btn_height, "Leaderboard", self.callbacks["show_leaderboard"], ui_tag="menu_btn")
        self.create_canvas_button(self.layout.screen_w * 0.25, self.layout.screen_h * 0.84, btn_width, btn_height, "Options", lambda: self.callbacks["show_options"]("main"), ui_tag="menu_btn")
        self.create_canvas_button(self.layout.screen_w * 0.25, self.layout.screen_h * 0.92, btn_width, btn_height, "Exit", self.callbacks["exit_game"], ui_tag="menu_btn")

    def _draw_menu_monitor(self):
        # Draw the menu monitor and intro text.
        menu_scale = 2
        menu_m_w = int(self.layout.monitor_w * menu_scale)
        menu_m_h = int(self.layout.monitor_h * menu_scale)
        img_monitor_menu = Image.open(image_path("screen.png")).resize((menu_m_w, menu_m_h))
        self.assets.menu_monitor_photo = ImageTk.PhotoImage(img_monitor_menu)
        menu_monitor_x = self.layout.screen_w * 0.72
        self.widgets.main_canvas.create_image(menu_monitor_x, self.layout.screen_h + 10, image=self.assets.menu_monitor_photo, anchor="s", tags="menu_ui")
        self.widgets.menu_screen_text = tk.Text(self.widgets.main_canvas, font=("Courier New", 28, "bold"), bg="#050505", fg="#72d477", bd=0, highlightthickness=0, padx=10, pady=10, state=tk.NORMAL)
        menu_tags = self.widgets.menu_screen_text.bindtags()
        self.widgets.menu_screen_text.bindtags(tuple(tag for tag in menu_tags if tag != "Text"))
        self.widgets.menu_screen_text.insert(tk.END, ">>> TYPE AS FAST AS YOU CAN!\n\n\n>>> Or\n\n\n>>> You will DIE!!!\n\n\n>>> Good Luck!!!")
        self.widgets.menu_screen_text.config(state=tk.DISABLED)
        m_inner_w = int(self.layout.inner_screen_w * menu_scale)
        m_inner_h = int(self.layout.inner_screen_h * menu_scale)
        menu_screen_text_y = (self.layout.screen_h + 10) - int(menu_m_h * 0.58)
        self.widgets.menu_screen_text_window_id = self.widgets.main_canvas.create_window(menu_monitor_x, menu_screen_text_y, window=self.widgets.menu_screen_text, anchor="center", width=m_inner_w, height=m_inner_h, state="hidden")

    def _draw_menu_title(self):
        # Draw the stylized game title on the menu.
        title_font = tkFont.Font(family="Courier New", size=70, weight="bold")
        char_w = title_font.measure("A")
        char_h = title_font.metrics("linespace")
        start_x = (self.layout.screen_w * 0.25) - (14 * char_w) / 2
        title_y = self.layout.screen_h * 0.25
        self.widgets.main_canvas.create_rectangle(start_x, title_y - char_h / 2, start_x + char_w, title_y + char_h / 2, fill="#FF3737", outline="", tags="menu_ui")
        self.widgets.main_canvas.create_text(start_x, title_y, text="F", font=("Courier New", 70, "bold"), fill="#FF8C00", anchor="w", tags="menu_ui")
        start_x += char_w
        self.widgets.main_canvas.create_text(start_x, title_y, text="inal ", font=("Courier New", 70, "bold"), fill="#FF8C00", anchor="w", tags="menu_ui")
        start_x += char_w * 5
        self.widgets.main_canvas.create_rectangle(start_x, title_y - char_h / 2, start_x + char_w, title_y + char_h / 2, fill="#FF3737", outline="", tags="menu_ui")
        self.widgets.main_canvas.create_text(start_x, title_y, text="S", font=("Courier New", 70, "bold"), fill="#FF8C00", anchor="w", tags="menu_ui")
        start_x += char_w
        self.widgets.main_canvas.create_text(start_x, title_y, text="entence", font=("Courier New", 70, "bold"), fill="#FF8C00", anchor="w", tags="menu_ui")

    def show_multiplayer_menu(self):
        # Render the multiplayer menu and rules.
        self.widgets.main_canvas.delete("menu_btn", "multiplayer_ui")
        self._hide_menu_monitor()
        cx = self.layout.screen_w * 0.25
        self.widgets.main_canvas.create_text(cx, self.layout.screen_h * 0.38, text="MULTIPLAYER", font=("Courier New", 42, "bold"), fill="#FF8C00", tags="multiplayer_ui")
        self.widgets.main_canvas.create_text(cx, self.layout.screen_h * 0.48, text=self.multiplayer_rules, font=("Courier New", 13, "bold"), fill="#d9d0c0", justify="left", width=720, tags="multiplayer_ui")
        self.create_canvas_button(cx, self.layout.screen_h * 0.68, 500, 70, "Host Game", self.callbacks["host_lobby"], ui_tag="multiplayer_ui")
        self.create_canvas_button(cx, self.layout.screen_h * 0.78, 500, 70, "Join Game", self.callbacks["join_lobby"], ui_tag="multiplayer_ui")
        self.create_canvas_button(cx, self.layout.screen_h * 0.88, 500, 70, "Back", self.callbacks["show_main_menu"], ui_tag="multiplayer_ui")

    def show_multiplayer_lobby(self, status):
        # Render the host waiting room.
        self.widgets.main_canvas.delete("menu_btn", "multiplayer_ui", "lobby_ui")
        self._hide_menu_monitor()
        cx = self.layout.screen_w * 0.25
        self.widgets.main_canvas.create_text(cx, self.layout.screen_h * 0.30, text="PRIVATE LOBBY", font=("Courier New", 42, "bold"), fill="#FF8C00", tags="lobby_ui")
        self.multiplayer.multiplayer_status_text_id = self.widgets.main_canvas.create_text(cx, self.layout.screen_h * 0.46, text=status, font=("Courier New", 18, "bold"), fill="#72d477", justify="center", width=760, tags="lobby_ui")
        self.create_canvas_button(cx, self.layout.screen_h * 0.66, 500, 70, "Start Match", self.callbacks["start_multiplayer"], ui_tag="lobby_ui")
        self.create_canvas_button(cx, self.layout.screen_h * 0.78, 500, 70, "Back", self.callbacks["leave_lobby"], ui_tag="lobby_ui")

    def show_waiting_lobby(self, status):
        # Render the client waiting room.
        self.widgets.main_canvas.delete("menu_btn", "multiplayer_ui", "lobby_ui")
        self._hide_menu_monitor()
        cx = self.layout.screen_w * 0.25
        self.widgets.main_canvas.create_text(cx, self.layout.screen_h * 0.32, text="WAITING ROOM", font=("Courier New", 42, "bold"), fill="#FF8C00", tags="lobby_ui")
        self.multiplayer.multiplayer_status_text_id = self.widgets.main_canvas.create_text(cx, self.layout.screen_h * 0.52, text=status, font=("Courier New", 17, "bold"), fill="#72d477", justify="center", width=760, tags="lobby_ui")
        self.create_canvas_button(cx, self.layout.screen_h * 0.78, 500, 70, "Back", self.callbacks["leave_lobby"], ui_tag="lobby_ui")

    def update_lobby_status(self):
        # Refresh the host player list text.
        if self.multiplayer.multiplayer_status_text_id:
            players = [self.multiplayer.player_name] + [client["name"] for client in self.multiplayer.connected_clients]
            status = f"Hosting on {self.callbacks['local_ip']()}:{self.callbacks['port']()}\nPlayers: {len(players)}\n\n" + "\n".join(f">>> {name}" for name in players)
            self.widgets.main_canvas.itemconfigure(self.multiplayer.multiplayer_status_text_id, text=status)

    def show_leaderboard_menu(self, rows):
        # Render the local leaderboard scene.
        self.widgets.main_canvas.delete("menu_btn", "leaderboard_ui")
        self._hide_menu_monitor()
        cx = self.layout.screen_w * 0.25
        self.widgets.main_canvas.create_text(cx, self.layout.screen_h * 0.30, text="LEADERBOARD", font=("Courier New", 42, "bold"), fill="#FF8C00", tags="leaderboard_ui")
        if rows:
            lines = [" Rank Player        Result COMP   WPM  Date", " ----------------------------------------------"]
            for index, row in enumerate(rows, 1):
                player = str(row.get("player", "Player"))[:12]
                completion_rate = row.get("completion_rate", row.get("avg_acc", 0))
                lines.append(f" {index:>2}.  {player:<12} {row.get('result', 'Lost'):<5} {completion_rate:>5.1f}%  {row.get('avg_wpm', 0):>3}  {row.get('created_at', '')}")
            board_text = "\n".join(lines)
        else:
            board_text = "No results yet.\nFinish a match to create your first record."
        self.widgets.main_canvas.create_text(cx, self.layout.screen_h * 0.50, text=board_text, font=("Courier New", 16, "bold"), fill="#72d477", justify="left", width=780, tags="leaderboard_ui")
        self.create_canvas_button(cx, self.layout.screen_h * 0.78, 500, 70, "Back", self.callbacks["show_main_menu"], ui_tag="leaderboard_ui")

    def show_missions_menu(self, rows):
        # Render the persistent mission progress scene.
        self.widgets.main_canvas.delete("menu_btn", "missions_ui")
        self._hide_menu_monitor()
        cx = self.layout.screen_w * 0.25
        self.widgets.main_canvas.create_text(cx, self.layout.screen_h * 0.30, text="MISSIONS", font=("Courier New", 42, "bold"), fill="#FF8C00", tags="missions_ui")
        if rows:
            lines = []
            for row in rows:
                state = "Done" if row["complete"] else f"{row['display_progress']}/{row['target']}"
                lines.append(f"{row['title']}: {state}")
                lines.append(f"  {row['description']}")
                lines.append("")
            mission_text = "\n".join(lines).strip()
        else:
            mission_text = "No missions available."
        self.widgets.main_canvas.create_text(
            cx,
            self.layout.screen_h * 0.52,
            text=mission_text,
            font=("Courier New", 16, "bold"),
            fill="#72d477",
            justify="left",
            width=780,
            tags="missions_ui",
        )
        self.create_canvas_button(cx, self.layout.screen_h * 0.82, 500, 70, "Back", self.callbacks["show_main_menu"], ui_tag="missions_ui")

    def show_options(self, from_state):
        # Render the options popup.
        self.menu.in_options_menu = True
        self.menu.options_previous_state = from_state
        if from_state == "main":
            self.widgets.main_canvas.itemconfigure("menu_btn", state="hidden")
            self._hide_menu_monitor()
        elif from_state == "ingame":
            self.widgets.main_canvas.itemconfigure("ingame_btn", state="hidden")
        cx = self.layout.screen_w // 2
        cy = self.layout.screen_h // 2
        self.widgets.main_canvas.create_rectangle(cx - 300, cy - 150, cx + 300, cy + 150, fill="#050505", outline="#FF8C00", width=3, tags="options_ui")
        self.widgets.main_canvas.create_text(cx - 180, cy - 40, text="Music", font=("Courier New", 25, "bold"), fill="#ffffff", anchor="w", tags="options_ui")
        self.widgets.main_canvas.create_text(cx - 180, cy + 40, text="Sound", font=("Courier New", 25, "bold"), fill="#ffffff", anchor="w", tags="options_ui")
        self.menu.music_scale_widget = tk.Scale(self.widgets.main_canvas, from_=0, to=100, orient="horizontal", bg="#050505", fg="#FF8C00", font=("Courier New", 15, "bold"), troughcolor="#222222", activebackground="#FF8C00", highlightthickness=0, bd=0, length=200, show=0, command=self.callbacks["set_music"])
        self.menu.music_scale_widget.set(int(self.settings.music_vol * 100))
        self.widgets.main_canvas.create_window(cx + 80, cy - 40, window=self.menu.music_scale_widget, tags="options_ui")
        self.menu.sfx_scale_widget = tk.Scale(self.widgets.main_canvas, from_=0, to=100, orient="horizontal", bg="#050505", fg="#FF8C00", font=("Courier New", 15, "bold"), troughcolor="#222222", activebackground="#FF8C00", highlightthickness=0, bd=0, length=200, show=0, command=self.callbacks["set_sfx"])
        self.menu.sfx_scale_widget.set(int(self.settings.sfx_vol * 100))
        self.widgets.main_canvas.create_window(cx + 80, cy + 40, window=self.menu.sfx_scale_widget, tags="options_ui")
        self.create_canvas_button(cx, cy + 100, 200, 50, "Back", self.callbacks["close_options"], ui_tag="options_ui")

    def close_options(self):
        # Remove the options popup and restore underlying widgets.
        self.menu.in_options_menu = False
        self.widgets.main_canvas.delete("options_ui")
        if self.menu.music_scale_widget:
            self.menu.music_scale_widget.destroy()
            self.menu.music_scale_widget = None
        if self.menu.sfx_scale_widget:
            self.menu.sfx_scale_widget.destroy()
            self.menu.sfx_scale_widget = None
        if self.menu.options_previous_state == "main":
            self.widgets.main_canvas.itemconfigure("menu_btn", state="normal")
            if self.widgets.menu_screen_text_window_id:
                self.widgets.main_canvas.itemconfigure(self.widgets.menu_screen_text_window_id, state="normal")
        elif self.menu.options_previous_state == "ingame":
            self.widgets.main_canvas.itemconfigure("ingame_btn", state="normal")

    def show_stats_on_screen(self, status_type, summary, last_wpm, best_completion, article_completion):
        # Render end-of-match stats text on the monitor.
        self.widgets.screen_text.config(state=tk.NORMAL)
        self.widgets.screen_text.delete("1.0", tk.END)
        stats_text = f"""
   -------------------------------------------
   |  Metric  | Average |   Max   |   Last   |
   -------------------------------------------
   | Complete | {summary['completion_rate']:>6.1f}% | {best_completion:>6.1f}% | {article_completion:>6.1f}% |
   -------------------------------------------
   |   WPM    | {summary['avg_wpm']:^7} | {summary['max_wpm']:^7} | {last_wpm:^7} |
   -------------------------------------------

   Char: {summary['chars']}
   Mistakes: {summary['mistakes']}
   Typing time: {self.stats.total_typing_time}s
   Roulettes: {summary['roulettes']}
   Best Combo: {self.game.max_combo}
   Rank: {summary['rank']}
"""
        self.widgets.screen_text.insert(tk.END, "\n   Result: ")
        if status_type == "Won":
            self.widgets.screen_text.insert(tk.END, " Won ", "tag_won")
        else:
            self.widgets.screen_text.insert(tk.END, " Lost ", "tag_dead")
        self.widgets.screen_text.config(state=tk.DISABLED)
        self.callbacks["typewriter"](stats_text, 0)

    def transition_monitor_to_center(self):
        # Enlarge the monitor for the ending scene.
        scale = 3
        term_monitor_w = int(self.layout.monitor_w * scale)
        term_monitor_h = int(self.layout.monitor_h * scale)
        img_monitor = Image.open(image_path("screen.png")).resize((term_monitor_w, term_monitor_h))
        self.assets.term_monitor_photo = ImageTk.PhotoImage(img_monitor)
        self.widgets.main_canvas.itemconfigure("monitor", image=self.assets.term_monitor_photo)
        new_monitor_y = self.layout.screen_h // 2 + term_monitor_h // 2 + 250
        self.widgets.main_canvas.coords("monitor", self.layout.center_x, new_monitor_y)
        term_screen_w = int(self.layout.inner_screen_w * scale)
        term_screen_h = int(self.layout.inner_screen_h * scale)
        new_screen_text_y = new_monitor_y - int(term_monitor_h * 0.58)
        self.widgets.main_canvas.itemconfigure(self.widgets.screen_text_window_id, state="normal")
        self.widgets.main_canvas.itemconfigure(self.widgets.screen_text_window_id, width=term_screen_w, height=term_screen_h)
        self.widgets.main_canvas.coords(self.widgets.screen_text_window_id, self.layout.center_x, new_screen_text_y)
        self.widgets.screen_text.config(font=("Courier New", 25, "bold"))
        self.widgets.main_canvas.tag_raise("monitor")
        self.widgets.main_canvas.tag_raise(self.widgets.screen_text_window_id)

    def _hide_menu_monitor(self):
        # Hide the menu monitor text if it exists.
        if self.widgets.menu_screen_text_window_id:
            self.widgets.main_canvas.itemconfigure(self.widgets.menu_screen_text_window_id, state="hidden")
