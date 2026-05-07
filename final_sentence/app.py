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
from .missions import MissionStore
from .network import get_local_ip ,read_json_lines ,send_json 
from .paths import image_path 
from .texts import MULTIPLAYER_RULES ,PREDEFINED_TEXTS ,format_article_text 
from .view import GameView

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
missions = MissionStore()
view =None 

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
game .roulette_survivals =0 

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
# Record WPM, accuracy, and completion for one passage.
    time_spent =240 -game .time_left 
    if time_spent <=0 :time_spent =1 
    stats .total_typing_time +=time_spent 
    wpm =(stats .article_chars /5.0 )/(time_spent /60.0 )if stats .article_chars >0 else 0 
    total_attempts =stats .article_chars +stats .article_mistakes 
    acc =(stats .article_chars /total_attempts *100.0 )if total_attempts >0 else 0.0 
    completion =compute_current_article_completion ()
    if total_attempts >0 :
        stats .wpm_list .append (int (wpm ))
        stats .acc_list .append (round (acc ,1 ))
        stats .completion_list .append (round (completion ,1 ))
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
    game .roulette_survivals =0 
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
    stats .completion_list =[]
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
    view .draw_revolver (rotation_index )

def draw_lives ():
# Draw the current mistake boxes.
    view .draw_lives ()

def update_hud ():
# Refresh the roulette and lives HUD.
    draw_revolver (0 )
    draw_lives ()
    draw_feedback_hud ()

def draw_feedback_hud ():
# Draw combo, judgement, and multiplayer progress text.
    view .draw_feedback_hud ()

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
    view .update_clock_display ()
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
        game .roulette_survivals +=1 
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
    summary =get_match_summary ()
    last_wpm =stats .wpm_list [-1 ]if stats .wpm_list else 0 
    best_completion =max (stats .completion_list )if stats .completion_list else summary ["completion_rate"]
    article_completion =stats .completion_list [-1 ]if stats .completion_list else summary ["completion_rate"]
    view .show_stats_on_screen (status_type ,summary ,last_wpm ,best_completion ,article_completion )

def compute_current_article_completion ():
# Convert the active article progress into a per-article percentage.
    if not game .articles or game .current_article_idx >=len (game .articles ):
        return 0.0 
    current_article =game .articles [game .current_article_idx ]
    if not current_article :
        return 0.0 
    return min (100.0 ,(game .current_index /len (current_article ))*100.0 )

def get_match_summary():
# Calculate aggregate stats for score display and ranking.
    avg_wpm = sum(stats.wpm_list) // len(stats.wpm_list) if stats.wpm_list else 0
    max_wpm = max(stats.wpm_list) if stats.wpm_list else 0
    completion_rate = 100.0 if game.match_status == "Won" else compute_progress_percent()
    rank = calculate_rank(completion_rate, avg_wpm, stats.total_mistakes, game.match_status)
    return {
        "completion_rate": round(completion_rate, 1),
        "avg_wpm": avg_wpm,
        "max_wpm": max_wpm,
        "chars": stats.total_chars_typed,
        "mistakes": stats.total_mistakes,
        "roulettes": game.bullets_loaded,
        "best_combo": game.max_combo,
        "result": game.match_status,
        "roulette_survivals": game.roulette_survivals,
        "rank": rank,
    }

def calculate_rank(completion_rate, avg_wpm, total_mistakes, status_type):
    # Convert match outcome into a completion-led letter rank.
    if status_type == "Won" and completion_rate >= 100 and avg_wpm >= 75 and total_mistakes <= 8:
        return "S"
    if status_type == "Won" and completion_rate >= 100 and avg_wpm >= 60:
        return "A"
    if completion_rate >= 80:
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
        summary["completion_rate"],
        summary["avg_wpm"],
        summary["max_wpm"],
        summary["chars"],
        summary["mistakes"],
        summary["roulettes"],
    )
    leaderboard.save_entry(entry)
    game.leaderboard_saved = True

def update_mission_progress():
    # Apply the latest match summary to the persistent mission system.
    missions.update_from_run(get_match_summary())

    #轉場動畫
def transition_monitor_to_center ():
# Move the monitor into the ending view.
    try :
        view .transition_monitor_to_center ()
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
        update_mission_progress ()
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
    view .show_options (from_state )

def close_options ():
# Close the options menu.
    view .close_options ()

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
    view .create_canvas_button (cx ,cy ,width ,height ,text_str ,action ,ui_tag )

def show_multiplayer_menu ():
# Display multiplayer menu options.
    view .show_multiplayer_menu ()

def update_lobby_status ():
# Refresh host lobby player text.
    view .update_lobby_status ()

def show_multiplayer_lobby (status ):
# Show the host lobby screen.
    view .show_multiplayer_lobby (status )
    update_lobby_status ()

def show_waiting_lobby (status ):
# Show the client waiting screen.
    view .show_waiting_lobby (status )

def show_leaderboard_menu():
    # Display the saved local leaderboard.
    view .show_leaderboard_menu (leaderboard .top_entries (8 ))

def show_missions_menu():
    # Display the persistent mission progress screen.
    view .show_missions_menu (missions .mission_rows ())

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
    destroy_options_widgets ()
    view .build_game_scene ()
    update_hud ()
    initialize_game (multiplayer .pending_article_indices )

def show_main_menu ():
# Build the main menu screen.
    view .show_main_menu ()

def main ():
# Create the window and run the app.
    global view 
    view =GameView (
    game ,
    menu ,
    multiplayer ,
    stats ,
    layout ,
    assets ,
    widgets ,
    settings ,
    leaderboard ,
    audio ,
    {
    "global_click":handle_global_click ,
    "global_escape":handle_global_escape ,
    "keypress":handle_keypress ,
    "single_player":play_btn_clicked ,
    "show_multiplayer_menu":show_multiplayer_menu ,
    "show_main_menu":show_main_menu ,
    "show_options":show_options ,
    "close_options":close_options ,
    "exit_game":exit_game ,
    "host_lobby":start_host_lobby ,
    "join_lobby":join_host_lobby ,
    "start_multiplayer":host_start_multiplayer_match ,
    "leave_lobby":lambda :[stop_multiplayer_network (),show_multiplayer_menu ()],
    "set_music":set_music_vol ,
    "set_sfx":set_sfx_vol ,
    "show_leaderboard":show_leaderboard_menu ,
    "show_missions":show_missions_menu ,
    "typewriter":typewriter_insert ,
    "local_ip":get_local_ip ,
    "port":lambda :MULTIPLAYER_PORT ,
    },
    TEXT_WIDTH ,
    START_INDEX ,
    PREFIX_SPACES ,
    MULTIPLAYER_RULES ,
    )
    view .build_root ()
    try :
        view .load_assets ()
    except Exception as e :
        print (f"圖片載入失敗，請確認檔名與路徑是否正確: {e }")
    view .bind_root_events ()
    show_main_menu ()
    poll_network_events ()
    if widgets .menu_screen_text_window_id :
        try :widgets .main_canvas .itemconfigure (widgets .menu_screen_text_window_id ,state ="normal")
        except :pass 
    widgets .root .mainloop ()
