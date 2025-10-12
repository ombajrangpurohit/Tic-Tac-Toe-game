import pygame
import sys
import random
import math
import numpy as np

# --- Initialization ---
# Explicitly pre-initialize the mixer for better compatibility (freq, size, channels, buffer)
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()

# --- Constants ---
SCREEN_WIDTH = 400
SCREEN_HEIGHT = 500
BOARD_ROWS = 3
BOARD_COLS = 3

# Grid layout constants for easier modification
GRID_X_START = 20
GRID_Y_START = 120
GRID_WIDTH = SCREEN_WIDTH - (2 * GRID_X_START)
CELL_SIZE = GRID_WIDTH // BOARD_COLS
ANIMATION_SPEED = 0.05

# Colors
BG_COLOR = (44, 62, 80)
LINE_COLOR = (52, 73, 94)
X_COLOR = (231, 76, 60)
O_COLOR = (52, 152, 219)
WIN_LINE_COLOR = (241, 196, 15)
TEXT_COLOR = (236, 240, 241)
BUTTON_COLOR = (26, 188, 156)
BUTTON_HOVER_COLOR = (22, 160, 133)
BUTTON_SHADOW_COLOR = (22, 160, 133)
UI_FRAME_COLOR = (52, 73, 94)

# Line widths
LINE_WIDTH = 8
X_WIDTH = 15
O_WIDTH = 15
WIN_LINE_WIDTH = 8

# --- Screen Setup ---
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Enhanced Tic-Tac-Toe")

# --- Fonts (Using default Pygame font for compatibility) ---
title_font = pygame.font.Font(None, 60)
status_font = pygame.font.Font(None, 34)
menu_font = pygame.font.Font(None, 38)
score_font = pygame.font.Font(None, 26)


# --- Sounds (Generated) ---
def generate_sound(frequency=440, duration=0.05):
    try:
        sample_rate = pygame.mixer.get_init()[0]
        max_amp = 2 ** (pygame.mixer.get_init()[2] - 1) - 1
        length = int(duration * sample_rate)
        wave = [max_amp * math.sin(2.0 * math.pi * frequency * x / sample_rate) for x in range(length)]
        
        # Create a stereo sound by duplicating the mono wave.
        stereo_wave = np.array([wave, wave]).T
        sound_array = stereo_wave.astype(np.int16)
        
        sound = pygame.mixer.Sound(array=sound_array)
        sound.set_volume(0.1)
        return sound
    except (pygame.error, TypeError, ValueError):
        # Return a dummy sound object if sound generation fails
        class DummySound:
            def play(self): pass
        return DummySound()

place_sound = generate_sound(440, 0.1)
win_sound = generate_sound(880, 0.5)
draw_sound = generate_sound(220, 0.5)

# --- Game Variables ---
board = [[" " for _ in range(BOARD_COLS)] for _ in range(BOARD_ROWS)]
scores = {"X": 0, "O": 0, "Draw": 0}
minimax_memo = {} # Cache for minimax optimization
current_player = "X"
game_over = False
winner = None
win_info = None
game_mode = "menu"  # menu, difficulty, choose_piece, pvp, pvc
human_player = "X"
computer_player = "O"
difficulty = "Medium"
animating_piece = None
animating_win_line = None

# --- UI Element Rects ---
buttons = {
    "pvp": pygame.Rect(100, 150, 200, 50),
    "pvc": pygame.Rect(100, 220, 200, 50),
    "easy": pygame.Rect(100, 150, 200, 50),
    "medium": pygame.Rect(100, 220, 200, 50),
    "hard": pygame.Rect(100, 290, 200, 50),
    "play_x": pygame.Rect(100, 180, 80, 80),
    "play_o": pygame.Rect(220, 180, 80, 80)
}

# --- Functions ---

def draw_button(rect, text, text_font=menu_font):
    mouse_pos = pygame.mouse.get_pos()
    color = BUTTON_HOVER_COLOR if rect.collidepoint(mouse_pos) else BUTTON_COLOR
    
    shadow_rect = rect.copy()
    shadow_rect.move_ip(5, 5)
    pygame.draw.rect(screen, BUTTON_SHADOW_COLOR, shadow_rect, border_radius=15)

    pygame.draw.rect(screen, color, rect, border_radius=15)
    btn_text = text_font.render(text, True, TEXT_COLOR)
    screen.blit(btn_text, (rect.centerx - btn_text.get_width()/2, rect.centery - btn_text.get_height()/2))

def draw_background():
    screen.fill(BG_COLOR)
    pygame.draw.rect(screen, UI_FRAME_COLOR, (0, 0, SCREEN_WIDTH, 100))
    # Board background
    pygame.draw.rect(screen, BG_COLOR, (GRID_X_START, GRID_Y_START, GRID_WIDTH, GRID_WIDTH), 0, 15)

    # Grid lines
    for i in range(1, BOARD_ROWS):
        pygame.draw.line(screen, LINE_COLOR, (GRID_X_START, GRID_Y_START + i * CELL_SIZE), (GRID_X_START + GRID_WIDTH, GRID_Y_START + i * CELL_SIZE), LINE_WIDTH)
        pygame.draw.line(screen, LINE_COLOR, (GRID_X_START + i * CELL_SIZE, GRID_Y_START), (GRID_X_START + i * CELL_SIZE, GRID_Y_START + GRID_WIDTH), LINE_WIDTH)

def draw_single_piece(row, col, player, progress):
    center_x = GRID_X_START + col * CELL_SIZE + CELL_SIZE // 2
    center_y = GRID_Y_START + row * CELL_SIZE + CELL_SIZE // 2

    if player == "X":
        line_len = (CELL_SIZE // 2 - 20) * progress
        pygame.draw.line(screen, X_COLOR, (center_x - line_len, center_y - line_len), (center_x + line_len, center_y + line_len), X_WIDTH)
        pygame.draw.line(screen, X_COLOR, (center_x - line_len, center_y + line_len), (center_x + line_len, center_y - line_len), X_WIDTH)
    elif player == "O":
        radius = (CELL_SIZE // 2 - 20) * progress
        if radius > O_WIDTH / 2: pygame.draw.circle(screen, O_COLOR, (center_x, center_y), radius, O_WIDTH)

def draw_pieces():
    for row in range(BOARD_ROWS):
        for col in range(BOARD_COLS):
            if board[row][col] in ["X", "O"]: draw_single_piece(row, col, board[row][col], 1.0)
    if animating_piece:
        draw_single_piece(animating_piece['pos'][0], animating_piece['pos'][1], animating_piece['player'], animating_piece['progress'])

def check_win(player):
    for r in range(BOARD_ROWS):
        if all(board[r][c] == player for c in range(BOARD_COLS)): return ("row", r)
    for c in range(BOARD_COLS):
        if all(board[r][c] == player for r in range(BOARD_ROWS)): return ("col", c)
    if all(board[i][i] == player for i in range(3)): return ("diag", 1)
    if all(board[i][2-i] == player for i in range(3)): return ("diag", 2)
    return None

def draw_win_line(win_info, progress):
    if not win_info: return
    win_type, index = win_info
    start_pos, end_pos = None, None
    if win_type == "row":
        start_pos = (GRID_X_START + 10, GRID_Y_START + index * CELL_SIZE + CELL_SIZE / 2)
        end_pos = (GRID_X_START + GRID_WIDTH - 10, GRID_Y_START + index * CELL_SIZE + CELL_SIZE / 2)
    elif win_type == "col":
        start_pos = (GRID_X_START + index * CELL_SIZE + CELL_SIZE / 2, GRID_Y_START + 10)
        end_pos = (GRID_X_START + index * CELL_SIZE + CELL_SIZE / 2, GRID_Y_START + GRID_WIDTH - 10)
    elif win_type == "diag":
        if index == 1:
            start_pos = (GRID_X_START + 20, GRID_Y_START + 20)
            end_pos = (GRID_X_START + GRID_WIDTH - 20, GRID_Y_START + GRID_WIDTH - 20)
        else:
            start_pos = (GRID_X_START + GRID_WIDTH - 20, GRID_Y_START + 20)
            end_pos = (GRID_X_START + 20, GRID_Y_START + GRID_WIDTH - 20)
    
    if start_pos and end_pos:
        anim_x = start_pos[0] + (end_pos[0] - start_pos[0]) * progress
        anim_y = start_pos[1] + (end_pos[1] - start_pos[1]) * progress
        pygame.draw.line(screen, WIN_LINE_COLOR, start_pos, (anim_x, anim_y), WIN_LINE_WIDTH)

def check_draw():
    return all(cell != " " for row in board for cell in row)

def restart_game(full_reset=True):
    global board, current_player, game_over, winner, win_info, animating_piece, animating_win_line, game_mode, minimax_memo
    board = [[" " for _ in range(BOARD_COLS)] for _ in range(BOARD_ROWS)]
    minimax_memo = {}
    current_player = "X"
    game_over = False
    winner = None
    win_info = None
    animating_piece = None
    animating_win_line = None
    if full_reset: game_mode = "menu"
    else:
        if game_mode == 'pvc' and human_player == 'O':
            r, c = computer_move()
            if r is not None:
                board[r][c] = 'placing'
                animating_piece = {'pos': (r, c), 'player': computer_player, 'progress': 0.0}

def minimax(is_maximizing):
    board_tuple = tuple(map(tuple, board))
    if board_tuple in minimax_memo: return minimax_memo[board_tuple]

    if check_win(computer_player): return 1
    if check_win(human_player): return -1
    if check_draw(): return 0
    
    scores = []
    for r in range(3):
        for c in range(3):
            if board[r][c] == ' ':
                board[r][c] = computer_player if is_maximizing else human_player
                scores.append(minimax(not is_maximizing))
                board[r][c] = ' '
    
    result = max(scores) if is_maximizing else min(scores)
    minimax_memo[board_tuple] = result
    return result

def minimax_move():
    minimax_memo.clear()
    best_score = -math.inf
    move = None
    for r in range(3):
        for c in range(3):
            if board[r][c] == ' ':
                board[r][c] = computer_player
                score = minimax(False)
                board[r][c] = ' '
                if score > best_score:
                    best_score = score
                    move = (r, c)
    return move if move else easy_medium_move()

def easy_medium_move():
    empty_cells = [(r, c) for r in range(3) for c in range(3) if board[r][c] == ' ']
    if not empty_cells: return None, None
    if difficulty == "Easy": return random.choice(empty_cells)
    
    for p in [computer_player, human_player]:
        for r, c in empty_cells:
            board[r][c] = p
            if check_win(p):
                board[r][c] = ' '; return r, c
            board[r][c] = ' '
    return random.choice(empty_cells)

def computer_move():
    return minimax_move() if difficulty == 'Hard' else easy_medium_move()

def draw_menu_screen(title, button_keys):
    screen.fill(BG_COLOR)
    title_text = title_font.render(title, True, TEXT_COLOR)
    screen.blit(title_text, (SCREEN_WIDTH/2 - title_text.get_width()/2, 70))
    for key in button_keys:
        text = key.replace("_", " ").title() if "play" not in key else key[-1].upper()
        draw_button(buttons[key], text)

def draw_status():
    if winner: message = f"Player {winner} wins!"
    elif check_draw() and not win_info: message = "It's a draw!"
    else: message = f"Player {current_player}'s turn"
    
    text = status_font.render(message, True, TEXT_COLOR)
    screen.blit(text, (SCREEN_WIDTH/2 - text.get_width()/2, 20))
    
    score_text = score_font.render(f"X: {scores['X']} | O: {scores['O']} | Draw: {scores['Draw']}", True, TEXT_COLOR)
    screen.blit(score_text, (SCREEN_WIDTH/2 - score_text.get_width()/2, 60))

# --- Main Game Loop ---
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: pygame.quit(); sys.exit()
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r: restart_game()
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = event.pos
            if game_mode == "menu":
                if buttons["pvp"].collidepoint(pos): game_mode = "pvp"
                elif buttons["pvc"].collidepoint(pos): game_mode = "difficulty"
            elif game_mode == "difficulty":
                if buttons["easy"].collidepoint(pos): difficulty, game_mode = "Easy", "choose_piece"
                elif buttons["medium"].collidepoint(pos): difficulty, game_mode = "Medium", "choose_piece"
                elif buttons["hard"].collidepoint(pos): difficulty, game_mode = "Hard", "choose_piece"
            elif game_mode == "choose_piece":
                if buttons["play_x"].collidepoint(pos): human_player, computer_player, game_mode = "X", "O", "pvc"
                elif buttons["play_o"].collidepoint(pos): human_player, computer_player, game_mode = "O", "X", "pvc"
                if game_mode == "pvc": restart_game(full_reset=False)
            elif not game_over and not animating_piece and (game_mode == "pvp" or current_player == human_player):
                if GRID_X_START < pos[0] < GRID_X_START + GRID_WIDTH and GRID_Y_START < pos[1] < GRID_Y_START + GRID_WIDTH:
                    r, c = (pos[1] - GRID_Y_START) // CELL_SIZE, (pos[0] - GRID_X_START) // CELL_SIZE
                    if 0 <= r < 3 and 0 <= c < 3 and board[r][c] == " ":
                        board[r][c] = 'placing'
                        place_sound.play()
                        animating_piece = {'pos': (r, c), 'player': current_player, 'progress': 0.0}

    # --- Updates ---
    if animating_piece:
        animating_piece['progress'] = min(1.0, animating_piece['progress'] + ANIMATION_SPEED)
        if animating_piece['progress'] >= 1.0:
            r, c, p = *animating_piece['pos'], animating_piece['player']
            board[r][c] = p
            win_info = check_win(p)
            if win_info:
                winner, game_over = p, True
                scores[p] += 1
                win_sound.play()
                animating_win_line = {'info': win_info, 'progress': 0.0}
            elif check_draw():
                game_over = True
                scores["Draw"] += 1
                draw_sound.play()
            else:
                current_player = "O" if current_player == "X" else "X"
            animating_piece = None
    
    if animating_win_line:
        animating_win_line['progress'] = min(1.0, animating_win_line['progress'] + ANIMATION_SPEED)

    if game_mode == "pvc" and current_player == computer_player and not game_over and not animating_piece:
        r, c = computer_move()
        if r is not None:
            board[r][c] = 'placing'
            place_sound.play()
            animating_piece = {'pos': (r, c), 'player': computer_player, 'progress': 0.0}

    # --- Drawing ---
    screen.fill(BG_COLOR)
    if game_mode in ["pvp", "pvc"]:
        draw_background()
        draw_status()
        draw_pieces()
        if animating_win_line: draw_win_line(animating_win_line['info'], animating_win_line['progress'])
        elif game_over and winner: draw_win_line(win_info, 1.0)
    elif game_mode == "menu": draw_menu_screen("Tic-Tac-Toe", ["pvp", "pvc"])
    elif game_mode == "difficulty": draw_menu_screen("Select Difficulty", ["easy", "medium", "hard"])
    elif game_mode == "choose_piece": draw_menu_screen("Choose Your Piece", ["play_x", "play_o"])
    
    pygame.display.update()

