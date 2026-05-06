import tkinter as tk 
import tkinter .font as tkFont 
import tkinter .simpledialog as simpledialog 
import tkinter .messagebox as messagebox 
import random 
import math 
import socket 
import threading 
import queue 
from time import monotonic
from PIL import Image ,ImageTk 

from .audio import AudioManager 
from .image_tools import create_rotated_text_image 
from .leaderboard import LeaderboardStore, create_entry
from .models import AssetStore ,GameState ,LayoutState ,MenuState ,MultiplayerState ,SettingsState ,StatsState ,WidgetStore 
from .network import get_local_ip ,read_json_lines ,send_json 
from .paths import image_path 
from .texts import MULTIPLAYER_RULES ,PREDEFINED_TEXTS ,format_article_text 

settings =SettingsState ()
game =GameState ()
menu =MenuState ()
multiplayer =MultiplayerState ()
stats =StatsState ()
layout =LayoutState ()
assets =AssetStore ()
widgets =WidgetStore ()

#Pygame音效
audio =AudioManager ()
leaderboard = LeaderboardStore()

#音量變數(預設100%)
settings .music_vol =1.0 
settings .sfx_vol =1.0 

#音量同步函數
def apply_volumes ():
# Sync music and sound effect volumes.
    audio .music_vol =settings .music_vol 
    audio .sfx_vol =settings .sfx_vol 
    audio .apply_volumes ()

apply_volumes ()

#遊戲狀態與排版變數
game .articles =[]
game .current_article_idx =0 
game .current_index =0 
game .mistakes =0 
game .max_mistakes =3 
game .bullets_loaded =0 

game .chambers =[False ]*6 

game .game_active =False 
game .is_frozen =False 
game .is_resting =False 

game .is_pre_game =False 
game .pre_game_time =5 
game .termination_time =20 
game .can_exit =False 
game .in_menu =True 
game .in_transition =False 

#選單狀態
menu .in_ingame_menu =False 
menu .ingame_overlay_photo =None 
menu .in_options_menu =False 
menu .options_previous_state =None 
menu .music_scale_widget =None 
menu .sfx_scale_widget =None 

#多人連線狀態
MULTIPLAYER_PORT =50505 
multiplayer .multiplayer_mode =False 
multiplayer .is_host =False 
multiplayer .player_name ="Player"
multiplayer .host_socket =None 
multiplayer .server_socket =None 
multiplayer .client_threads =[]
multiplayer .connected_clients =[]
multiplayer .network_queue =queue .Queue ()
multiplayer .pending_article_indices =None 
multiplayer .multiplayer_status_text_id =None 
multiplayer .match_finished =False 

stats .total_chars_typed =0 
stats .total_mistakes =0 
stats .total_typing_time =0 
stats .article_chars =0 
stats .article_mistakes =0 
stats .wpm_list =[]
stats .acc_list =[]

game .loading_progress =0 
game .scroll_job =None 
game .roulette_revealed =False 

game .time_left =240 
game .timer_job =None 
game .player_id =1 

assets .bg_photo =None 
assets .dead_bg_photo =None 
assets .table_photo =None 
assets .monitor_photo =None 
assets .term_monitor_photo =None 
assets .menu_monitor_photo =None 
assets .kb_photo =None 
assets .clock_photo =None 
assets .rank_photo =None 

assets .img_blood =None 
assets .black_screen =None 
assets .fade_photo =None 
assets .blood_photo =None 
widgets .text_window_id =None 
widgets .screen_text_window_id =None 

assets .clock_text_photo =None 
assets .rank_text_photo =None 

layout .left_edge =0 
layout .center_x =0 
layout .base_y =0 

layout .first_box_cx =0 
layout .revolver_cx =0 

layout .clock_text_x =0 
layout .clock_text_y =0 
layout .clock_font_size =20 

game .current_bar_width =40 

TEXT_WIDTH =48 
START_INDEX =3 
PREFIX_SPACES =" "*START_INDEX 

def get_article_text (raw_text ):
# Format a passage for the typing widget.
    return format_article_text (raw_text ,PREFIX_SPACES )

def queue_network_event (event ):
# Queue a network event for the Tk thread.
    multiplayer .network_queue .put (event )

def poll_network_events ():
# Process queued network events periodically.
    try :
        while True :
            event =multiplayer .network_queue .get_nowait ()
            handle_network_event (event )
    except queue .Empty :
        pass 
    widgets .root .after (100 ,poll_network_events )

def stop_multiplayer_network ():
# Close all active multiplayer sockets.
    for client in multiplayer .connected_clients :
        try :client ["sock"].close ()
        except OSError :pass 
    multiplayer .connected_clients =[]
    if multiplayer .host_socket :
        try :multiplayer .host_socket .close ()
        except OSError :pass 
    if multiplayer .server_socket :
        try :multiplayer .server_socket .close ()
        except OSError :pass 
    multiplayer .host_socket =None 
    multiplayer .server_socket =None 
    multiplayer .client_threads =[]
    multiplayer .is_host =False 

def broadcast_to_clients (payload ):
# Send a payload to all connected clients.
    alive_clients =[]
    for client in multiplayer .connected_clients :
        if send_json (client ["sock"],payload ):
            alive_clients .append (client )
    multiplayer .connected_clients [:]=alive_clients 

def host_accept_loop ():
# Accept clients while hosting a lobby.
    while multiplayer .server_socket :
        try :
            sock ,addr =multiplayer .server_socket .accept ()
            client ={"sock":sock ,"addr":addr ,"name":f"Player {len (multiplayer .connected_clients )+2 }","alive":True }
            multiplayer .connected_clients .append (client )
            def on_message (msg ,client_ref =client ):
            # Handle one message from a joined client.
                if msg .get ("type")=="hello":
                    client_ref ["name"]=msg .get ("name",client_ref ["name"])
                    queue_network_event ({"type":"lobby_update"})
                elif msg .get ("type")in ("finished","dead"):
                    queue_network_event ({"type":"remote_result","name":client_ref ["name"],"result":msg .get ("type")})
            threading .Thread (target =read_json_lines ,args =(sock ,on_message ),daemon =True ).start ()
            send_json (sock ,{"type":"welcome","rules":MULTIPLAYER_RULES })
            queue_network_event ({"type":"lobby_update"})
        except OSError :
            break 

def client_listen_loop (sock ):
# Listen for host messages on a client.
    read_json_lines (sock ,queue_network_event )
    queue_network_event ({"type":"connection_closed"})

def start_host_lobby ():
# Create a multiplayer host lobby.
    stop_multiplayer_network ()
    name =simpledialog .askstring ("Host Multiplayer","Your player name:",initialvalue ="Host")
    if not name :return 
    multiplayer .player_name =name 
    multiplayer .multiplayer_mode =True 
    multiplayer .is_host =True 
    multiplayer .connected_clients =[]
    try :
        multiplayer .server_socket =socket .socket (socket .AF_INET ,socket .SOCK_STREAM )
        multiplayer .server_socket .setsockopt (socket .SOL_SOCKET ,socket .SO_REUSEADDR ,1 )
        multiplayer .server_socket .bind (("",MULTIPLAYER_PORT ))
        multiplayer .server_socket .listen ()
        threading .Thread (target =host_accept_loop ,daemon =True ).start ()
        show_multiplayer_lobby (f"Hosting on {get_local_ip ()}:{MULTIPLAYER_PORT }")
    except OSError as e :
        messagebox .showerror ("Socket Error",f"Cannot host game:\n{e }")
        stop_multiplayer_network ()

def join_host_lobby ():
# Connect to a multiplayer host lobby.
    stop_multiplayer_network ()
    name =simpledialog .askstring ("Join Multiplayer","Your player name:",initialvalue ="Player")
    if not name :return 
    host_ip =simpledialog .askstring ("Join Multiplayer","Host IP:",initialvalue ="127.0.0.1")
    if not host_ip :return 
    multiplayer .player_name =name 
    multiplayer .multiplayer_mode =True 
    multiplayer .is_host =False 
    try :
        multiplayer .host_socket =socket .socket (socket .AF_INET ,socket .SOCK_STREAM )
        multiplayer .host_socket .connect ((host_ip ,MULTIPLAYER_PORT ))
        send_json (multiplayer .host_socket ,{"type":"hello","name":multiplayer .player_name })
        threading .Thread (target =client_listen_loop ,args =(multiplayer .host_socket ,),daemon =True ).start ()
        show_waiting_lobby (f"Connected to {host_ip }:{MULTIPLAYER_PORT }\nWaiting for host...")
    except OSError as e :
        messagebox .showerror ("Socket Error",f"Cannot join game:\n{e }")
        stop_multiplayer_network ()

def host_start_multiplayer_match ():
# Start a shared multiplayer match.
    if not multiplayer .is_host :return 
    multiplayer .pending_article_indices =random .sample (range (len (PREDEFINED_TEXTS )),5 )
    multiplayer .match_finished =False 
    multiplayer .remote_progress ={}
    for client in multiplayer .connected_clients :
        client ["alive"]=True 
    broadcast_to_clients ({"type":"start","article_indices":multiplayer .pending_article_indices })
    play_btn_clicked (is_multiplayer_start =True )

def notify_multiplayer_result (result ):
# Report this player result to the match.
    if not multiplayer .multiplayer_mode or multiplayer .match_finished :
        return 
    multiplayer .match_finished =True 
    payload ={"type":result ,"name":multiplayer .player_name }
    if multiplayer .is_host :
        broadcast_to_clients ({"type":"match_result","winner":multiplayer .player_name if result =="finished"else None ,"reason":result })
    elif multiplayer .host_socket :
        send_json (multiplayer .host_socket ,payload )

def handle_network_event (event ):
# Apply a network event to the UI state.
    event_type =event .get ("type")
    if event_type =="lobby_update":
        update_lobby_status ()
    elif event_type =="welcome":
        show_waiting_lobby ("Connected.\nWaiting for host...\n\n"+event .get ("rules",""))
    elif event_type =="start":
        multiplayer .pending_article_indices =event .get ("article_indices")
        multiplayer .match_finished =False 
        multiplayer .remote_progress ={}
        play_btn_clicked (is_multiplayer_start =True )
    elif event_type =="progress":
        if event .get ("name")!=multiplayer .player_name :
            multiplayer .remote_progress [event .get ("name","Player")]=event .get ("percent",0.0 )
            update_hud ()
    elif event_type =="remote_result":
        name =event .get ("name","Player")
        result =event .get ("result")
        if result =="finished":
            broadcast_to_clients ({"type":"match_result","winner":name ,"reason":"finished"})
            if game .game_active :
                game_over ()
        elif result =="dead":
            for client in multiplayer .connected_clients :
                if client ["name"]==name :
                    client ["alive"]=False 
            multiplayer .remote_progress .pop (name ,None )
            if game .game_active and multiplayer .connected_clients and all (not client .get ("alive",True )for client in multiplayer .connected_clients ):
                game_win ()
    elif event_type =="match_result":
        winner =event .get ("winner")
        if winner and winner !=multiplayer .player_name and game .game_active :
            widgets .main_canvas .create_text (layout .center_x ,int (layout .screen_h *0.08 ),text =f"{winner } has finished first.",font =("Courier New",24 ,"bold"),fill ="#ff4444",justify ="center",tags ="end_msg")
            game_over ()
    elif event_type =="connection_closed":
        if multiplayer .multiplayer_mode and game .in_menu :
            show_waiting_lobby ("Connection closed.\nReturn to menu and try again.")

def record_article_stats ():
# Record WPM and accuracy for one passage.
    time_spent =240 -game .time_left 
    if time_spent <=0 :time_spent =1 
    stats .total_typing_time +=time_spent 
    wpm =(stats .article_chars /5.0 )/(time_spent /60.0 )if stats .article_chars >0 else 0 
    total_attempts =stats .article_chars +stats .article_mistakes 
    acc =(stats .article_chars /total_attempts *100.0 )if total_attempts >0 else 0.0 
    if total_attempts >0 :
        stats .wpm_list .append (int (wpm ))
        stats .acc_list .append (round (acc ,1 ))
    stats .article_chars =0 
    stats .article_mistakes =0 

def initialize_game (article_indices =None ):
# Reset state and load passages for a match.

    if article_indices :
        selected_texts =[PREDEFINED_TEXTS [i ]for i in article_indices ]
    else :
        selected_texts =random .sample (PREDEFINED_TEXTS ,5 )
    game .articles =[get_article_text (text )for text in selected_texts ]
    game .current_article_idx =0 
    game .current_index =START_INDEX 
    game .chambers =[False ]*6 
    game .bullets_loaded =0 
    game .roulette_revealed =False 
    game .game_active =True 
    game .can_exit =False 
    game .mistakes =0 
    game .is_frozen =False 
    game .is_resting =False 
    menu .in_ingame_menu =False 
    menu .in_options_menu =False 
    game .loading_progress =0 
    stats .total_chars_typed =0 
    stats .total_mistakes =0 
    stats .total_typing_time =0 
    stats .article_chars =0 
    stats .article_mistakes =0 
    stats .wpm_list =[]
    stats .acc_list =[]
    multiplayer .remote_progress ={}
    game .leaderboard_saved = False
    game .current_combo =0 
    game .max_combo =0 
    game .last_judgement ="Ready"
    game .last_hit_time =monotonic ()
    game .is_pre_game =True 
    game .pre_game_time =5 
    game .time_left =240 

    if game .timer_job :
        widgets .root .after_cancel (game .timer_job )
        game .timer_job =None 

    widgets .text_display .delete ("1.0",tk .END )

    try :
        widgets .screen_text .config (state =tk .NORMAL )
        widgets .screen_text .delete ("1.0",tk .END )
        widgets .screen_text .insert (tk .END ,PREFIX_SPACES )
        widgets .screen_text .config (state =tk .DISABLED )
    except :
        pass 

    for i ,content in enumerate (game .articles ):
        start_mark =f"art_{i }_start"
        idx =widgets .text_display .index ("end-1c")
        widgets .text_display .mark_set (start_mark ,idx )
        widgets .text_display .mark_gravity (start_mark ,tk .LEFT )
        widgets .text_display .insert (tk .END ,content ,"pending")
        if i <4 :
            bar_mark =f"bar_{i }_start"
            idx =widgets .text_display .index ("end-1c")
            widgets .text_display .mark_set (bar_mark ,idx )
            widgets .text_display .mark_gravity (bar_mark ,tk .LEFT )
            widgets .text_display .insert (tk .END ,"\n")

    widgets .text_display .insert (tk .END ,"\n"*20 )
    widgets .text_display .yview_moveto (0 )
    widgets .text_display .mark_set ("insert",f"art_0_start + {START_INDEX } chars")
    widgets .text_display .see ("insert")
    update_line_highlight ()
    update_hud ()
    update_clock_display ()
    broadcast_progress_update ()

    widgets .main_canvas .delete ("pre_game_text")
    widgets .main_canvas .create_text (layout .center_x ,int (layout .screen_h *0.08 ),text ="Game starts in:\n00:05",
    font =("Courier New",20 ,"bold"),fill ="#72d477",justify ="center",tags ="pre_game_text")

    game .timer_job =widgets .root .after (1000 ,run_pre_game_timer )

    #UI與左輪手槍
def draw_revolver (rotation_index =0 ):
# Draw the roulette cylinder HUD.
    widgets .main_canvas .delete ("revolver")
    if not game .roulette_revealed :return 

    cx =layout .revolver_cx 
    cy =layout .base_y -45 

    widgets .main_canvas .create_oval (cx -28 ,cy -28 ,cx +28 ,cy +28 ,fill ="#1a1a1a",outline ="#0a0a0a",width =2 ,tags ="revolver")
    widgets .main_canvas .create_oval (cx -4 ,cy -4 ,cx +4 ,cy +4 ,fill ="#0a0a0a",tags ="revolver")

    for i in range (6 ):
        angle =math .radians (i *60 -90 )
        bx =cx +16 *math .cos (angle )
        by =cy +16 *math .sin (angle )

        logical_index =(i -rotation_index )%6 
        is_loaded =game .chambers [logical_index ]

        widgets .main_canvas .create_oval (bx -6 ,by -6 ,bx +6 ,by +6 ,fill ="#050505",outline ="#2a2a2a",tags ="revolver")
        if is_loaded :
            widgets .main_canvas .create_oval (bx -4 ,by -4 ,bx +4 ,by +4 ,fill ="#aa1111",outline ="#ff4444",tags ="revolver")

def draw_lives ():
# Draw the current mistake boxes.
    widgets .main_canvas .delete ("lives")
    cy =layout .base_y -45 
    for i in range (game .max_mistakes ):
        cx =layout .first_box_cx +(i *40 )
        if i <game .mistakes :
            bg_color ="#550000"
            outline_color ="#880000"
            char ="X"
        else :
            bg_color ="#111111"
            outline_color ="#5a4a36"
            char =""
        widgets .main_canvas .create_rectangle (cx -16 ,cy -16 ,cx +16 ,cy +16 ,fill =bg_color ,outline =outline_color ,width =2 ,tags ="lives")
        if char :
            widgets .main_canvas .create_text (cx ,cy ,text =char ,fill ="#ff4444",font =("Courier New",18 ,"bold"),tags ="lives")

def update_hud ():
# Refresh the roulette and lives HUD.
    draw_revolver (0 )
    draw_lives ()
    draw_feedback_hud ()

def draw_feedback_hud ():
# Draw combo, judgement, and multiplayer progress text.
    widgets .main_canvas .delete ("feedback_hud")
    combo_color ="#ffd54a"if game .current_combo >0 else "#8e8a80"
    widgets .main_canvas .create_text (
    layout .center_x ,
    max (30 ,layout .base_y -70 ),
    text =f"{game .last_judgement }   Combo x{game .current_combo }",
    font =("Courier New",20 ,"bold"),
    fill =combo_color ,
    tags ="feedback_hud"
    )
    if multiplayer .multiplayer_mode and multiplayer .remote_progress :
        progress_lines =[]
        for name ,percent in multiplayer .remote_progress .items ():
            progress_lines .append (f"{name }: {percent :>5.1f}%")
        widgets .main_canvas .create_text (
        layout .screen_w -120 ,
        max (90 ,layout .base_y +10 ),
        text ="\n".join (progress_lines ),
        font =("Courier New",14 ,"bold"),
        fill ="#72d477",
        justify ="right",
        tags ="feedback_hud"
        )

def judge_hit_timing ():
# Grade the latest correct keypress by rhythm timing.
    now =monotonic ()
    delta =now -game .last_hit_time 
    game .last_hit_time =now 
    if delta <=0.22 :
        return "Perfect"
    if delta <=0.45 :
        return "Good"
    return "Good"

def register_hit_feedback ():
# Update combo and judgement after a correct keypress.
    game .last_judgement =judge_hit_timing ()
    game .current_combo +=1 
    if game .current_combo >game .max_combo :
        game .max_combo =game .current_combo 
    update_hud ()

def register_miss_feedback ():
# Reset combo and mark the latest judgement as a miss.
    game .last_judgement ="Miss"
    game .current_combo =0 
    update_hud ()

def compute_progress_percent ():
# Convert local article progress into a single completion percentage.
    completed_articles =game .current_article_idx 
    article_total =len (game .articles )or 1 
    current_article =game .articles [game .current_article_idx ]if game .articles and game .current_article_idx <len (game .articles )else ""
    current_ratio =(game .current_index /len (current_article ))if current_article else 0.0 
    return min (100.0 ,((completed_articles +current_ratio )/article_total )*100.0 )

def broadcast_progress_update ():
# Send the local progress percent to other multiplayer players.
    if not multiplayer .multiplayer_mode :
        return
    payload ={"type":"progress","name":multiplayer .player_name ,"percent":round (compute_progress_percent (),1 )}
    if multiplayer .is_host :
        handle_network_event (payload )
        broadcast_to_clients (payload )
    elif multiplayer .host_socket :
        send_json (multiplayer .host_socket ,payload )

def shake_screen (strength =14 ,steps =8 ):
# Apply a short camera shake to the main canvas.
    if widgets .main_canvas is None :
        return
    if game .shake_job :
        widgets .root .after_cancel (game .shake_job )
        game .shake_job =None 
    game .shake_offset_x =0 
    game .shake_offset_y =0 

    def step_shake (remaining ):
    # Advance one shake step and restore the canvas at the end.
        if remaining <=0 :
            widgets .main_canvas .move ("all",-game .shake_offset_x ,-game .shake_offset_y )
            game .shake_offset_x =0 
            game .shake_offset_y =0 
            game .shake_job =None 
            return
        widgets .main_canvas .move ("all",-game .shake_offset_x ,-game .shake_offset_y )
        game .shake_offset_x =random .randint (-strength ,strength )
        game .shake_offset_y =random .randint (-strength //2 ,strength //2 )
        widgets .main_canvas .move ("all",game .shake_offset_x ,game .shake_offset_y )
        game .shake_job =widgets .root .after (18 ,lambda :step_shake (remaining -1 ))

    step_shake (steps )

def run_pre_game_timer ():
# Run the pre-game countdown.
    if not game .game_active :return 
    game .pre_game_time -=1 
    if game .pre_game_time >0 :
        widgets .main_canvas .itemconfigure ("pre_game_text",text =f"Game starts in:\n00:0{game .pre_game_time }")
        game .timer_job =widgets .root .after (1000 ,run_pre_game_timer )
    else :
        widgets .main_canvas .delete ("pre_game_text")
        game .is_pre_game =False 
        run_timer ()

def run_timer ():
# Run the per-passage countdown timer.
    if not game .game_active :return 

    if not game .is_frozen and not game .is_resting :
        game .time_left -=1 
        audio .play ("tick")

        if game .time_left <=0 :
            game .time_left =0 
            update_clock_display ()
            if menu .in_options_menu :close_options ()
            if menu .in_ingame_menu :
                menu .in_ingame_menu =False 
                widgets .main_canvas .delete ("ingame_menu_bg","ingame_btn")
                widgets .main_canvas .itemconfigure (widgets .text_window_id ,state ="normal")
                widgets .main_canvas .itemconfigure (widgets .screen_text_window_id ,state ="normal")
            game_over (by_timeout =True )
            return 

    update_clock_display ()
    game .timer_job =widgets .root .after (1000 ,run_timer )

    #旋轉文字圖片(時鐘、名牌)
def update_clock_display ():
# Update the clock image text.
    mins =game .time_left //60 
    secs =game .time_left %60 
    time_str =f"{mins :02d}:{secs :02d}"

    widgets .main_canvas .delete ("clock_text")
    assets .clock_text_photo =create_rotated_text_image (time_str ,layout .clock_font_size ,"#ffffff",2 ,font_file ="courbd.ttf")
    widgets .main_canvas .create_image (layout .clock_text_x ,layout .clock_text_y ,image =assets .clock_text_photo ,anchor ="center",tags ="clock_text")

    if menu .in_ingame_menu :
        widgets .main_canvas .tag_raise ("ingame_menu_bg")
        widgets .main_canvas .tag_raise ("ingame_btn")
    if menu .in_options_menu :
        widgets .main_canvas .tag_raise ("options_ui")

        #遊戲邏輯與滾動動畫
def start_roulette ():
# Load a chamber and start roulette.
    game .roulette_revealed =True 
    game .is_frozen =True 
    audio .play ("spin")
    shake_screen (18 ,10 )

    empty_chambers =[i for i ,loaded in enumerate (game .chambers )if not loaded ]
    if empty_chambers :
        chosen =random .choice (empty_chambers )
        game .chambers [chosen ]=True 
        game .bullets_loaded +=1 

    target_chamber =random .randint (0 ,5 )
    final_rotation =(-target_chamber )%6 
    total_spins =random .randint (3 ,5 )*6 
    total_steps =total_spins +final_rotation 
    animate_spin (0 ,total_steps ,target_chamber )

def animate_spin (current_step ,total_steps ,target_chamber ):
# Animate the roulette cylinder spin.
    draw_revolver (current_step %6 )
    if current_step <total_steps :
        progress =current_step /total_steps 
        delay =int (20 +200 *(progress **3 ))
        widgets .root .after (delay ,lambda :animate_spin (current_step +1 ,total_steps ,target_chamber ))
    else :
        widgets .root .after (500 ,lambda :resolve_roulette (target_chamber ))

def resolve_roulette (target_chamber ):
# Resolve the roulette result.
    if game .chambers [target_chamber ]:
        audio .play ("shoot")
        game_over (by_roulette =True )
    else :
        audio .play ("click")
        game .mistakes =0 
        update_hud ()
        target_content =game .articles [game .current_article_idx ]
        line_start_idx =target_content .rfind ('\n',0 ,game .current_index )
        new_index =(0 if line_start_idx ==-1 else line_start_idx +1 )+START_INDEX 
        show_error_and_reset (new_index )

def perform_smooth_scroll (current_y ,target_y ,step ,total_steps =15 ):
# Animate text scrolling to a target.
    if step >=total_steps :
        widgets .text_display .yview_moveto (target_y )
        game .scroll_job =None 
        widgets .text_display .see ("insert")
        return 
    progress =step /total_steps 
    ease =1 -(1 -progress )**2 
    new_y =current_y +(target_y -current_y )*ease 
    widgets .text_display .yview_moveto (new_y )
    game .scroll_job =widgets .root .after (16 ,lambda :perform_smooth_scroll (current_y ,target_y ,step +1 ,total_steps ))

def scroll_one_line_down ():
# Scroll the typing area down one line.
    if game .scroll_job :widgets .root .after_cancel (game .scroll_job )
    widgets .text_display .update_idletasks ()
    current_y =widgets .text_display .yview ()[0 ]
    widgets .text_display .yview_scroll (1 ,"units")
    target_y =widgets .text_display .yview ()[0 ]
    if abs (target_y -current_y )>0.0001 :
        widgets .text_display .yview_moveto (current_y )
        perform_smooth_scroll (current_y ,target_y ,1 )

def handle_keypress (event ):
# Validate each player keypress.

    if game .can_exit :
        return_to_menu_transition ()
        return "break"

    if event .keysym =='Escape':
        if menu .in_options_menu :
            close_options ()
            return "break"
        toggle_ingame_menu ()
        return "break"

    if not game .game_active or game .is_frozen or game .is_resting or game .is_pre_game or game .in_menu or game .in_transition or menu .in_ingame_menu or menu .in_options_menu :
        return "break"

    if event .keysym in ('Shift_L','Shift_R','Caps_Lock','Control_L','Control_R','Alt_L','Alt_R'):return "break"

    char =event .char 
    if event .keysym =="Return":char ="\n"
    if not char :return "break"

    target_content =game .articles [game .current_article_idx ]
    expected_char =target_content [game .current_index ]
    mark_start =f"art_{game .current_article_idx }_start"

    if char =='\n'and expected_char ==' 'and game .current_index +1 <len (target_content )and target_content [game .current_index +1 ]=='\n':
        widgets .text_display .tag_remove ("pending",f"{mark_start } + {game .current_index } chars")
        widgets .text_display .tag_add ("correct",f"{mark_start } + {game .current_index } chars")
        game .current_index +=1 
        expected_char ='\n'

    if char ==expected_char :
        audio .play ("type")
        register_hit_feedback ()

        stats .total_chars_typed +=1 
        stats .article_chars +=1 

        widgets .screen_text .config (state =tk .NORMAL )
        widgets .screen_text .insert (tk .END ,char )
        widgets .screen_text .see (tk .END )
        widgets .screen_text .config (state =tk .DISABLED )

        pos =f"{mark_start } + {game .current_index } chars"
        widgets .text_display .tag_remove ("pending",pos )
        widgets .text_display .tag_add ("correct",pos )
        game .current_index +=1 

        while game .current_index <len (target_content )and target_content [game .current_index ]==' ':
            next_newline =target_content .find ('\n',game .current_index )
            if next_newline !=-1 and target_content [game .current_index :next_newline ].strip ()=='':
                widgets .screen_text .config (state =tk .NORMAL )
                widgets .screen_text .insert (tk .END ,' ')
                widgets .screen_text .see (tk .END )
                widgets .screen_text .config (state =tk .DISABLED )
                p =f"{mark_start } + {game .current_index } chars"
                widgets .text_display .tag_remove ("pending",p )
                widgets .text_display .tag_add ("correct",p )
                game .current_index +=1 
            else :
                break 

        if game .current_index <len (target_content )and char =='\n':
            game .current_index +=START_INDEX 
            widgets .screen_text .config (state =tk .NORMAL )
            widgets .screen_text .insert (tk .END ,PREFIX_SPACES )
            widgets .screen_text .see (tk .END )
            widgets .screen_text .config (state =tk .DISABLED )
            for offset in range (START_INDEX ):
                p =f"{mark_start } + {game .current_index -START_INDEX +offset } chars"
                widgets .text_display .tag_remove ("pending",p )
                widgets .text_display .tag_add ("correct",p )
            scroll_one_line_down ()

        if game .current_index >=len (target_content ):
            if game .current_article_idx <4 :trigger_rest_phase ()
            else :game_win ()
        else :
            widgets .text_display .mark_set ("insert",f"{mark_start } + {game .current_index } chars")
            update_line_highlight ()
            widgets .text_display .see ("insert")
        broadcast_progress_update ()
    else :
        audio .play ("wrong")
        register_miss_feedback ()
        shake_screen (10 ,6 )
        game .mistakes +=1 
        stats .total_mistakes +=1 
        stats .article_mistakes +=1 
        update_hud ()

        err_idx =game .current_index 
        if expected_char =='\n':err_idx =max (0 ,game .current_index -1 )
        widgets .text_display .tag_add ("wrong_bg",f"{mark_start } + {err_idx } chars",f"{mark_start } + {err_idx +1 } chars")

        if game .mistakes >=game .max_mistakes :start_roulette ()
        else :
            line_start_idx =target_content .rfind ('\n',0 ,game .current_index )
            new_index =(0 if line_start_idx ==-1 else line_start_idx +1 )+START_INDEX 
            show_error_and_reset (new_index )

    return "break"

def show_error_and_reset (new_index ):
# Reset typing to the current line start.
    game .is_frozen =True 
    mark_start =f"art_{game .current_article_idx }_start"

    chars_to_delete =game .current_index -new_index 

    def finalize ():
    # Finish the current line reset.
        if not game .game_active :return 
        for i in range (new_index ,game .current_index ):
            p =f"{mark_start } + {i } chars"
            widgets .text_display .tag_remove ("correct",p )
            widgets .text_display .tag_add ("pending",p )
        game .current_index =new_index 
        widgets .text_display .mark_set ("insert",f"{mark_start } + {game .current_index } chars")
        update_line_highlight ()
        widgets .text_display .see ("insert")
        game .is_frozen =False 

    def animate_backspace (remaining ):
    # Animate deleting typed screen text.
        if remaining >0 and game .game_active :
            try :
                widgets .screen_text .config (state =tk .NORMAL )
                widgets .screen_text .delete ("end-2c")
                widgets .screen_text .see (tk .END )
                widgets .screen_text .config (state =tk .DISABLED )
            except :pass 

            delay =max (15 ,300 //chars_to_delete )if chars_to_delete >0 else 30 
            widgets .root .after (delay ,animate_backspace ,remaining -1 )
        else :widgets .root .after (100 ,finalize )

    if chars_to_delete >0 :animate_backspace (chars_to_delete )
    else :widgets .root .after (300 ,finalize )

def trigger_rest_phase ():
# Start the between-passage rest phase.
    record_article_stats ()
    game .is_resting =True 
    game .loading_progress =0 
    widgets .text_display .config (insertbackground ="#111111")
    widgets .text_display .tag_remove ("current_line_bg","1.0",tk .END )
    bar_mark =f"bar_{game .current_article_idx }_start"
    widgets .screen_text .config (state =tk .NORMAL )
    widgets .screen_text .insert (tk .END ,PREFIX_SPACES )
    widgets .screen_text .see (tk .END )
    widgets .screen_text .config (state =tk .DISABLED )
    game .current_bar_width =40 
    widgets .text_display .insert (bar_mark ,PREFIX_SPACES +"|"*game .current_bar_width )
    widgets .text_display .tag_add ("loading_bar_fill",f"{bar_mark } + {START_INDEX } chars",f"{bar_mark } + {START_INDEX +game .current_bar_width } chars")
    scroll_one_line_down ()
    animate_loading_bar ()

def animate_loading_bar ():
# Animate the rest phase loading bar.
    if not game .game_active :return 
    bar_mark =f"bar_{game .current_article_idx }_start"
    if game .loading_progress <game .current_bar_width :
        target_idx =START_INDEX +(game .current_bar_width -1 )-game .loading_progress 
        pos_start =f"{bar_mark } + {target_idx } chars"
        pos_end =f"{bar_mark } + {target_idx +1 } chars"
        widgets .text_display .tag_remove ("loading_bar_fill",pos_start ,pos_end )
        widgets .text_display .tag_add ("loading_bar_bg",pos_start ,pos_end )
        game .loading_progress +=1 
        delay =int (5000 /game .current_bar_width )
        widgets .root .after (delay ,animate_loading_bar )
    else :
        game .current_article_idx +=1 
        game .current_index =START_INDEX 
        game .is_resting =False 
        game .time_left =240 
        update_clock_display ()
        widgets .text_display .config (insertbackground ="#ffffff")
        start_pos =f"art_{game .current_article_idx }_start"
        widgets .text_display .mark_set ("insert",f"{start_pos } + {START_INDEX } chars")
        update_line_highlight ()
        widgets .text_display .see ("insert")
        scroll_one_line_down ()
        widgets .screen_text .config (state =tk .NORMAL )
        widgets .screen_text .insert (tk .END ,"\n"+PREFIX_SPACES )
        widgets .screen_text .see (tk .END )
        widgets .screen_text .config (state =tk .DISABLED )
        broadcast_progress_update ()

def update_line_highlight ():
# Highlight the active typing line.
    widgets .text_display .tag_remove ("current_line_bg","1.0",tk .END )
    widgets .text_display .tag_add ("current_line_bg",f"insert linestart + {START_INDEX } chars","insert lineend")
    widgets .text_display .tag_raise ("wrong_bg","current_line_bg")

    #結算排版
def typewriter_insert (text_str ,index ):
# Print stats with a typewriter effect.
    if index <len (text_str )and not game .game_active :
        chunk =text_str [index :index +1 ]
        try :
            widgets .screen_text .config (state =tk .NORMAL )
            widgets .screen_text .insert (tk .END ,chunk )
            widgets .screen_text .see (tk .END )
            widgets .screen_text .config (state =tk .DISABLED )
            if chunk not in (' ','\n'):
                audio .play ("type_stats")
        except :pass 
        delay =40 if chunk =='\n'else 15 
        widgets .root .after (delay ,typewriter_insert ,text_str ,index +1 )
    elif index >=len (text_str )and not game .game_active :
        try :
            widgets .screen_text .config (state =tk .NORMAL )
            widgets .screen_text .insert (tk .END ,"\n\n--按下任意按鍵來離開--","blink_exit")
            widgets .screen_text .see (tk .END )
            widgets .screen_text .config (state =tk .DISABLED )
            blink_screen_exit_prompt (True )
        except :pass 

def blink_screen_exit_prompt (visible ):
# Blink the stats exit prompt.
    try :
        current_color ="#72d477"if visible else "#050505"
        widgets .screen_text .tag_config ("blink_exit",foreground =current_color ,justify ="center")
        widgets .root .after (600 ,lambda :blink_screen_exit_prompt (not visible ))
    except :pass 

def show_stats_on_screen (status_type ):
# Render match stats on the monitor.
    widgets .screen_text .config (state =tk .NORMAL )
    widgets .screen_text .delete ("1.0",tk .END )

    summary =get_match_summary ()
    avg_wpm =summary ["avg_wpm"]
    max_wpm =summary ["max_wpm"]
    last_wpm =stats .wpm_list [-1 ]if stats .wpm_list else 0 
    avg_acc =summary ["avg_acc"]
    max_acc =max (stats .acc_list )if stats .acc_list else 0.0 
    last_acc =stats .acc_list [-1 ]if stats .acc_list else 0.0 
    rank =summary ["rank"]

    stats_text =f"""
   ---------------------------------------
   |  Metric  | Average |  Max  |  Last  |
   ---------------------------------------
   | Accuracy |{avg_acc :>6.1f}% |{max_acc :>6.1f}% |{last_acc :>6.1f}% |
   ---------------------------------------
   |   WPM    |{avg_wpm :^7} |{max_wpm :^7} |{last_wpm :^7} |
   ---------------------------------------

   Char: {stats .total_chars_typed }
   Mistakes: {stats .total_mistakes }
   Typing time: {stats .total_typing_time }s
   Roulettes: {game .bullets_loaded }
   Best Combo: {game .max_combo }
   Rank: {rank }
"""
    widgets .screen_text .insert (tk .END ,"\n   Result: ")
    if status_type =="Won":widgets .screen_text .insert (tk .END ," Won ","tag_won")
    else :widgets .screen_text .insert (tk .END ," Lost ","tag_dead")
    widgets .screen_text .config (state =tk .DISABLED )
    typewriter_insert (stats_text ,0 )

def get_match_summary():
# Calculate aggregate stats for score display and ranking.
    avg_wpm = sum(stats.wpm_list) // len(stats.wpm_list) if stats.wpm_list else 0
    max_wpm = max(stats.wpm_list) if stats.wpm_list else 0
    avg_acc = sum(stats.acc_list) / len(stats.acc_list) if stats.acc_list else 0.0
    rank = calculate_rank(avg_wpm, avg_acc, game.match_status)
    return {
        "avg_wpm": avg_wpm,
        "max_wpm": max_wpm,
        "avg_acc": round(avg_acc, 1),
        "chars": stats.total_chars_typed,
        "mistakes": stats.total_mistakes,
        "roulettes": game.bullets_loaded,
        "rank": rank,
    }

def calculate_rank(avg_wpm, avg_acc, status_type):
    # Convert overall typing performance into a letter rank.
    if status_type != "Won":
        if avg_acc >= 92 and avg_wpm >= 45:
            return "B"
        return "C"
    if avg_acc >= 98 and avg_wpm >= 75:
        return "S"
    if avg_acc >= 95 and avg_wpm >= 60:
        return "A"
    if avg_acc >= 90 and avg_wpm >= 45:
        return "B"
    return "C"

def save_leaderboard_result(status_type):
    # Save the current finished match into the local leaderboard.
    if game.leaderboard_saved:
        return
    summary = get_match_summary()
    entry = create_entry(
        multiplayer.player_name,
        status_type,
        summary["avg_wpm"],
        summary["max_wpm"],
        summary["avg_acc"],
        summary["chars"],
        summary["mistakes"],
        summary["roulettes"],
    )
    leaderboard.save_entry(entry)
    game.leaderboard_saved = True

    #轉場動畫
def transition_monitor_to_center ():
# Move the monitor into the ending view.
    try :
        scale =3 
        term_monitor_w =int (layout .monitor_w *scale )
        term_monitor_h =int (layout .monitor_h *scale )
        img_monitor =Image .open (image_path ("screen.png")).resize ((term_monitor_w ,term_monitor_h ))
        assets .term_monitor_photo =ImageTk .PhotoImage (img_monitor )
        widgets .main_canvas .itemconfigure ("monitor",image =assets .term_monitor_photo )
        new_monitor_y =layout .screen_h //2 +term_monitor_h //2 +250 
        widgets .main_canvas .coords ("monitor",layout .center_x ,new_monitor_y )
        term_screen_w =int (layout .inner_screen_w *scale )
        term_screen_h =int (layout .inner_screen_h *scale )
        new_screen_text_y =new_monitor_y -int (term_monitor_h *0.58 )

        widgets .main_canvas .itemconfigure (widgets .screen_text_window_id ,state ="normal")
        widgets .main_canvas .itemconfigure (widgets .screen_text_window_id ,width =term_screen_w ,height =term_screen_h )
        widgets .main_canvas .coords (widgets .screen_text_window_id ,layout .center_x ,new_screen_text_y )
        widgets .screen_text .config (font =("Courier New",25 ,"bold"))
        widgets .main_canvas .tag_raise ("monitor")
        widgets .main_canvas .tag_raise (widgets .screen_text_window_id )
    except Exception as e :print ("螢幕放大轉場錯誤:",e )

    #遊戲獲勝
def game_win ():
# Handle a winning match result.
    game .game_active =False 
    game .match_status ="Won"
    if game .timer_job :
        widgets .root .after_cancel (game .timer_job )
        game .timer_job =None 
    widgets .text_display .tag_remove ("current_line_bg","1.0",tk .END )
    record_article_stats ()
    notify_multiplayer_result ("finished")
    audio .stop_music ()
    widgets .main_canvas .create_text (layout .center_x ,int (layout .screen_h *0.08 ),text ="YOU HAVE WON！！",font =("Courier New",28 ,"bold"),fill ="#72d477",justify ="center",tags ="end_msg")
    widgets .root .after (3000 ,lambda :start_transition ("Won"))

    #遊戲失敗
def game_over (by_roulette =False ,by_timeout =False ):
# Handle a losing match result.
    game .game_active =False 
    game .match_status ="Lost"
    if game .timer_job :
        widgets .root .after_cancel (game .timer_job )
        game .timer_job =None 
    widgets .text_display .tag_remove ("current_line_bg","1.0",tk .END )
    record_article_stats ()
    notify_multiplayer_result ("dead")
    audio .stop_music ()
    widgets .main_canvas .create_text (layout .center_x ,int (layout .screen_h *0.08 ),text ="YOU ARE DEAD！！",font =("Courier New",28 ,"bold"),fill ="#ff4444",justify ="center",tags ="end_msg")
    widgets .root .after (3000 ,lambda :start_transition ("Lost"))


def start_transition (status_type ):
# Begin the ending transition.
    try :widgets .main_canvas .delete (widgets .text_window_id )
    except :pass 
    try :fade_to_black_scene (0 ,status_type )
    except :pass 

def fade_to_black_scene (step ,status_type ):
# Fade the scene to black.
    try :
        if step ==30 :widgets .main_canvas .itemconfigure (widgets .screen_text_window_id ,state ="hidden")
        if step <=40 :
            alpha =int (255 *(step /40.0 ))
            overlay =Image .new ("RGBA",(layout .screen_w ,layout .screen_h ),(0 ,0 ,0 ,alpha ))
            assets .fade_photo =ImageTk .PhotoImage (overlay )
            widgets .main_canvas .delete ("fade_overlay")
            widgets .main_canvas .create_image (0 ,0 ,image =assets .fade_photo ,anchor ="nw",tags ="fade_overlay")
            widgets .root .after (50 ,lambda :fade_to_black_scene (step +1 ,status_type ))
        else :
            setup_termination_scene (status_type )
    except :pass 

def setup_termination_scene (status_type ):
# Build the ending stats scene.
    try :
        if status_type =="Lost"and assets .dead_bg_photo :
            widgets .main_canvas .itemconfigure ("bg",image =assets .dead_bg_photo )
        widgets .main_canvas .delete ("table","kb","clock","clock_text","rank","rank_text","revolver","lives")
        widgets .main_canvas .delete ("fade_overlay")
        transition_monitor_to_center ()
        save_leaderboard_result (status_type)
        show_stats_on_screen (status_type )

        game .termination_time =20 
        widgets .main_canvas .itemconfigure ("end_msg",text =f"Terminating in:\n00:{game .termination_time :02d}")
        widgets .main_canvas .itemconfigure ("end_msg",fill ="#72d477"if status_type =="Won"else "#ff4444")
        widgets .main_canvas .tag_raise ("end_msg")
        game .can_exit =True 
        widgets .root .after (1000 ,run_termination_timer )
    except Exception as e :print ("轉場發生錯誤:",e )

def run_termination_timer ():
# Count down before returning to menu.
    try :
        game .termination_time -=1 
        if game .termination_time >0 :
            widgets .main_canvas .itemconfigure ("end_msg",text =f"Terminating in:\n00:{game .termination_time :02d}")
            widgets .root .after (1000 ,run_termination_timer )
        else :
            if game .can_exit :return_to_menu_transition ()
    except :pass 

def return_to_menu_transition ():
# Transition back to the main menu.
    if game .in_transition :return 
    game .can_exit =False 
    game .in_transition =True 
    menu .in_ingame_menu =False 
    widgets .main_canvas .delete ("ingame_menu_bg","ingame_btn","options_ui")
    destroy_options_widgets ()
    fade_to_menu_scene (0 )

def fade_to_menu_scene (step ):
# Fade out before rebuilding the menu.
    try :
        if step ==20 :widgets .main_canvas .itemconfigure (widgets .screen_text_window_id ,state ="hidden")
        if step <=40 :
            alpha =int (255 *(step /40.0 ))
            overlay =Image .new ("RGBA",(layout .screen_w ,layout .screen_h ),(0 ,0 ,0 ,alpha ))
            assets .fade_photo =ImageTk .PhotoImage (overlay )
            widgets .main_canvas .delete ("fade_overlay")
            widgets .main_canvas .create_image (0 ,0 ,image =assets .fade_photo ,anchor ="nw",tags ="fade_overlay")
            widgets .root .after (30 ,lambda :fade_to_menu_scene (step +1 ))
        else :
            widgets .main_canvas .delete ("all")
            game .in_menu =True 
            show_main_menu ()
            fade_in_menu_scene (30 )
    except :pass 

def fade_in_menu_scene (step ):
# Fade the menu back in.
    try :
        if step ==28 :
            try :widgets .main_canvas .itemconfigure (widgets .menu_screen_text_window_id ,state ="normal")
            except :pass 
        if step >=0 :
            alpha =int (255 *(step /30.0 ))
            overlay =Image .new ("RGBA",(layout .screen_w ,layout .screen_h ),(0 ,0 ,0 ,alpha ))
            assets .fade_photo =ImageTk .PhotoImage (overlay )
            widgets .main_canvas .delete ("fade_overlay")
            widgets .main_canvas .create_image (0 ,0 ,image =assets .fade_photo ,anchor ="nw",tags ="fade_overlay")
            widgets .root .after (40 ,lambda :fade_in_menu_scene (step -1 ))
        else :
            widgets .main_canvas .delete ("fade_overlay")
            game .in_transition =False 
    except :pass 

    #Options選單
def destroy_options_widgets ():
# Destroy option menu widgets.
    if menu .music_scale_widget :
        menu .music_scale_widget .destroy ()
        menu .music_scale_widget =None 
    if menu .sfx_scale_widget :
        menu .sfx_scale_widget .destroy ()
        menu .sfx_scale_widget =None 

def set_music_vol (val ):
# Set background music volume.
    settings .music_vol =float (val )/100.0 
    apply_volumes ()

def set_sfx_vol (val ):
# Set sound effect volume.
    settings .sfx_vol =float (val )/100.0 
    apply_volumes ()

def show_options (from_state ):
# Display the options menu.
    menu .in_options_menu =True 
    menu .options_previous_state =from_state 

    if from_state =="main":
        widgets .main_canvas .itemconfigure ("menu_btn",state ="hidden")
        try :widgets .main_canvas .itemconfigure (widgets .menu_screen_text_window_id ,state ="hidden")
        except :pass 
    elif from_state =="ingame":
        widgets .main_canvas .itemconfigure ("ingame_btn",state ="hidden")

    cx =layout .screen_w //2 
    cy =layout .screen_h //2 
    box_w =600 
    box_h =300 

    widgets .main_canvas .create_rectangle (cx -box_w /2 ,cy -box_h /2 ,cx +box_w /2 ,cy +box_h /2 ,
    fill ="#050505",outline ="#FF8C00",width =3 ,tags ="options_ui")

    widgets .main_canvas .create_text (cx -180 ,cy -40 ,text ="Music",font =("Courier New",25 ,"bold"),fill ="#ffffff",anchor ="w",tags ="options_ui")
    widgets .main_canvas .create_text (cx -180 ,cy +40 ,text ="Sound",font =("Courier New",25 ,"bold"),fill ="#ffffff",anchor ="w",tags ="options_ui")

    menu .music_scale_widget =tk .Scale (widgets .main_canvas ,from_ =0 ,to =100 ,orient ="horizontal",
    bg ="#050505",fg ="#FF8C00",font =("Courier New",15 ,"bold"),
    troughcolor ="#222222",activebackground ="#FF8C00",
    highlightthickness =0 ,bd =0 ,length =200 ,show =0 ,command =set_music_vol )
    menu .music_scale_widget .set (int (settings .music_vol *100 ))
    widgets .main_canvas .create_window (cx +80 ,cy -40 ,window =menu .music_scale_widget ,tags ="options_ui")

    menu .sfx_scale_widget =tk .Scale (widgets .main_canvas ,from_ =0 ,to =100 ,orient ="horizontal",
    bg ="#050505",fg ="#FF8C00",font =("Courier New",15 ,"bold"),
    troughcolor ="#222222",activebackground ="#FF8C00",
    highlightthickness =0 ,bd =0 ,length =200 ,show =0 ,command =set_sfx_vol )
    menu .sfx_scale_widget .set (int (settings .sfx_vol *100 ))
    widgets .main_canvas .create_window (cx +80 ,cy +40 ,window =menu .sfx_scale_widget ,tags ="options_ui")

    create_canvas_button (cx ,cy +100 ,200 ,50 ,"Back",close_options ,ui_tag ="options_ui")

def close_options ():
# Close the options menu.
    menu .in_options_menu =False 
    widgets .main_canvas .delete ("options_ui")
    destroy_options_widgets ()

    if menu .options_previous_state =="main":
        widgets .main_canvas .itemconfigure ("menu_btn",state ="normal")
        try :widgets .main_canvas .itemconfigure (widgets .menu_screen_text_window_id ,state ="normal")
        except :pass 
    elif menu .options_previous_state =="ingame":
        widgets .main_canvas .itemconfigure ("ingame_btn",state ="normal")

        #遊戲選單與轉場
def exit_game (event =None ):
# Exit the game application.
    stop_multiplayer_network ()
    widgets .root .destroy ()

def handle_global_click (event ):
# Handle clicks outside focused widgets.
    if game .in_menu or game .in_transition or menu .in_ingame_menu or menu .in_options_menu :return 
    if game .can_exit :return_to_menu_transition ()
    elif game .game_active and widgets .text_display :widgets .text_display .focus_set ()

def handle_global_escape (event ):
# Handle Escape key behavior.
    if game .in_transition :return 
    if menu .in_options_menu :
        close_options ()
        return 
    if game .in_menu :pass 
    elif game .game_active :toggle_ingame_menu ()
    elif game .can_exit :return_to_menu_transition ()

def create_canvas_button (cx ,cy ,width ,height ,text_str ,action ,ui_tag ="menu_btn"):
# Create a Canvas button.
    bg_id =widgets .main_canvas .create_rectangle (
    cx -width /2 ,cy -height /2 ,cx +width /2 ,cy +height /2 ,
    fill ="#000000",outline ="",tags =ui_tag 
    )
    txt_id =widgets .main_canvas .create_text (
    cx ,cy ,text =text_str ,font =("Courier New",35 ,"bold"),
    fill ="#ffffff",tags =ui_tag 
    )
    def on_enter (e ):
    # Apply button hover styling.
        widgets .main_canvas .itemconfigure (bg_id ,fill ="#FF8C00")
        widgets .main_canvas .itemconfigure (txt_id ,fill ="#FFD000")
    def on_leave (e ):
    # Restore button normal styling.
        widgets .main_canvas .itemconfigure (bg_id ,fill ="#000000")
        widgets .main_canvas .itemconfigure (txt_id ,fill ="#ffffff")
    def on_click (e ):
    # Run the button action.
        action ()
    for item_id in (bg_id ,txt_id ):
        widgets .main_canvas .tag_bind (item_id ,"<Enter>",on_enter )
        widgets .main_canvas .tag_bind (item_id ,"<Leave>",on_leave )
        widgets .main_canvas .tag_bind (item_id ,"<Button-1>",on_click )

def show_multiplayer_menu ():
# Display multiplayer menu options.
    widgets .main_canvas .delete ("menu_btn","multiplayer_ui")
    try :widgets .main_canvas .itemconfigure (widgets .menu_screen_text_window_id ,state ="hidden")
    except :pass 
    cx =layout .screen_w *0.25 
    widgets .main_canvas .create_text (cx ,layout .screen_h *0.35 ,text ="MULTIPLAYER",font =("Courier New",42 ,"bold"),fill ="#FF8C00",tags ="multiplayer_ui")
    widgets .main_canvas .create_text (cx ,layout .screen_h *0.48 ,text =MULTIPLAYER_RULES ,font =("Courier New",13 ,"bold"),fill ="#d9d0c0",justify ="left",width =720 ,tags ="multiplayer_ui")
    create_canvas_button (cx ,layout .screen_h *0.68 ,500 ,70 ,"Host Game",start_host_lobby ,ui_tag ="multiplayer_ui")
    create_canvas_button (cx ,layout .screen_h *0.78 ,500 ,70 ,"Join Game",join_host_lobby ,ui_tag ="multiplayer_ui")
    create_canvas_button (cx ,layout .screen_h *0.88 ,500 ,70 ,"Back",show_main_menu ,ui_tag ="multiplayer_ui")

def update_lobby_status ():
# Refresh host lobby player text.
    if multiplayer .multiplayer_status_text_id :
        players =[multiplayer .player_name ]+[client ["name"]for client in multiplayer .connected_clients ]
        status =f"Hosting on {get_local_ip ()}:{MULTIPLAYER_PORT }\nPlayers: {len (players )}\n\n"+"\n".join (f">>> {name }"for name in players )
        widgets .main_canvas .itemconfigure (multiplayer .multiplayer_status_text_id ,text =status )

def show_multiplayer_lobby (status ):
# Show the host lobby screen.
    widgets .main_canvas .delete ("menu_btn","multiplayer_ui","lobby_ui")
    try :widgets .main_canvas .itemconfigure (widgets .menu_screen_text_window_id ,state ="hidden")
    except :pass 
    cx =layout .screen_w *0.25 
    widgets .main_canvas .create_text (cx ,layout .screen_h *0.30 ,text ="PRIVATE LOBBY",font =("Courier New",42 ,"bold"),fill ="#FF8C00",tags ="lobby_ui")
    multiplayer .multiplayer_status_text_id =widgets .main_canvas .create_text (cx ,layout .screen_h *0.46 ,text =status ,font =("Courier New",18 ,"bold"),fill ="#72d477",justify ="center",width =760 ,tags ="lobby_ui")
    create_canvas_button (cx ,layout .screen_h *0.66 ,500 ,70 ,"Start Match",host_start_multiplayer_match ,ui_tag ="lobby_ui")
    create_canvas_button (cx ,layout .screen_h *0.78 ,500 ,70 ,"Back",lambda :[stop_multiplayer_network (),show_multiplayer_menu ()],ui_tag ="lobby_ui")
    update_lobby_status ()

def show_waiting_lobby (status ):
# Show the client waiting screen.
    widgets .main_canvas .delete ("menu_btn","multiplayer_ui","lobby_ui")
    try :widgets .main_canvas .itemconfigure (widgets .menu_screen_text_window_id ,state ="hidden")
    except :pass 
    cx =layout .screen_w *0.25 
    widgets .main_canvas .create_text (cx ,layout .screen_h *0.32 ,text ="WAITING ROOM",font =("Courier New",42 ,"bold"),fill ="#FF8C00",tags ="lobby_ui")
    multiplayer .multiplayer_status_text_id =widgets .main_canvas .create_text (cx ,layout .screen_h *0.52 ,text =status ,font =("Courier New",17 ,"bold"),fill ="#72d477",justify ="center",width =760 ,tags ="lobby_ui")
    create_canvas_button (cx ,layout .screen_h *0.78 ,500 ,70 ,"Back",lambda :[stop_multiplayer_network (),show_multiplayer_menu ()],ui_tag ="lobby_ui")

def show_leaderboard_menu():
    # Display the saved local leaderboard.
    widgets.main_canvas.delete("menu_btn", "leaderboard_ui")
    try:
        widgets.main_canvas.itemconfigure(widgets.menu_screen_text_window_id, state="hidden")
    except:
        pass
    cx = layout.screen_w * 0.25
    widgets.main_canvas.create_text(cx, layout.screen_h * 0.35, text="LEADERBOARD", font=("Courier New", 42, "bold"), fill="#FF8C00", tags="leaderboard_ui")
    rows = leaderboard.top_entries(8)
    if rows:
        lines = [" Rank Player        Result WPM  ACC   Date", " ---------------------------------------------"]
        for i, row in enumerate(rows, 1):
            player = str(row.get("player", "Player"))[:12]
            lines.append(
                f" {i:>2}.  {player:<12} {row.get('result', 'Lost'):<5} "
                f"{row.get('avg_wpm', 0):>3}  {row.get('avg_acc', 0):>5.1f}%  {row.get('created_at', '')}"
            )
        board_text = "\n".join(lines)
    else:
        board_text = "No results yet.\nFinish a match to create your first record."
    widgets.main_canvas.create_text(cx, layout.screen_h * 0.50, text=board_text, font=("Courier New", 16, "bold"), fill="#72d477", justify="left", width=780, tags="leaderboard_ui")
    create_canvas_button(cx, layout.screen_h * 0.78, 500, 70, "Back", show_main_menu, ui_tag="leaderboard_ui")

def toggle_ingame_menu ():
# Open or close the in-game menu.
    if not game .game_active or game .is_pre_game or game .is_frozen or game .is_resting or game .in_menu or game .in_transition :return 

    if menu .in_ingame_menu :
        menu .in_ingame_menu =False 
        widgets .main_canvas .delete ("ingame_menu_bg","ingame_btn")
        widgets .main_canvas .itemconfigure (widgets .text_window_id ,state ="normal")
        widgets .main_canvas .itemconfigure (widgets .screen_text_window_id ,state ="normal")
        widgets .text_display .focus_set ()
    else :
        menu .in_ingame_menu =True 
        widgets .main_canvas .itemconfigure (widgets .text_window_id ,state ="hidden")
        widgets .main_canvas .itemconfigure (widgets .screen_text_window_id ,state ="hidden")

        overlay =Image .new ("RGBA",(layout .screen_w ,layout .screen_h ),(0 ,0 ,0 ,200 ))
        menu .ingame_overlay_photo =ImageTk .PhotoImage (overlay )
        widgets .main_canvas .create_image (0 ,0 ,image =menu .ingame_overlay_photo ,anchor ="nw",tags ="ingame_menu_bg")

        btn_width =400 
        btn_height =80 
        create_canvas_button (layout .screen_w //2 ,layout .screen_h //2 -100 ,btn_width ,btn_height ,"Continue",toggle_ingame_menu ,ui_tag ="ingame_btn")
        create_canvas_button (layout .screen_w //2 ,layout .screen_h //2 ,btn_width ,btn_height ,"Options",lambda :show_options ("ingame"),ui_tag ="ingame_btn")
        create_canvas_button (layout .screen_w //2 ,layout .screen_h //2 +100 ,btn_width ,btn_height ,"Exit",exit_to_main_menu_from_ingame ,ui_tag ="ingame_btn")

def exit_to_main_menu_from_ingame ():
# Leave a match from the pause menu.
    audio .stop_music ()
    menu .in_ingame_menu =False 
    game .game_active =False 
    widgets .main_canvas .delete ("ingame_menu_bg","ingame_btn","options_ui")
    destroy_options_widgets ()
    game .in_transition =True 
    fade_to_menu_scene (0 )

def play_btn_clicked (is_multiplayer_start =False ):
# Start a single or multiplayer match.
    if game .in_transition :return 
    if not is_multiplayer_start :
        multiplayer .multiplayer_mode =False 
        multiplayer .pending_article_indices =None 
        stop_multiplayer_network ()
    game .in_transition =True 
    audio .fadeout_music (1300 )
    fade_out_menu (0 )

def fade_out_menu (step ):
# Fade out the main menu.
    try :
        if step ==25 :
            if widgets .menu_screen_text_window_id :widgets .main_canvas .delete (widgets .menu_screen_text_window_id )
            if widgets .menu_screen_text :widgets .menu_screen_text .destroy ()
        if step <=40 :
            alpha =int (255 *(step /40.0 ))
            overlay =Image .new ("RGBA",(layout .screen_w ,layout .screen_h ),(0 ,0 ,0 ,alpha ))
            assets .fade_photo =ImageTk .PhotoImage (overlay )
            widgets .main_canvas .delete ("fade_overlay")
            widgets .main_canvas .create_image (0 ,0 ,image =assets .fade_photo ,anchor ="nw",tags ="fade_overlay")
            widgets .root .after (20 ,lambda :fade_out_menu (step +1 ))
        else :
            destroy_options_widgets ()
            start_game_from_menu ()
            fade_in_game (30 )
    except :pass 

def fade_in_game (step ):
# Fade in the game scene.
    try :
        if step ==8 :
            widgets .main_canvas .itemconfigure (widgets .text_window_id ,state ="normal")
            widgets .text_display .focus_set ()
        if step >=0 :
            alpha =int (255 *(step /30.0 ))
            overlay =Image .new ("RGBA",(layout .screen_w ,layout .screen_h ),(0 ,0 ,0 ,alpha ))
            assets .fade_photo =ImageTk .PhotoImage (overlay )
            widgets .main_canvas .delete ("fade_overlay")
            widgets .main_canvas .create_image (0 ,0 ,image =assets .fade_photo ,anchor ="nw",tags ="fade_overlay")
            widgets .root .after (30 ,lambda :fade_in_game (step -1 ))
        else :
            widgets .main_canvas .delete ("fade_overlay")
            game .in_transition =False 
            if game .game_active :widgets .text_display .focus_force ()
    except :pass 

def start_game_from_menu ():
# Build widgets for a match.
    game .in_menu =False 
    widgets .main_canvas .delete ("menu_ui","menu_btn","options_ui")
    destroy_options_widgets ()
    widgets .main_canvas .delete ("all")

    overlay =Image .new ("RGBA",(layout .screen_w ,layout .screen_h ),(0 ,0 ,0 ,255 ))
    assets .fade_photo =ImageTk .PhotoImage (overlay )

    widgets .main_canvas .config (bg ="#111111")
    if assets .bg_photo :widgets .main_canvas .create_image (0 ,0 ,image =assets .bg_photo ,anchor ="nw",tags ="bg")
    if assets .table_photo :widgets .main_canvas .create_image (0 ,layout .screen_h -int (layout .screen_h *0.25 ),image =assets .table_photo ,anchor ="nw",tags ="table")
    if assets .monitor_photo :widgets .main_canvas .create_image (layout .screen_w //2 ,layout .screen_h -150 ,image =assets .monitor_photo ,anchor ="s",tags ="monitor")
    if assets .kb_photo :widgets .main_canvas .create_image (layout .screen_w //2 ,layout .screen_h -10 ,image =assets .kb_photo ,anchor ="s",tags ="kb")

    if assets .clock_photo :
        cw ,ch =Image .open (image_path ("clock.png")).size 
        clock_x =-int (layout .screen_w *0.05 )+90 
        clock_y =(layout .screen_h -int (layout .screen_h *0.25 ))-int (int (layout .screen_w *0.2 )*(ch /cw )*0.5 )
        widgets .main_canvas .create_image (clock_x ,clock_y ,image =assets .clock_photo ,anchor ="nw",tags ="clock")
        layout .clock_text_x =clock_x +int (layout .screen_w *0.2 )*0.52 
        layout .clock_text_y =clock_y +int (int (layout .screen_w *0.2 )*(ch /cw ))*0.52 
        layout .clock_font_size =int (int (int (layout .screen_w *0.2 )*(ch /cw ))*0.3 )

    if assets .rank_photo :
        rw ,rh =Image .open (image_path ("rank.png")).size 
        rank_w =int (layout .screen_w *0.15 )
        rank_h =int (rank_w *(rh /rw ))
        rank_x =layout .screen_w -rank_w +int (rank_w *0.09 )
        rank_y =(layout .screen_h -int (layout .screen_h *0.25 ))-int (rank_h *0.6 )
        widgets .main_canvas .create_image (rank_x ,rank_y ,anchor ="nw",image =assets .rank_photo ,tags ="rank")
        rank_text_x =rank_x +rank_w *0.52 
        rank_text_y =rank_y +rank_h *0.52 
        layout .rank_font_size =int (rank_h *0.55 )
        if assets .rank_text_photo :widgets .main_canvas .create_image (rank_text_x ,rank_text_y ,image =assets .rank_text_photo ,anchor ="center",tags ="rank_text")

    widgets .text_display =tk .Text (widgets .main_canvas ,font =("Courier New",20 ,"bold"),bg ="#161311",bd =0 ,
    highlightthickness =0 ,width =TEXT_WIDTH ,height =6 ,
    spacing1 =2 ,spacing2 =0 ,spacing3 =2 ,
    padx =25 ,pady =10 ,insertbackground ="#ffffff",insertwidth =4 )
    widgets .root .update_idletasks ()
    tw =widgets .text_display .winfo_reqwidth ()
    layout .left_edge =layout .center_x -(tw //2 )
    my_font =tkFont .Font (family ="Courier New",size =20 ,weight ="bold")
    char_width =my_font .measure ("A")
    real_text_left_x =layout .left_edge +25 +(START_INDEX *char_width )
    layout .first_box_cx =real_text_left_x +16 
    layout .revolver_cx =real_text_left_x -38 

    widgets .text_window_id =widgets .main_canvas .create_window (layout .center_x ,layout .base_y ,window =widgets .text_display ,anchor ="n",state ="hidden")

    widgets .text_display .tag_config ("correct",foreground ="#72d477")
    widgets .text_display .tag_config ("pending",foreground ="#A07431")
    widgets .text_display .tag_config ("error",foreground ="#ff4444")
    widgets .text_display .tag_config ("wrong_bg",background ="#770000")
    widgets .text_display .tag_config ("current_line_bg",background ="#423d3a")
    widgets .text_display .tag_config ("loading_bar_bg",foreground ="#222222")
    widgets .text_display .tag_config ("loading_bar_fill",foreground ="#d28c00")

    current_tags =widgets .text_display .bindtags ()
    new_tags =tuple (tag for tag in current_tags if tag !="Text")
    widgets .text_display .bindtags (new_tags )

    widgets .screen_text =tk .Text (widgets .main_canvas ,font =("Courier New",8 ,"bold"),bg ="#050505",fg ="#72d477",bd =0 ,
    highlightthickness =0 ,padx =10 ,pady =10 ,state =tk .DISABLED )
    widgets .screen_text .bindtags (new_tags )
    widgets .screen_text .tag_config ("tag_won",background ="#72d477",foreground ="#000000")
    widgets .screen_text .tag_config ("tag_dead",background ="#ff4444",foreground ="#000000")

    widgets .screen_text_window_id =widgets .main_canvas .create_window (
    layout .center_x ,layout .screen_h -150 -int (layout .monitor_h *0.58 ),
    window =widgets .screen_text ,anchor ="center",width =layout .inner_screen_w ,height =layout .inner_screen_h 
    )

    widgets .main_canvas .create_text (layout .center_x ,layout .screen_h *0.95 ,text ="--點擊畫面任意位置離開--",
    font =("Courier New",16 ,"bold"),fill ="#ffffff",tags ="exit_prompt",state ="hidden")
    widgets .main_canvas .create_image (0 ,0 ,image =assets .fade_photo ,anchor ="nw",tags ="fade_overlay")
    widgets .text_display .bind ("<Key>",handle_keypress )
    widgets .root .bind ("<FocusIn>",lambda e :widgets .text_display .focus_set ()if game .game_active else None )

    update_hud ()
    initialize_game (multiplayer .pending_article_indices )

def show_main_menu ():
# Build the main menu screen.
    widgets .main_canvas .delete ("all")
    widgets .main_canvas .config (bg ="#000000")
    audio .play_music_loop ()
    if assets .table_photo :widgets .main_canvas .create_image (0 ,layout .screen_h -int (layout .screen_h *0.25 ),image =assets .table_photo ,anchor ="nw",tags ="menu_ui")

    menu_scale =2 
    menu_m_w =int (layout .monitor_w *menu_scale )
    menu_m_h =int (layout .monitor_h *menu_scale )

    try :
        img_monitor_menu =Image .open (image_path ("screen.png")).resize ((menu_m_w ,menu_m_h ))
        assets .menu_monitor_photo =ImageTk .PhotoImage (img_monitor_menu )
        menu_monitor_x =layout .screen_w *0.72 
        widgets .main_canvas .create_image (menu_monitor_x ,layout .screen_h +10 ,image =assets .menu_monitor_photo ,anchor ="s",tags ="menu_ui")

        widgets .menu_screen_text =tk .Text (widgets .main_canvas ,font =("Courier New",28 ,"bold"),bg ="#050505",fg ="#72d477",bd =0 ,
        highlightthickness =0 ,padx =10 ,pady =10 ,state =tk .NORMAL )
        menu_tags =widgets .menu_screen_text .bindtags ()
        widgets .menu_screen_text .bindtags (tuple (t for t in menu_tags if t !="Text"))
        widgets .menu_screen_text .insert (tk .END ,">>> TYPE AS FAST AS YOU CAN!\n\n\n>>> Or\n\n\n>>> You will DIE!!!\n\n\n>>> Good Luck!!!")
        widgets .menu_screen_text .config (state =tk .DISABLED )

        m_inner_w =int (layout .inner_screen_w *menu_scale )
        m_inner_h =int (layout .inner_screen_h *menu_scale )
        menu_screen_text_y =(layout .screen_h +10 )-int (menu_m_h *0.58 )

        widgets .menu_screen_text_window_id =widgets .main_canvas .create_window (
        menu_monitor_x ,menu_screen_text_y ,
        window =widgets .menu_screen_text ,anchor ="center",width =m_inner_w ,height =m_inner_h ,state ="hidden"
        )
    except Exception as e :print ("Menu Monitor loading error:",e )

    title_font =tkFont .Font (family ="Courier New",size =70 ,weight ="bold")
    char_w =title_font .measure ("A")
    char_h =title_font .metrics ("linespace")

    start_x =(layout .screen_w *0.25 )-(14 *char_w )/2 
    title_y =layout .screen_h *0.25 

    widgets .main_canvas .create_rectangle (start_x ,title_y -char_h /2 ,start_x +char_w ,title_y +char_h /2 ,fill ="#FF3737",outline ="",tags ="menu_ui")
    widgets .main_canvas .create_text (start_x ,title_y ,text ="F",font =("Courier New",70 ,"bold"),fill ="#FF8C00",anchor ="w",tags ="menu_ui")
    start_x +=char_w 
    widgets .main_canvas .create_text (start_x ,title_y ,text ="inal ",font =("Courier New",70 ,"bold"),fill ="#FF8C00",anchor ="w",tags ="menu_ui")
    start_x +=char_w *5 
    widgets .main_canvas .create_rectangle (start_x ,title_y -char_h /2 ,start_x +char_w ,title_y +char_h /2 ,fill ="#FF3737",outline ="",tags ="menu_ui")
    widgets .main_canvas .create_text (start_x ,title_y ,text ="S",font =("Courier New",70 ,"bold"),fill ="#FF8C00",anchor ="w",tags ="menu_ui")
    start_x +=char_w 
    widgets .main_canvas .create_text (start_x ,title_y ,text ="entence",font =("Courier New",70 ,"bold"),fill ="#FF8C00",anchor ="w",tags ="menu_ui")

    btn_width =500 
    btn_height =80 
    create_canvas_button (layout .screen_w *0.25 ,layout .screen_h *0.40 ,btn_width ,btn_height ,"Single Player",play_btn_clicked ,ui_tag ="menu_btn")
    create_canvas_button (layout .screen_w *0.25 ,layout .screen_h *0.51 ,btn_width ,btn_height ,"Multiplayer",show_multiplayer_menu ,ui_tag ="menu_btn")
    create_canvas_button (layout .screen_w *0.25 ,layout .screen_h *0.62 ,btn_width ,btn_height ,"Leaderboard",show_leaderboard_menu ,ui_tag ="menu_btn")
    create_canvas_button (layout .screen_w *0.25 ,layout .screen_h *0.73 ,btn_width ,btn_height ,"Options",lambda :show_options ("main"),ui_tag ="menu_btn")
    create_canvas_button (layout .screen_w *0.25 ,layout .screen_h *0.84 ,btn_width ,btn_height ,"Exit",exit_game ,ui_tag ="menu_btn")

def main ():
# Create the window and run the app.

    widgets .root =tk .Tk ()
    widgets .root .title ("Final Sentence")
    widgets .root .attributes ("-fullscreen",True )

    widgets .root .update_idletasks ()
    layout .screen_w =widgets .root .winfo_screenwidth ()
    layout .screen_h =widgets .root .winfo_screenheight ()
    layout .center_x =layout .screen_w //2 
    layout .base_y =int (layout .screen_h *0.20 )

    layout .monitor_w =int (layout .screen_w *0.5 )
    layout .monitor_h =int (layout .screen_h *0.45 )
    layout .inner_screen_w =int (layout .monitor_w *0.35 )
    layout .inner_screen_h =int (layout .monitor_h *0.51 )

    widgets .main_canvas =tk .Canvas (widgets .root ,width =layout .screen_w ,height =layout .screen_h ,highlightthickness =0 ,bg ="#111111",bd =0 )
    widgets .main_canvas .pack (fill =tk .BOTH ,expand =True )

    try :
        img_bg =Image .open (image_path ("room.png")).resize ((layout .screen_w ,layout .screen_h ))
        assets .bg_photo =ImageTk .PhotoImage (img_bg )
        table_h =int (layout .screen_h *0.25 )
        img_table =Image .open (image_path ("table.png")).resize ((layout .screen_w ,table_h ))
        assets .table_photo =ImageTk .PhotoImage (img_table )
        img_monitor =Image .open (image_path ("screen.png")).resize ((layout .monitor_w ,layout .monitor_h ))
        assets .monitor_photo =ImageTk .PhotoImage (img_monitor )
        try :
            orig_kb =Image .open (image_path ("kb.png"))
            orig_kw ,orig_kh =orig_kb .size 
            kb_w =int (layout .screen_w *0.35 )
            kb_h =int (kb_w *(orig_kh /orig_kw ))
            img_kb =orig_kb .resize ((kb_w ,kb_h ))
            assets .kb_photo =ImageTk .PhotoImage (img_kb )
        except Exception as e :print (f"鍵盤圖片載入失敗 (kb.png): {e }")

        orig_clock =Image .open (image_path ("clock.png"))
        orig_cw ,orig_ch =orig_clock .size 
        clock_w =int (layout .screen_w *0.2 )
        clock_h =int (clock_w *(orig_ch /orig_cw ))
        img_clock =orig_clock .resize ((clock_w ,clock_h ))
        assets .clock_photo =ImageTk .PhotoImage (img_clock )

        orig_rank =Image .open (image_path ("rank.png"))
        orig_rw ,orig_rh =orig_rank .size 
        rank_w =int (layout .screen_w *0.15 )
        rank_h =int (rank_w *(orig_rh /orig_rw ))
        img_rank =orig_rank .resize ((rank_w ,rank_h ))
        assets .rank_photo =ImageTk .PhotoImage (img_rank )
        layout .rank_font_size =int (rank_h *0.55 )
        assets .rank_text_photo =create_rotated_text_image (str (game .player_id ),layout .rank_font_size ,"#1a1a1a",-10 ,font_file ="timesbd.ttf")

        try :
            orig_blood =Image .open (image_path ("dead.png")).convert ("RGB")
            assets .img_blood =orig_blood .resize ((layout .screen_w ,layout .screen_h ))
            assets .dead_bg_photo =ImageTk .PhotoImage (assets .img_blood )
        except Exception as e :
            print (f"圖片載入失敗 (dead.png): {e }")
            assets .img_blood =Image .new ("RGB",(layout .screen_w ,layout .screen_h ),(80 ,0 ,0 ))
            assets .dead_bg_photo =ImageTk .PhotoImage (assets .img_blood )

        assets .black_screen =Image .new ("RGB",(layout .screen_w ,layout .screen_h ),(0 ,0 ,0 ))

    except Exception as e :
        print (f"圖片載入失敗，請確認檔名與路徑是否正確: {e }")

    widgets .root .bind ("<Button-1>",handle_global_click )
    widgets .root .bind ("<Escape>",handle_global_escape )

    show_main_menu ()
    poll_network_events ()

    if widgets .menu_screen_text_window_id :
        try :widgets .main_canvas .itemconfigure (widgets .menu_screen_text_window_id ,state ="normal")
        except :pass 

    widgets .root .mainloop ()
