import tkinter as tk
import tkinter.font as tkFont  
import tkinter.simpledialog as simpledialog
import tkinter.messagebox as messagebox
import random
import math
import socket
import threading
import json
import queue
from PIL import Image, ImageTk, ImageDraw, ImageFont
import pygame

#Pygame音效
pygame.mixer.init()
AUDIO_ENABLED = True

#音量變數(預設100%)
music_vol = 1.0
sfx_vol = 1.0

#載入音效檔案
pygame.mixer.music.load("bgm.mp3")            
sound_type = pygame.mixer.Sound("type.wav")   
sound_wrong = pygame.mixer.Sound("wrong.wav") 
sound_spin = pygame.mixer.Sound("spin.wav")   
sound_click = pygame.mixer.Sound("click.wav") 
sound_shoot = pygame.mixer.Sound("shoot.wav") 
sound_tick = pygame.mixer.Sound("tick.wav")   
sound_type_stats = pygame.mixer.Sound("type.wav") 

#音量同步函數
def apply_volumes():
    if not AUDIO_ENABLED: return
    pygame.mixer.music.set_volume(music_vol)
    if sound_type: sound_type.set_volume(0.3 * sfx_vol)
    if sound_wrong: sound_wrong.set_volume(1.0 * sfx_vol)
    if sound_spin: sound_spin.set_volume(1.0 * sfx_vol)
    if sound_click: sound_click.set_volume(1.0 * sfx_vol)
    if sound_shoot: sound_shoot.set_volume(1.0 * sfx_vol)
    if sound_tick: sound_tick.set_volume(0.15 * sfx_vol)
    if sound_type_stats: sound_type_stats.set_volume(0.1 * sfx_vol)

apply_volumes()

#遊戲狀態與排版變數
articles = []           
current_article_idx = 0 
current_index = 0       
mistakes = 0
max_mistakes = 3
bullets_loaded = 0      

chambers = [False] * 6  

game_active = False
is_frozen = False
is_resting = False

is_pre_game = False
pre_game_time = 5
termination_time = 20 
can_exit = False 
in_menu = True 
in_transition = False 

#選單狀態
in_ingame_menu = False
ingame_overlay_photo = None
in_options_menu = False
options_previous_state = None
music_scale_widget = None
sfx_scale_widget = None

#多人連線狀態
MULTIPLAYER_PORT = 50505
multiplayer_mode = False
is_host = False
player_name = "Player"
host_socket = None
server_socket = None
client_threads = []
connected_clients = []
network_queue = queue.Queue()
pending_article_indices = None
multiplayer_status_text_id = None
match_finished = False

total_chars_typed = 0
total_mistakes = 0
total_typing_time = 0
article_chars = 0
article_mistakes = 0
wpm_list = []
acc_list = []

loading_progress = 0
scroll_job = None
roulette_revealed = False 

time_left = 240      
timer_job = None     
player_id = 1

bg_photo = None
dead_bg_photo = None
table_photo = None
monitor_photo = None 
term_monitor_photo = None  
menu_monitor_photo = None 
kb_photo = None  
clock_photo = None
rank_photo = None  

img_blood = None
black_screen = None
fade_photo = None
blood_photo = None
text_window_id = None
screen_text_window_id = None 

clock_text_photo = None
rank_text_photo = None

left_edge = 0
center_x = 0
base_y = 0

first_box_cx = 0
revolver_cx = 0

clock_text_x = 0
clock_text_y = 0
clock_font_size = 20

current_bar_width = 40 

TEXT_WIDTH = 48       
START_INDEX = 3       
PREFIX_SPACES = " " * START_INDEX 

#遊戲文本(可擴充)
PREDEFINED_TEXTS = [
    "Tomatoes\nTomatos\nTomatoss\nTomattos\nTomattoes\nTomattoess\nTommattoess\nTommattoes\nTommatos\nTommatoss\nThe word was guessed: Tomatoes\n",
    "Cucumbers\nCucumbers\nCucmubers\nCucumbars\nCucumbirs\nCucumbors\nCucumburs\nCucmumbers\nCucumberss\nCucumbersz\nThe word was guessed: Cucumbers\n",
    "Potatoes\nPotatos\nPotattos\nPotattos\nPotatoos\nPotatoos\nPottatoes\nPottatoes\nPotattoes\nPotatoos\nThe word was guessed: Potatoes\n",
    "It's-been three? four? days-\nThey said there'd be time to speak.\nI sleep. I eat. I wait. I'm fine.\nI keep thinking this is all... not yet real.\n",
    "I saw her face again-no-no I didn't-\njust her hands-one hand-shaking.\nI looked away. WHY did I look away?\nIt was over too fast. That's worse.\n",
    "I THOUGHT I-\nI thought I had time to change?\nTo fix something. to-undo-to stop it.\nBut I just stood there. I DID NOTHING.\n",
    "I HEARD THEM-I DID-I JUST-\nplease god please I didn't want to-\nI DID! I KNOW I DID!\ndon't let them hang me without-\n",
    "I'm sorry.\nI'm sorry.\nI remember it all. Every sound.\nTell them I said it. Tell them I said it.\n",
    "All your base are belong to us\nI can haz cheeseburger?\nLeeroy Jenkins!\nDo a barrel roll!\n",
    "Press F to pay respects\nOne does not simply walk into Mordor\nHide yo kids, hide yo wife\nThis is fine\n",
    "I am your father\nBut I never told you\nThis is SPARTA!\nWhy you heff to me mad?\n",
    "Here comes dat boi!\nO shit waddup!\nI see what you did there\nAm I a joke to you?\n",
    "Observer: D. Thorne\nLocation: Sector North-East, Ridge 7-B\nPage 14\n",
    "Specimen ID: 042\nCoordinates: 54d12'N, 13d44'E\nDate - Time: 7.04 at 09:36\nObserved Traits:\n- Hexapod, est, 4.1 cm, weight under 2 g\n- Exoskeleton: green-black, iridescent\n- Emerged from shale surface\n- Clicking sound when handled\nStatus: Sample secured, vial C3\n",
    "Specimen ID: 057\nCoordinates: 54d13'N, 13d46'E\nDate - Time: 7.04 at 13:12\nObserved Traits:\n- Quadruped, est, 37 cm, weight 1.2 kg\n- Facial mark: full black oval \"mask\"\n- Fur: pale gold, grey-blue underlayer\n- Hind legs highly articulated\nStatus: Avoided capture\n",
    "Specimen ID: 063\nCoordinates: 54d15'N, 13d49'E\nDate - Time: 7.04 at 16:08\nObserved Traits:\n- Solitary bird, wingspan est. 62 cm\n- Plumage: copper with soot-black bands\n- No vocal call; throat vibrates visibly\n- Eyes front-facing, unblinking\nStatus: Observeed only\n",
    "First text finished.\nCongratulations.\nNow let's add commas. dashes. dots.\n",
    "The timer on the table shows time left.\nIf it hits zero - bang bang.\nThe man in the black coat shoots.\n",
    "Numbers first.\n1234567890\nLetters next\nqwertyuiop\nasdfghjkl\nzxcvbnm\nNow symbols\n---\n'''\n...\n,,,\n;;;\n:::\n!!!\n???\n",
    "end line with enter or space\nshift is optional for CAPITALS\nround one cleared well done\nempty line ends a round\nPractice ends when this text is finished.\nGet ready for the real thing.\n"
]

def get_article_text(raw_text):
    lines = raw_text.strip().split('\n')
    formatted_lines = [PREFIX_SPACES + line.strip() + " " for line in lines]
    return "\n".join(formatted_lines) + "\n"

#多人規則說明
MULTIPLAYER_RULES = (
    "Multiplayer Rules\n"
    "1. All players type the same five passages at the same time.\n"
    "2. Every player has a 240-second timer for each passage.\n"
    "3. A wrong key resets the current line and adds one strike.\n"
    "4. Three strikes trigger Russian Roulette; a loaded chamber eliminates that player.\n"
    "5. The first player to finish all passages wins. If everyone else dies first, the last survivor wins.\n"
    "6. This Socket version supports private LAN lobbies: one player hosts, others join by IP.\n"
)

def queue_network_event(event):
    network_queue.put(event)

def poll_network_events():
    try:
        while True:
            event = network_queue.get_nowait()
            handle_network_event(event)
    except queue.Empty:
        pass
    root.after(100, poll_network_events)

def send_json(sock, payload):
    try:
        sock.sendall((json.dumps(payload) + "\n").encode("utf-8"))
        return True
    except OSError:
        return False

def read_json_lines(sock, callback):
    buffer = ""
    try:
        while True:
            data = sock.recv(4096)
            if not data:
                break
            buffer += data.decode("utf-8")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if line.strip():
                    callback(json.loads(line))
    except (OSError, json.JSONDecodeError):
        pass

def stop_multiplayer_network():
    global host_socket, server_socket, connected_clients, client_threads, is_host
    for client in connected_clients:
        try: client["sock"].close()
        except OSError: pass
    connected_clients = []
    if host_socket:
        try: host_socket.close()
        except OSError: pass
    if server_socket:
        try: server_socket.close()
        except OSError: pass
    host_socket = None
    server_socket = None
    client_threads = []
    is_host = False

def get_local_ip():
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        ip = probe.getsockname()[0]
        probe.close()
        return ip
    except OSError:
        return "127.0.0.1"

def broadcast_to_clients(payload):
    alive_clients = []
    for client in connected_clients:
        if send_json(client["sock"], payload):
            alive_clients.append(client)
    connected_clients[:] = alive_clients

def host_accept_loop():
    global connected_clients
    while server_socket:
        try:
            sock, addr = server_socket.accept()
            client = {"sock": sock, "addr": addr, "name": f"Player {len(connected_clients) + 2}", "alive": True}
            connected_clients.append(client)
            def on_message(msg, client_ref=client):
                if msg.get("type") == "hello":
                    client_ref["name"] = msg.get("name", client_ref["name"])
                    queue_network_event({"type": "lobby_update"})
                elif msg.get("type") in ("finished", "dead"):
                    queue_network_event({"type": "remote_result", "name": client_ref["name"], "result": msg.get("type")})
            threading.Thread(target=read_json_lines, args=(sock, on_message), daemon=True).start()
            send_json(sock, {"type": "welcome", "rules": MULTIPLAYER_RULES})
            queue_network_event({"type": "lobby_update"})
        except OSError:
            break

def client_listen_loop(sock):
    read_json_lines(sock, queue_network_event)
    queue_network_event({"type": "connection_closed"})

def start_host_lobby():
    global multiplayer_mode, is_host, player_name, server_socket, connected_clients
    stop_multiplayer_network()
    name = simpledialog.askstring("Host Multiplayer", "Your player name:", initialvalue="Host")
    if not name: return
    player_name = name
    multiplayer_mode = True
    is_host = True
    connected_clients = []
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(("", MULTIPLAYER_PORT))
        server_socket.listen()
        threading.Thread(target=host_accept_loop, daemon=True).start()
        show_multiplayer_lobby(f"Hosting on {get_local_ip()}:{MULTIPLAYER_PORT}")
    except OSError as e:
        messagebox.showerror("Socket Error", f"Cannot host game:\n{e}")
        stop_multiplayer_network()

def join_host_lobby():
    global multiplayer_mode, is_host, player_name, host_socket
    stop_multiplayer_network()
    name = simpledialog.askstring("Join Multiplayer", "Your player name:", initialvalue="Player")
    if not name: return
    host_ip = simpledialog.askstring("Join Multiplayer", "Host IP:", initialvalue="127.0.0.1")
    if not host_ip: return
    player_name = name
    multiplayer_mode = True
    is_host = False
    try:
        host_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host_socket.connect((host_ip, MULTIPLAYER_PORT))
        send_json(host_socket, {"type": "hello", "name": player_name})
        threading.Thread(target=client_listen_loop, args=(host_socket,), daemon=True).start()
        show_waiting_lobby(f"Connected to {host_ip}:{MULTIPLAYER_PORT}\nWaiting for host...")
    except OSError as e:
        messagebox.showerror("Socket Error", f"Cannot join game:\n{e}")
        stop_multiplayer_network()

def host_start_multiplayer_match():
    global pending_article_indices, match_finished
    if not is_host: return
    pending_article_indices = random.sample(range(len(PREDEFINED_TEXTS)), 5)
    match_finished = False
    for client in connected_clients:
        client["alive"] = True
    broadcast_to_clients({"type": "start", "article_indices": pending_article_indices})
    play_btn_clicked(multiplayer=True)

def notify_multiplayer_result(result):
    global match_finished
    if not multiplayer_mode or match_finished:
        return
    match_finished = True
    payload = {"type": result, "name": player_name}
    if is_host:
        broadcast_to_clients({"type": "match_result", "winner": player_name if result == "finished" else None, "reason": result})
    elif host_socket:
        send_json(host_socket, payload)

def handle_network_event(event):
    global pending_article_indices, match_finished
    event_type = event.get("type")
    if event_type == "lobby_update":
        update_lobby_status()
    elif event_type == "welcome":
        show_waiting_lobby("Connected.\nWaiting for host...\n\n" + event.get("rules", ""))
    elif event_type == "start":
        pending_article_indices = event.get("article_indices")
        match_finished = False
        play_btn_clicked(multiplayer=True)
    elif event_type == "remote_result":
        name = event.get("name", "Player")
        result = event.get("result")
        if result == "finished":
            broadcast_to_clients({"type": "match_result", "winner": name, "reason": "finished"})
            if game_active:
                game_over()
        elif result == "dead":
            for client in connected_clients:
                if client["name"] == name:
                    client["alive"] = False
            if game_active and connected_clients and all(not client.get("alive", True) for client in connected_clients):
                game_win()
    elif event_type == "match_result":
        winner = event.get("winner")
        if winner and winner != player_name and game_active:
            main_canvas.create_text(center_x, int(screen_h * 0.08), text=f"{winner} has finished first.", font=("Courier New", 24, "bold"), fill="#ff4444", justify="center", tags="end_msg")
            game_over()
    elif event_type == "connection_closed":
        if multiplayer_mode and in_menu:
            show_waiting_lobby("Connection closed.\nReturn to menu and try again.")

def record_article_stats():
    global article_chars, article_mistakes, wpm_list, acc_list, total_typing_time
    time_spent = 240 - time_left
    if time_spent <= 0: time_spent = 1 
    total_typing_time += time_spent
    wpm = (article_chars / 5.0) / (time_spent / 60.0) if article_chars > 0 else 0
    total_attempts = article_chars + article_mistakes
    acc = (article_chars / total_attempts * 100.0) if total_attempts > 0 else 0.0
    if total_attempts > 0:
        wpm_list.append(int(wpm))
        acc_list.append(round(acc, 1))
    article_chars = 0
    article_mistakes = 0

def initialize_game(article_indices=None):
    global articles, current_article_idx, current_index, bullets_loaded, roulette_revealed, chambers
    global time_left, timer_job, game_active, is_pre_game, pre_game_time, can_exit
    global total_chars_typed, total_mistakes, total_typing_time, article_chars, article_mistakes, wpm_list, acc_list
    global mistakes, is_frozen, is_resting, loading_progress, in_ingame_menu, in_options_menu
    
    if article_indices:
        selected_texts = [PREDEFINED_TEXTS[i] for i in article_indices]
    else:
        selected_texts = random.sample(PREDEFINED_TEXTS, 5)
    articles = [get_article_text(text) for text in selected_texts]
    current_article_idx = 0
    current_index = START_INDEX 
    chambers = [False] * 6  
    bullets_loaded = 0
    roulette_revealed = False
    game_active = True
    can_exit = False
    mistakes = 0
    is_frozen = False
    is_resting = False
    in_ingame_menu = False
    in_options_menu = False
    loading_progress = 0
    total_chars_typed = 0
    total_mistakes = 0
    total_typing_time = 0
    article_chars = 0
    article_mistakes = 0
    wpm_list = []
    acc_list = []
    is_pre_game = True
    pre_game_time = 5
    time_left = 240
    
    if timer_job:
        root.after_cancel(timer_job)
        timer_job = None
    
    text_display.delete("1.0", tk.END)
    
    try:
        screen_text.config(state=tk.NORMAL)
        screen_text.delete("1.0", tk.END)
        screen_text.insert(tk.END, PREFIX_SPACES)
        screen_text.config(state=tk.DISABLED)
    except:
        pass
    
    for i, content in enumerate(articles):
        start_mark = f"art_{i}_start"
        idx = text_display.index("end-1c")
        text_display.mark_set(start_mark, idx)
        text_display.mark_gravity(start_mark, tk.LEFT)
        text_display.insert(tk.END, content, "pending")
        if i < 4:
            bar_mark = f"bar_{i}_start"
            idx = text_display.index("end-1c")
            text_display.mark_set(bar_mark, idx)
            text_display.mark_gravity(bar_mark, tk.LEFT)
            text_display.insert(tk.END, "\n")
            
    text_display.insert(tk.END, "\n" * 20)
    text_display.yview_moveto(0)
    text_display.mark_set("insert", f"art_0_start + {START_INDEX} chars")
    text_display.see("insert") 
    update_line_highlight()
    update_hud()
    update_clock_display()
    
    main_canvas.delete("pre_game_text")
    main_canvas.create_text(center_x, int(screen_h * 0.08), text="Game starts in:\n00:05",
                            font=("Courier New", 20, "bold"), fill="#72d477", justify="center", tags="pre_game_text")
    
    timer_job = root.after(1000, run_pre_game_timer)

#UI與左輪手槍
def draw_revolver(rotation_index=0):
    main_canvas.delete("revolver")
    if not roulette_revealed: return
        
    cx = revolver_cx
    cy = base_y - 45 
    
    main_canvas.create_oval(cx-28, cy-28, cx+28, cy+28, fill="#1a1a1a", outline="#0a0a0a", width=2, tags="revolver")
    main_canvas.create_oval(cx-4, cy-4, cx+4, cy+4, fill="#0a0a0a", tags="revolver") 

    for i in range(6):
        angle = math.radians(i * 60 - 90)
        bx = cx + 16 * math.cos(angle)
        by = cy + 16 * math.sin(angle)
        
        logical_index = (i - rotation_index) % 6
        is_loaded = chambers[logical_index]
        
        main_canvas.create_oval(bx-6, by-6, bx+6, by+6, fill="#050505", outline="#2a2a2a", tags="revolver")
        if is_loaded:
            main_canvas.create_oval(bx-4, by-4, bx+4, by+4, fill="#aa1111", outline="#ff4444", tags="revolver")

def draw_lives():
    main_canvas.delete("lives")
    cy = base_y - 45
    for i in range(max_mistakes):
        cx = first_box_cx + (i * 40) 
        if i < mistakes:
            bg_color = "#550000"
            outline_color = "#880000"
            char = "X"
        else:
            bg_color = "#111111"
            outline_color = "#5a4a36"
            char = ""
        main_canvas.create_rectangle(cx-16, cy-16, cx+16, cy+16, fill=bg_color, outline=outline_color, width=2, tags="lives")
        if char:
            main_canvas.create_text(cx, cy, text=char, fill="#ff4444", font=("Courier New", 18, "bold"), tags="lives")

def update_hud():
    draw_revolver(0)
    draw_lives()

def run_pre_game_timer():
    global pre_game_time, is_pre_game, timer_job
    if not game_active: return
    pre_game_time -= 1
    if pre_game_time > 0:
        main_canvas.itemconfigure("pre_game_text", text=f"Game starts in:\n00:0{pre_game_time}")
        timer_job = root.after(1000, run_pre_game_timer)
    else:
        main_canvas.delete("pre_game_text")
        is_pre_game = False
        run_timer()

def run_timer():
    global time_left, timer_job, in_ingame_menu, in_options_menu
    if not game_active: return
    
    if not is_frozen and not is_resting:
        time_left -= 1
        if AUDIO_ENABLED: sound_tick.play()
        
        if time_left <= 0:
            time_left = 0
            update_clock_display()
            if in_options_menu: close_options()
            if in_ingame_menu:
                in_ingame_menu = False
                main_canvas.delete("ingame_menu_bg", "ingame_btn")
                main_canvas.itemconfigure(text_window_id, state="normal")
                main_canvas.itemconfigure(screen_text_window_id, state="normal")
            game_over(by_timeout=True)
            return
            
    update_clock_display()
    timer_job = root.after(1000, run_timer)

#旋轉文字圖片(時鐘、名牌)
def create_rotated_text_image(text, font_size, color, angle, font_file="courbd.ttf"):
    try: font = ImageFont.truetype(font_file, font_size)
    except IOError:
        try: font = ImageFont.truetype("timesbd.ttf", font_size)
        except IOError:
            try: font = ImageFont.truetype("Courier New Bold.ttf", font_size)
            except IOError: font = ImageFont.load_default()
    dummy_draw = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    bbox = dummy_draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    canvas_size = int(max(text_width, text_height) * 1.5)
    img = Image.new('RGBA', (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((canvas_size/2, canvas_size/2), text, font=font, fill=color, anchor="mm")
    rotated_img = img.rotate(angle, resample=Image.BICUBIC, expand=True)
    return ImageTk.PhotoImage(rotated_img)

def update_clock_display():
    global clock_text_photo
    mins = time_left // 60
    secs = time_left % 60
    time_str = f"{mins:02d}:{secs:02d}"
    
    main_canvas.delete("clock_text")
    clock_text_photo = create_rotated_text_image(time_str, clock_font_size, "#ffffff", 2, font_file="courbd.ttf")
    main_canvas.create_image(clock_text_x, clock_text_y, image=clock_text_photo, anchor="center", tags="clock_text")
    
    if in_ingame_menu:
        main_canvas.tag_raise("ingame_menu_bg")
        main_canvas.tag_raise("ingame_btn") 
    if in_options_menu:
        main_canvas.tag_raise("options_ui")

#遊戲邏輯與滾動動畫
def start_roulette():
    global bullets_loaded, is_frozen, roulette_revealed, chambers
    roulette_revealed = True 
    is_frozen = True
    if AUDIO_ENABLED: sound_spin.play()
    
    empty_chambers = [i for i, loaded in enumerate(chambers) if not loaded]
    if empty_chambers:
        chosen = random.choice(empty_chambers)
        chambers[chosen] = True
        bullets_loaded += 1

    target_chamber = random.randint(0, 5)
    final_rotation = (-target_chamber) % 6
    total_spins = random.randint(3, 5) * 6 
    total_steps = total_spins + final_rotation
    animate_spin(0, total_steps, target_chamber)

def animate_spin(current_step, total_steps, target_chamber):
    draw_revolver(current_step % 6)
    if current_step < total_steps:
        progress = current_step / total_steps
        delay = int(20 + 200 * (progress ** 3))
        root.after(delay, lambda: animate_spin(current_step + 1, total_steps, target_chamber))
    else:
        root.after(500, lambda: resolve_roulette(target_chamber))

def resolve_roulette(target_chamber):
    global mistakes, is_frozen
    if chambers[target_chamber]:
        if AUDIO_ENABLED: sound_shoot.play()
        game_over(by_roulette=True)
    else:
        if AUDIO_ENABLED: sound_click.play()
        mistakes = 0
        update_hud()
        target_content = articles[current_article_idx]
        line_start_idx = target_content.rfind('\n', 0, current_index)
        new_index = (0 if line_start_idx == -1 else line_start_idx + 1) + START_INDEX
        show_error_and_reset(new_index)

def perform_smooth_scroll(current_y, target_y, step, total_steps=15):
    global scroll_job
    if step >= total_steps:
        text_display.yview_moveto(target_y)
        scroll_job = None
        text_display.see("insert")
        return
    progress = step / total_steps
    ease = 1 - (1 - progress) ** 2 
    new_y = current_y + (target_y - current_y) * ease
    text_display.yview_moveto(new_y)
    scroll_job = root.after(16, lambda: perform_smooth_scroll(current_y, target_y, step + 1, total_steps))

def scroll_one_line_down():
    global scroll_job
    if scroll_job: root.after_cancel(scroll_job)
    text_display.update_idletasks()
    current_y = text_display.yview()[0]
    text_display.yview_scroll(1, "units")
    target_y = text_display.yview()[0]
    if abs(target_y - current_y) > 0.0001:
        text_display.yview_moveto(current_y)
        perform_smooth_scroll(current_y, target_y, 1)

def handle_keypress(event):
    global current_index, mistakes, game_active
    global total_chars_typed, total_mistakes, article_chars, article_mistakes
    
    if can_exit:
        return_to_menu_transition()
        return "break"
        
    if event.keysym == 'Escape':
        if in_options_menu:
            close_options()
            return "break"
        toggle_ingame_menu()
        return "break"
    
    if not game_active or is_frozen or is_resting or is_pre_game or in_menu or in_transition or in_ingame_menu or in_options_menu: 
        return "break"
        
    if event.keysym in ('Shift_L', 'Shift_R', 'Caps_Lock', 'Control_L', 'Control_R', 'Alt_L', 'Alt_R'): return "break"

    char = event.char
    if event.keysym == "Return": char = "\n"
    if not char: return "break"

    target_content = articles[current_article_idx]
    expected_char = target_content[current_index]
    mark_start = f"art_{current_article_idx}_start"

    if char == '\n' and expected_char == ' ' and current_index + 1 < len(target_content) and target_content[current_index + 1] == '\n':
        text_display.tag_remove("pending", f"{mark_start} + {current_index} chars")
        text_display.tag_add("correct", f"{mark_start} + {current_index} chars")
        current_index += 1
        expected_char = '\n'

    if char == expected_char:
        if AUDIO_ENABLED: sound_type.play()
            
        total_chars_typed += 1
        article_chars += 1
        
        screen_text.config(state=tk.NORMAL)
        screen_text.insert(tk.END, char)
        screen_text.see(tk.END)
        screen_text.config(state=tk.DISABLED)

        pos = f"{mark_start} + {current_index} chars"
        text_display.tag_remove("pending", pos)
        text_display.tag_add("correct", pos)
        current_index += 1
        
        while current_index < len(target_content) and target_content[current_index] == ' ':
            next_newline = target_content.find('\n', current_index)
            if next_newline != -1 and target_content[current_index:next_newline].strip() == '':
                screen_text.config(state=tk.NORMAL)
                screen_text.insert(tk.END, ' ')
                screen_text.see(tk.END)
                screen_text.config(state=tk.DISABLED)
                p = f"{mark_start} + {current_index} chars"
                text_display.tag_remove("pending", p)
                text_display.tag_add("correct", p)
                current_index += 1
            else:
                break
                
        if current_index < len(target_content) and char == '\n':
            current_index += START_INDEX
            screen_text.config(state=tk.NORMAL)
            screen_text.insert(tk.END, PREFIX_SPACES)
            screen_text.see(tk.END)
            screen_text.config(state=tk.DISABLED)
            for offset in range(START_INDEX):
                p = f"{mark_start} + {current_index - START_INDEX + offset} chars"
                text_display.tag_remove("pending", p)
                text_display.tag_add("correct", p)
            scroll_one_line_down()
        
        if current_index >= len(target_content):
            if current_article_idx < 4: trigger_rest_phase()
            else: game_win()
        else:
            text_display.mark_set("insert", f"{mark_start} + {current_index} chars")
            update_line_highlight()
            text_display.see("insert") 
    else:
        if AUDIO_ENABLED: sound_wrong.play()
        mistakes += 1
        total_mistakes += 1
        article_mistakes += 1
        update_hud()
        
        err_idx = current_index
        if expected_char == '\n': err_idx = max(0, current_index - 1)
        text_display.tag_add("wrong_bg", f"{mark_start} + {err_idx} chars", f"{mark_start} + {err_idx + 1} chars")
        
        if mistakes >= max_mistakes: start_roulette()
        else:
            line_start_idx = target_content.rfind('\n', 0, current_index)
            new_index = (0 if line_start_idx == -1 else line_start_idx + 1) + START_INDEX
            show_error_and_reset(new_index)

    return "break"

def show_error_and_reset(new_index):
    global is_frozen, current_index
    is_frozen = True  
    mark_start = f"art_{current_article_idx}_start"

    chars_to_delete = current_index - new_index
    
    def finalize():
        global current_index, is_frozen
        if not game_active: return
        for i in range(new_index, current_index):
            p = f"{mark_start} + {i} chars"
            text_display.tag_remove("correct", p)
            text_display.tag_add("pending", p)
        current_index = new_index
        text_display.mark_set("insert", f"{mark_start} + {current_index} chars")
        update_line_highlight()
        text_display.see("insert") 
        is_frozen = False

    def animate_backspace(remaining):
        if remaining > 0 and game_active:
            try:
                screen_text.config(state=tk.NORMAL)
                screen_text.delete("end-2c")
                screen_text.see(tk.END)
                screen_text.config(state=tk.DISABLED)
            except: pass
            
            delay = max(15, 300 // chars_to_delete) if chars_to_delete > 0 else 30
            root.after(delay, animate_backspace, remaining - 1)
        else: root.after(100, finalize)

    if chars_to_delete > 0: animate_backspace(chars_to_delete)
    else: root.after(300, finalize)

def trigger_rest_phase():
    global is_resting, loading_progress, current_bar_width
    record_article_stats()
    is_resting = True
    loading_progress = 0
    text_display.config(insertbackground="#111111")
    text_display.tag_remove("current_line_bg", "1.0", tk.END)
    bar_mark = f"bar_{current_article_idx}_start"
    screen_text.config(state=tk.NORMAL)
    screen_text.insert(tk.END, PREFIX_SPACES)
    screen_text.see(tk.END)
    screen_text.config(state=tk.DISABLED)
    current_bar_width = 40
    text_display.insert(bar_mark, PREFIX_SPACES + "|" * current_bar_width)
    text_display.tag_add("loading_bar_fill", f"{bar_mark} + {START_INDEX} chars", f"{bar_mark} + {START_INDEX + current_bar_width} chars")
    scroll_one_line_down()
    animate_loading_bar()

def animate_loading_bar():
    global loading_progress, current_article_idx, current_index, is_resting, time_left
    if not game_active: return
    bar_mark = f"bar_{current_article_idx}_start"
    if loading_progress < current_bar_width:
        target_idx = START_INDEX + (current_bar_width - 1) - loading_progress
        pos_start = f"{bar_mark} + {target_idx} chars"
        pos_end = f"{bar_mark} + {target_idx + 1} chars"
        text_display.tag_remove("loading_bar_fill", pos_start, pos_end)
        text_display.tag_add("loading_bar_bg", pos_start, pos_end)
        loading_progress += 1
        delay = int(5000 / current_bar_width)
        root.after(delay, animate_loading_bar)
    else:
        current_article_idx += 1
        current_index = START_INDEX  
        is_resting = False
        time_left = 240
        update_clock_display()
        text_display.config(insertbackground="#ffffff")
        start_pos = f"art_{current_article_idx}_start"
        text_display.mark_set("insert", f"{start_pos} + {START_INDEX} chars")
        update_line_highlight()
        text_display.see("insert")
        scroll_one_line_down()
        screen_text.config(state=tk.NORMAL)
        screen_text.insert(tk.END, "\n" + PREFIX_SPACES)
        screen_text.see(tk.END)
        screen_text.config(state=tk.DISABLED)

def update_line_highlight():
    text_display.tag_remove("current_line_bg", "1.0", tk.END)
    text_display.tag_add("current_line_bg", f"insert linestart + {START_INDEX} chars", "insert lineend")
    text_display.tag_raise("wrong_bg", "current_line_bg") 

#結算排版
def typewriter_insert(text_str, index):
    if index < len(text_str) and not game_active:
        chunk = text_str[index:index+1] 
        try:
            screen_text.config(state=tk.NORMAL)
            screen_text.insert(tk.END, chunk)
            screen_text.see(tk.END)
            screen_text.config(state=tk.DISABLED)
            if AUDIO_ENABLED and chunk not in (' ', '\n'):
                sound_type_stats.play()
        except: pass
        delay = 40 if chunk == '\n' else 15
        root.after(delay, typewriter_insert, text_str, index + 1)
    elif index >= len(text_str) and not game_active:
        try:
            screen_text.config(state=tk.NORMAL)
            screen_text.insert(tk.END, "\n\n--按下任意按鍵來離開--", "blink_exit")
            screen_text.see(tk.END)
            screen_text.config(state=tk.DISABLED)
            blink_screen_exit_prompt(True)
        except: pass

def blink_screen_exit_prompt(visible):
    try:
        current_color = "#72d477" if visible else "#050505"
        screen_text.tag_config("blink_exit", foreground=current_color, justify="center")
        root.after(600, lambda: blink_screen_exit_prompt(not visible))
    except: pass

def show_stats_on_screen(status_type):
    screen_text.config(state=tk.NORMAL)
    screen_text.delete("1.0", tk.END)
    
    avg_wpm = sum(wpm_list) // len(wpm_list) if wpm_list else 0
    max_wpm = max(wpm_list) if wpm_list else 0
    last_wpm = wpm_list[-1] if wpm_list else 0
    avg_acc = sum(acc_list) / len(acc_list) if acc_list else 0.0
    max_acc = max(acc_list) if acc_list else 0.0
    last_acc = acc_list[-1] if acc_list else 0.0
    
    stats_text = f"""
   -------------------------------------------
   |  Metric  | Average |   Max   |   Last   |
   -------------------------------------------
   | Accuracy | {avg_acc:>6.1f}% | {max_acc:>6.1f}% | {last_acc:>6.1f}% |
   -------------------------------------------
   |   WPM    | {avg_wpm:^7} | {max_wpm:^7} | {last_wpm:^7} |
   -------------------------------------------

   Char: {total_chars_typed}
   Mistakes: {total_mistakes}
   Typing time: {total_typing_time}s
   Roulettes: {bullets_loaded}
"""
    screen_text.insert(tk.END, "\n   Result: ")
    if status_type == "Won": screen_text.insert(tk.END, " Won ", "tag_won")
    else: screen_text.insert(tk.END, " Lost ", "tag_dead")
    screen_text.config(state=tk.DISABLED)
    typewriter_insert(stats_text, 0)

#轉場動畫
def transition_monitor_to_center():
    global term_monitor_photo
    try:
        scale = 3
        term_monitor_w = int(monitor_w * scale)
        term_monitor_h = int(monitor_h * scale)
        img_monitor = Image.open("screen.png").resize((term_monitor_w, term_monitor_h))
        term_monitor_photo = ImageTk.PhotoImage(img_monitor)
        main_canvas.itemconfigure("monitor", image=term_monitor_photo)
        new_monitor_y = screen_h // 2 + term_monitor_h // 2 + 250
        main_canvas.coords("monitor", center_x, new_monitor_y)
        term_screen_w = int(inner_screen_w * scale)
        term_screen_h = int(inner_screen_h * scale)
        new_screen_text_y = new_monitor_y - int(term_monitor_h * 0.58)
        
        main_canvas.itemconfigure(screen_text_window_id, state="normal")
        main_canvas.itemconfigure(screen_text_window_id, width=term_screen_w, height=term_screen_h)
        main_canvas.coords(screen_text_window_id, center_x, new_screen_text_y)
        screen_text.config(font=("Courier New", 25, "bold")) 
        main_canvas.tag_raise("monitor")
        main_canvas.tag_raise(screen_text_window_id)
    except Exception as e: print("螢幕放大轉場錯誤:", e)

#遊戲獲勝
def game_win():
    global game_active, timer_job
    game_active = False  
    if timer_job:
        root.after_cancel(timer_job)
        timer_job = None
    text_display.tag_remove("current_line_bg", "1.0", tk.END)
    record_article_stats() 
    notify_multiplayer_result("finished")
    if AUDIO_ENABLED: pygame.mixer.music.stop()
    main_canvas.create_text(center_x, int(screen_h * 0.08), text="YOU HAVE WON！！", font=("Courier New", 28, "bold"), fill="#72d477", justify="center", tags="end_msg")
    root.after(3000, lambda: start_transition("Won"))

#遊戲失敗
def game_over(by_roulette=False, by_timeout=False):
    global game_active, timer_job
    game_active = False  
    if timer_job:
        root.after_cancel(timer_job)
        timer_job = None
    text_display.tag_remove("current_line_bg", "1.0", tk.END)
    record_article_stats() 
    notify_multiplayer_result("dead")
    if AUDIO_ENABLED: pygame.mixer.music.stop()
    main_canvas.create_text(center_x, int(screen_h * 0.08), text="YOU ARE DEAD！！", font=("Courier New", 28, "bold"), fill="#ff4444", justify="center", tags="end_msg")
    root.after(3000, lambda: start_transition("Lost"))


def start_transition(status_type):
    try: main_canvas.delete(text_window_id)
    except: pass
    try: fade_to_black_scene(0, status_type)
    except: pass

def fade_to_black_scene(step, status_type):
    global fade_photo
    try:
        if step == 30: main_canvas.itemconfigure(screen_text_window_id, state="hidden")
        if step <= 40:
            alpha = int(255 * (step / 40.0))
            overlay = Image.new("RGBA", (screen_w, screen_h), (0, 0, 0, alpha))
            fade_photo = ImageTk.PhotoImage(overlay)
            main_canvas.delete("fade_overlay")
            main_canvas.create_image(0, 0, image=fade_photo, anchor="nw", tags="fade_overlay")
            root.after(50, lambda: fade_to_black_scene(step+1, status_type))
        else:
            setup_termination_scene(status_type)
    except: pass

def setup_termination_scene(status_type):
    global termination_time, can_exit
    try:
        if status_type == "Lost" and dead_bg_photo:
            main_canvas.itemconfigure("bg", image=dead_bg_photo)
        main_canvas.delete("table", "kb", "clock", "clock_text", "rank", "rank_text", "revolver", "lives")
        main_canvas.delete("fade_overlay")   
        transition_monitor_to_center()
        show_stats_on_screen(status_type)

        termination_time = 20
        main_canvas.itemconfigure("end_msg", text=f"Terminating in:\n00:{termination_time:02d}")
        main_canvas.itemconfigure("end_msg", fill="#72d477" if status_type=="Won" else "#ff4444")
        main_canvas.tag_raise("end_msg") 
        can_exit = True
        root.after(1000, run_termination_timer)
    except Exception as e: print("轉場發生錯誤:", e)

def run_termination_timer():
    global termination_time
    try:
        termination_time -= 1
        if termination_time > 0:
            main_canvas.itemconfigure("end_msg", text=f"Terminating in:\n00:{termination_time:02d}")
            root.after(1000, run_termination_timer)
        else:
            if can_exit: return_to_menu_transition()
    except: pass

def return_to_menu_transition():
    global can_exit, in_transition, in_ingame_menu
    if in_transition: return
    can_exit = False
    in_transition = True
    in_ingame_menu = False
    main_canvas.delete("ingame_menu_bg", "ingame_btn", "options_ui")
    destroy_options_widgets()
    fade_to_menu_scene(0)

def fade_to_menu_scene(step):
    global fade_photo
    try:
        if step == 20: main_canvas.itemconfigure(screen_text_window_id, state="hidden")
        if step <= 40:
            alpha = int(255 * (step / 40.0))
            overlay = Image.new("RGBA", (screen_w, screen_h), (0, 0, 0, alpha))
            fade_photo = ImageTk.PhotoImage(overlay)
            main_canvas.delete("fade_overlay")
            main_canvas.create_image(0, 0, image=fade_photo, anchor="nw", tags="fade_overlay")
            root.after(30, lambda: fade_to_menu_scene(step+1))
        else:
            main_canvas.delete("all")
            global in_menu
            in_menu = True
            show_main_menu()
            fade_in_menu_scene(30)
    except: pass

def fade_in_menu_scene(step):
    global fade_photo, in_transition
    try:
        if step == 28:
            try: main_canvas.itemconfigure(menu_screen_text_window_id, state="normal")
            except: pass
        if step >= 0:
            alpha = int(255 * (step / 30.0))
            overlay = Image.new("RGBA", (screen_w, screen_h), (0, 0, 0, alpha))
            fade_photo = ImageTk.PhotoImage(overlay)
            main_canvas.delete("fade_overlay")
            main_canvas.create_image(0, 0, image=fade_photo, anchor="nw", tags="fade_overlay")
            root.after(40, lambda: fade_in_menu_scene(step-1))
        else:
            main_canvas.delete("fade_overlay")
            in_transition = False
    except: pass

#Options選單
def destroy_options_widgets():
    global music_scale_widget, sfx_scale_widget
    if music_scale_widget:
        music_scale_widget.destroy()
        music_scale_widget = None
    if sfx_scale_widget:
        sfx_scale_widget.destroy()
        sfx_scale_widget = None

def set_music_vol(val):
    global music_vol
    music_vol = float(val) / 100.0
    apply_volumes()

def set_sfx_vol(val):
    global sfx_vol
    sfx_vol = float(val) / 100.0
    apply_volumes()

def show_options(from_state):
    global in_options_menu, options_previous_state, music_scale_widget, sfx_scale_widget
    in_options_menu = True
    options_previous_state = from_state
    
    if from_state == "main":
        main_canvas.itemconfigure("menu_btn", state="hidden")
        try: main_canvas.itemconfigure(menu_screen_text_window_id, state="hidden")
        except: pass
    elif from_state == "ingame":
        main_canvas.itemconfigure("ingame_btn", state="hidden")
        
    cx = screen_w // 2
    cy = screen_h // 2
    box_w = 600
    box_h = 300
    
    main_canvas.create_rectangle(cx - box_w/2, cy - box_h/2, cx + box_w/2, cy + box_h/2, 
                                 fill="#050505", outline="#FF8C00", width=3, tags="options_ui")
    
    main_canvas.create_text(cx - 180, cy - 40, text="Music", font=("Courier New", 25, "bold"), fill="#ffffff", anchor="w", tags="options_ui")
    main_canvas.create_text(cx - 180, cy + 40, text="Sound", font=("Courier New", 25, "bold"), fill="#ffffff", anchor="w", tags="options_ui")

    music_scale_widget = tk.Scale(main_canvas, from_=0, to=100, orient="horizontal", 
                                  bg="#050505", fg="#FF8C00", font=("Courier New", 15, "bold"),
                                  troughcolor="#222222", activebackground="#FF8C00", 
                                  highlightthickness=0, bd=0, length=200, show=0, command=set_music_vol)
    music_scale_widget.set(int(music_vol * 100))
    main_canvas.create_window(cx + 80, cy - 40, window=music_scale_widget, tags="options_ui")
    
    sfx_scale_widget = tk.Scale(main_canvas, from_=0, to=100, orient="horizontal", 
                                bg="#050505", fg="#FF8C00", font=("Courier New", 15, "bold"),
                                troughcolor="#222222", activebackground="#FF8C00", 
                                highlightthickness=0, bd=0, length=200, show=0, command=set_sfx_vol)
    sfx_scale_widget.set(int(sfx_vol * 100))
    main_canvas.create_window(cx + 80, cy + 40, window=sfx_scale_widget, tags="options_ui")
    
    create_canvas_button(cx, cy + 100, 200, 50, "Back", close_options, ui_tag="options_ui")

def close_options():
    global in_options_menu
    in_options_menu = False
    main_canvas.delete("options_ui")
    destroy_options_widgets()
    
    if options_previous_state == "main":
        main_canvas.itemconfigure("menu_btn", state="normal")
        try: main_canvas.itemconfigure(menu_screen_text_window_id, state="normal")
        except: pass
    elif options_previous_state == "ingame":
        main_canvas.itemconfigure("ingame_btn", state="normal")

#遊戲選單與轉場
def exit_game(event=None):
    stop_multiplayer_network()
    root.destroy()
    
def handle_global_click(event):
    if in_menu or in_transition or in_ingame_menu or in_options_menu: return
    if can_exit: return_to_menu_transition()
    elif game_active and 'text_display' in globals(): text_display.focus_set()

def handle_global_escape(event):
    if in_transition: return
    if in_options_menu:
        close_options()
        return
    if in_menu: pass
    elif game_active: toggle_ingame_menu()
    elif can_exit: return_to_menu_transition()

def create_canvas_button(cx, cy, width, height, text_str, action, ui_tag="menu_btn"):
    bg_id = main_canvas.create_rectangle(
        cx - width/2, cy - height/2, cx + width/2, cy + height/2,
        fill="#000000", outline="", tags=ui_tag
    )
    txt_id = main_canvas.create_text(
        cx, cy, text=text_str, font=("Courier New", 35, "bold"),
        fill="#ffffff", tags=ui_tag
    )
    def on_enter(e):
        main_canvas.itemconfigure(bg_id, fill="#FF8C00")
        main_canvas.itemconfigure(txt_id, fill="#FFD000")
    def on_leave(e):
        main_canvas.itemconfigure(bg_id, fill="#000000")
        main_canvas.itemconfigure(txt_id, fill="#ffffff")
    def on_click(e): action()
    for item_id in (bg_id, txt_id):
        main_canvas.tag_bind(item_id, "<Enter>", on_enter)
        main_canvas.tag_bind(item_id, "<Leave>", on_leave)
        main_canvas.tag_bind(item_id, "<Button-1>", on_click)

def show_multiplayer_menu():
    main_canvas.delete("menu_btn", "multiplayer_ui")
    try: main_canvas.itemconfigure(menu_screen_text_window_id, state="hidden")
    except: pass
    cx = screen_w * 0.25
    main_canvas.create_text(cx, screen_h * 0.38, text="MULTIPLAYER", font=("Courier New", 42, "bold"), fill="#FF8C00", tags="multiplayer_ui")
    main_canvas.create_text(cx, screen_h * 0.48, text=MULTIPLAYER_RULES, font=("Courier New", 13, "bold"), fill="#d9d0c0", justify="left", width=720, tags="multiplayer_ui")
    create_canvas_button(cx, screen_h * 0.68, 500, 70, "Host Game", start_host_lobby, ui_tag="multiplayer_ui")
    create_canvas_button(cx, screen_h * 0.78, 500, 70, "Join Game", join_host_lobby, ui_tag="multiplayer_ui")
    create_canvas_button(cx, screen_h * 0.88, 500, 70, "Back", show_main_menu, ui_tag="multiplayer_ui")

def update_lobby_status():
    if multiplayer_status_text_id:
        players = [player_name] + [client["name"] for client in connected_clients]
        status = f"Hosting on {get_local_ip()}:{MULTIPLAYER_PORT}\nPlayers: {len(players)}\n\n" + "\n".join(f">>> {name}" for name in players)
        main_canvas.itemconfigure(multiplayer_status_text_id, text=status)

def show_multiplayer_lobby(status):
    global multiplayer_status_text_id
    main_canvas.delete("menu_btn", "multiplayer_ui", "lobby_ui")
    try: main_canvas.itemconfigure(menu_screen_text_window_id, state="hidden")
    except: pass
    cx = screen_w * 0.25
    main_canvas.create_text(cx, screen_h * 0.30, text="PRIVATE LOBBY", font=("Courier New", 42, "bold"), fill="#FF8C00", tags="lobby_ui")
    multiplayer_status_text_id = main_canvas.create_text(cx, screen_h * 0.46, text=status, font=("Courier New", 18, "bold"), fill="#72d477", justify="center", width=760, tags="lobby_ui")
    create_canvas_button(cx, screen_h * 0.66, 500, 70, "Start Match", host_start_multiplayer_match, ui_tag="lobby_ui")
    create_canvas_button(cx, screen_h * 0.78, 500, 70, "Back", lambda: [stop_multiplayer_network(), show_multiplayer_menu()], ui_tag="lobby_ui")
    update_lobby_status()

def show_waiting_lobby(status):
    global multiplayer_status_text_id
    main_canvas.delete("menu_btn", "multiplayer_ui", "lobby_ui")
    try: main_canvas.itemconfigure(menu_screen_text_window_id, state="hidden")
    except: pass
    cx = screen_w * 0.25
    main_canvas.create_text(cx, screen_h * 0.32, text="WAITING ROOM", font=("Courier New", 42, "bold"), fill="#FF8C00", tags="lobby_ui")
    multiplayer_status_text_id = main_canvas.create_text(cx, screen_h * 0.52, text=status, font=("Courier New", 17, "bold"), fill="#72d477", justify="center", width=760, tags="lobby_ui")
    create_canvas_button(cx, screen_h * 0.78, 500, 70, "Back", lambda: [stop_multiplayer_network(), show_multiplayer_menu()], ui_tag="lobby_ui")

def toggle_ingame_menu():
    global in_ingame_menu, ingame_overlay_photo
    if not game_active or is_pre_game or is_frozen or is_resting or in_menu or in_transition: return
    
    if in_ingame_menu:
        in_ingame_menu = False
        main_canvas.delete("ingame_menu_bg", "ingame_btn")
        main_canvas.itemconfigure(text_window_id, state="normal")
        main_canvas.itemconfigure(screen_text_window_id, state="normal")
        text_display.focus_set()
    else:
        in_ingame_menu = True
        main_canvas.itemconfigure(text_window_id, state="hidden")
        main_canvas.itemconfigure(screen_text_window_id, state="hidden")
        
        overlay = Image.new("RGBA", (screen_w, screen_h), (0, 0, 0, 200))
        ingame_overlay_photo = ImageTk.PhotoImage(overlay)
        main_canvas.create_image(0, 0, image=ingame_overlay_photo, anchor="nw", tags="ingame_menu_bg")
        
        btn_width = 400
        btn_height = 80
        create_canvas_button(screen_w // 2, screen_h // 2 - 100, btn_width, btn_height, "Continue", toggle_ingame_menu, ui_tag="ingame_btn")
        create_canvas_button(screen_w // 2, screen_h // 2, btn_width, btn_height, "Options", lambda: show_options("ingame"), ui_tag="ingame_btn")
        create_canvas_button(screen_w // 2, screen_h // 2 + 100, btn_width, btn_height, "Exit", exit_to_main_menu_from_ingame, ui_tag="ingame_btn")

def exit_to_main_menu_from_ingame():
    global in_ingame_menu, game_active, in_transition
    if AUDIO_ENABLED: pygame.mixer.music.stop()
    in_ingame_menu = False
    game_active = False
    main_canvas.delete("ingame_menu_bg", "ingame_btn", "options_ui")
    destroy_options_widgets()
    in_transition = True
    fade_to_menu_scene(0)

def play_btn_clicked(multiplayer=False):
    global in_transition, multiplayer_mode, pending_article_indices
    if in_transition: return
    if not multiplayer:
        multiplayer_mode = False
        pending_article_indices = None
        stop_multiplayer_network()
    in_transition = True
    if AUDIO_ENABLED: pygame.mixer.music.fadeout(1300)
    fade_out_menu(0)

def fade_out_menu(step):
    global fade_photo
    try:
        if step == 25:
            if 'menu_screen_text_window_id' in globals(): main_canvas.delete(menu_screen_text_window_id)
            if 'menu_screen_text' in globals(): menu_screen_text.destroy()
        if step <= 40:
            alpha = int(255 * (step / 40.0))
            overlay = Image.new("RGBA", (screen_w, screen_h), (0, 0, 0, alpha))
            fade_photo = ImageTk.PhotoImage(overlay)
            main_canvas.delete("fade_overlay")
            main_canvas.create_image(0, 0, image=fade_photo, anchor="nw", tags="fade_overlay")
            root.after(20, lambda: fade_out_menu(step+1))
        else:
            destroy_options_widgets()
            start_game_from_menu()
            fade_in_game(30) 
    except: pass

def fade_in_game(step):
    global fade_photo, in_transition
    try:
        if step == 8:
            main_canvas.itemconfigure(text_window_id, state="normal")
            text_display.focus_set()
        if step >= 0:
            alpha = int(255 * (step / 30.0))
            overlay = Image.new("RGBA", (screen_w, screen_h), (0, 0, 0, alpha))
            fade_photo = ImageTk.PhotoImage(overlay)
            main_canvas.delete("fade_overlay")
            main_canvas.create_image(0, 0, image=fade_photo, anchor="nw", tags="fade_overlay")
            root.after(30, lambda: fade_in_game(step-1))
        else:
            main_canvas.delete("fade_overlay")
            in_transition = False
            if game_active: text_display.focus_force()
    except: pass

def start_game_from_menu():
    global in_menu, text_display, text_window_id, screen_text, screen_text_window_id
    global first_box_cx, revolver_cx, clock_text_x, clock_text_y, clock_font_size
    in_menu = False
    main_canvas.delete("menu_ui", "menu_btn", "options_ui") 
    destroy_options_widgets()
    main_canvas.delete("all")
    
    global fade_photo
    overlay = Image.new("RGBA", (screen_w, screen_h), (0, 0, 0, 255))
    fade_photo = ImageTk.PhotoImage(overlay)
    
    main_canvas.config(bg="#111111")
    if bg_photo: main_canvas.create_image(0, 0, image=bg_photo, anchor="nw", tags="bg")
    if table_photo: main_canvas.create_image(0, screen_h - int(screen_h * 0.25), image=table_photo, anchor="nw", tags="table")
    if monitor_photo: main_canvas.create_image(screen_w // 2, screen_h - 150, image=monitor_photo, anchor="s", tags="monitor")
    if kb_photo: main_canvas.create_image(screen_w // 2, screen_h - 10, image=kb_photo, anchor="s", tags="kb")
        
    if clock_photo:
        cw, ch = Image.open("clock.png").size
        clock_x = -int(screen_w * 0.05) + 90
        clock_y = (screen_h - int(screen_h * 0.25)) - int(int(screen_w * 0.2) * (ch / cw) * 0.5)
        main_canvas.create_image(clock_x, clock_y, image=clock_photo, anchor="nw", tags="clock")
        clock_text_x = clock_x + int(screen_w * 0.2) * 0.52
        clock_text_y = clock_y + int(int(screen_w * 0.2) * (ch / cw)) * 0.52
        clock_font_size = int(int(int(screen_w * 0.2) * (ch / cw)) * 0.3)
        
    if rank_photo:
        rw, rh = Image.open("rank.png").size
        rank_w = int(screen_w * 0.15)
        rank_h = int(rank_w * (rh / rw))
        rank_x = screen_w - rank_w + int(rank_w * 0.09)
        rank_y = (screen_h - int(screen_h * 0.25)) - int(rank_h * 0.6)
        main_canvas.create_image(rank_x, rank_y, anchor="nw", image=rank_photo, tags="rank")
        rank_text_x = rank_x + rank_w * 0.52
        rank_text_y = rank_y + rank_h * 0.52
        rank_font_size = int(rank_h * 0.55)
        if rank_text_photo: main_canvas.create_image(rank_text_x, rank_text_y, image=rank_text_photo, anchor="center", tags="rank_text")

    text_display = tk.Text(main_canvas, font=("Courier New", 20, "bold"), bg="#161311", bd=0, 
                           highlightthickness=0, width=TEXT_WIDTH, height=6, 
                           spacing1=2, spacing2=0, spacing3=2,
                           padx=25, pady=10, insertbackground="#ffffff", insertwidth=4)
    root.update_idletasks()
    tw = text_display.winfo_reqwidth()
    left_edge = center_x - (tw // 2)
    my_font = tkFont.Font(family="Courier New", size=20, weight="bold")
    char_width = my_font.measure("A") 
    real_text_left_x = left_edge + 25 + (START_INDEX * char_width)
    first_box_cx = real_text_left_x + 16
    revolver_cx = real_text_left_x - 38

    global text_window_id
    text_window_id = main_canvas.create_window(center_x, base_y, window=text_display, anchor="n", state="hidden")

    text_display.tag_config("correct", foreground="#72d477") 
    text_display.tag_config("pending", foreground="#A07431") 
    text_display.tag_config("error", foreground="#ff4444")
    text_display.tag_config("wrong_bg", background="#770000") 
    text_display.tag_config("current_line_bg", background="#423d3a") 
    text_display.tag_config("loading_bar_bg", foreground="#222222")  
    text_display.tag_config("loading_bar_fill", foreground="#d28c00") 

    current_tags = text_display.bindtags()
    new_tags = tuple(tag for tag in current_tags if tag != "Text")
    text_display.bindtags(new_tags)

    screen_text = tk.Text(main_canvas, font=("Courier New", 8, "bold"), bg="#050505", fg="#72d477", bd=0, 
                           highlightthickness=0, padx=10, pady=10, state=tk.DISABLED)
    screen_text.bindtags(new_tags) 
    screen_text.tag_config("tag_won", background="#72d477", foreground="#000000")
    screen_text.tag_config("tag_dead", background="#ff4444", foreground="#000000")

    global screen_text_window_id
    screen_text_window_id = main_canvas.create_window(
        center_x, screen_h - 150 - int(monitor_h * 0.58), 
        window=screen_text, anchor="center", width=inner_screen_w, height=inner_screen_h   
    )

    main_canvas.create_text(center_x, screen_h * 0.95, text="--點擊畫面任意位置離開--", 
                            font=("Courier New", 16, "bold"), fill="#ffffff", tags="exit_prompt", state="hidden")
    main_canvas.create_image(0, 0, image=fade_photo, anchor="nw", tags="fade_overlay")
    text_display.bind("<Key>", handle_keypress)
    root.bind("<FocusIn>", lambda e: text_display.focus_set() if game_active else None)
    
    update_hud()
    initialize_game(pending_article_indices)

def show_main_menu():
    main_canvas.delete("all")
    main_canvas.config(bg="#000000")
    if AUDIO_ENABLED: pygame.mixer.music.play(-1)
    if table_photo: main_canvas.create_image(0, screen_h - int(screen_h * 0.25), image=table_photo, anchor="nw", tags="menu_ui")
        
    global menu_monitor_photo, menu_screen_text, menu_screen_text_window_id
    menu_scale = 2
    menu_m_w = int(monitor_w * menu_scale)
    menu_m_h = int(monitor_h * menu_scale)
    
    try:
        img_monitor_menu = Image.open("screen.png").resize((menu_m_w, menu_m_h))
        menu_monitor_photo = ImageTk.PhotoImage(img_monitor_menu)
        menu_monitor_x = screen_w * 0.72
        main_canvas.create_image(menu_monitor_x, screen_h + 10, image=menu_monitor_photo, anchor="s", tags="menu_ui")
        
        menu_screen_text = tk.Text(main_canvas, font=("Courier New", 28, "bold"), bg="#050505", fg="#72d477", bd=0, 
                               highlightthickness=0, padx=10, pady=10, state=tk.NORMAL)
        menu_tags = menu_screen_text.bindtags()
        menu_screen_text.bindtags(tuple(t for t in menu_tags if t != "Text"))
        menu_screen_text.insert(tk.END, ">>> TYPE AS FAST AS YOU CAN!\n\n\n>>> Or\n\n\n>>> You will DIE!!!\n\n\n>>> Good Luck!!!")
        menu_screen_text.config(state=tk.DISABLED)
        
        m_inner_w = int(inner_screen_w * menu_scale)
        m_inner_h = int(inner_screen_h * menu_scale)
        menu_screen_text_y = (screen_h + 10) - int(menu_m_h * 0.58) 
        
        menu_screen_text_window_id = main_canvas.create_window(
            menu_monitor_x, menu_screen_text_y, 
            window=menu_screen_text, anchor="center", width=m_inner_w, height=m_inner_h, state="hidden" 
        )
    except Exception as e: print("Menu Monitor loading error:", e)
        
    title_font = tkFont.Font(family="Courier New", size=70, weight="bold")
    char_w = title_font.measure("A")
    char_h = title_font.metrics("linespace")
    
    start_x = (screen_w * 0.25) - (14 * char_w) / 2
    title_y = screen_h * 0.25

    main_canvas.create_rectangle(start_x, title_y - char_h/2, start_x + char_w, title_y + char_h/2, fill="#FF3737", outline="", tags="menu_ui")
    main_canvas.create_text(start_x, title_y, text="F", font=("Courier New", 70, "bold"), fill="#FF8C00", anchor="w", tags="menu_ui")
    start_x += char_w
    main_canvas.create_text(start_x, title_y, text="inal ", font=("Courier New", 70, "bold"), fill="#FF8C00", anchor="w", tags="menu_ui")
    start_x += char_w * 5
    main_canvas.create_rectangle(start_x, title_y - char_h/2, start_x + char_w, title_y + char_h/2, fill="#FF3737", outline="", tags="menu_ui")
    main_canvas.create_text(start_x, title_y, text="S", font=("Courier New", 70, "bold"), fill="#FF8C00", anchor="w", tags="menu_ui")
    start_x += char_w
    main_canvas.create_text(start_x, title_y, text="entence", font=("Courier New", 70, "bold"), fill="#FF8C00", anchor="w", tags="menu_ui")

    btn_width = 500
    btn_height = 80
    create_canvas_button(screen_w * 0.25, screen_h * 0.40, btn_width, btn_height, "Single Player", play_btn_clicked, ui_tag="menu_btn")
    create_canvas_button(screen_w * 0.25, screen_h * 0.51, btn_width, btn_height, "Multiplayer", show_multiplayer_menu, ui_tag="menu_btn")
    create_canvas_button(screen_w * 0.25, screen_h * 0.62, btn_width, btn_height, "Options", lambda: show_options("main"), ui_tag="menu_btn")
    create_canvas_button(screen_w * 0.25, screen_h * 0.73, btn_width, btn_height, "Exit", exit_game, ui_tag="menu_btn")

#遊戲視窗
root = tk.Tk()
root.title("Final Sentence")
root.attributes("-fullscreen", True)

root.update_idletasks()
screen_w = root.winfo_screenwidth()
screen_h = root.winfo_screenheight()
center_x = screen_w // 2
base_y = int(screen_h * 0.20)

monitor_w = int(screen_w * 0.5)
monitor_h = int(screen_h * 0.45)
inner_screen_w = int(monitor_w * 0.35)  
inner_screen_h = int(monitor_h * 0.51)  

main_canvas = tk.Canvas(root, width=screen_w, height=screen_h, highlightthickness=0, bg="#111111", bd=0)
main_canvas.pack(fill=tk.BOTH, expand=True)

try:
    img_bg = Image.open("room.png").resize((screen_w, screen_h))
    bg_photo = ImageTk.PhotoImage(img_bg)
    table_h = int(screen_h * 0.25)
    img_table = Image.open("table.png").resize((screen_w, table_h))
    table_photo = ImageTk.PhotoImage(img_table)
    img_monitor = Image.open("screen.png").resize((monitor_w, monitor_h))
    monitor_photo = ImageTk.PhotoImage(img_monitor)
    try:
        orig_kb = Image.open("kb.png")
        orig_kw, orig_kh = orig_kb.size
        kb_w = int(screen_w * 0.35)  
        kb_h = int(kb_w * (orig_kh / orig_kw)) 
        img_kb = orig_kb.resize((kb_w, kb_h))
        kb_photo = ImageTk.PhotoImage(img_kb)
    except Exception as e: print(f"鍵盤圖片載入失敗 (kb.png): {e}")

    orig_clock = Image.open("clock.png")
    orig_cw, orig_ch = orig_clock.size
    clock_w = int(screen_w * 0.2)
    clock_h = int(clock_w * (orig_ch / orig_cw)) 
    img_clock = orig_clock.resize((clock_w, clock_h))
    clock_photo = ImageTk.PhotoImage(img_clock)

    orig_rank = Image.open("rank.png")
    orig_rw, orig_rh = orig_rank.size
    rank_w = int(screen_w * 0.15) 
    rank_h = int(rank_w * (orig_rh / orig_rw)) 
    img_rank = orig_rank.resize((rank_w, rank_h))
    rank_photo = ImageTk.PhotoImage(img_rank)
    rank_font_size = int(rank_h * 0.55)
    rank_text_photo = create_rotated_text_image(str(player_id), rank_font_size, "#1a1a1a", -10, font_file="timesbd.ttf")

    try:
        orig_blood = Image.open("dead.png").convert("RGB")
        img_blood = orig_blood.resize((screen_w, screen_h))
        dead_bg_photo = ImageTk.PhotoImage(img_blood)
    except Exception as e:
        print(f"圖片載入失敗 (dead.png): {e}")
        img_blood = Image.new("RGB", (screen_w, screen_h), (80, 0, 0)) 
        dead_bg_photo = ImageTk.PhotoImage(img_blood)
        
    black_screen = Image.new("RGB", (screen_w, screen_h), (0, 0, 0))

except Exception as e:
    print(f"圖片載入失敗，請確認檔名與路徑是否正確: {e}")

root.bind("<Button-1>", handle_global_click)
root.bind("<Escape>", handle_global_escape)

show_main_menu()
poll_network_events()

if 'menu_screen_text_window_id' in globals():
    try: main_canvas.itemconfigure(menu_screen_text_window_id, state="normal")
    except: pass

root.mainloop()
