"""
Simple Tetris in Python with Pygame
Single-file implementation — no assets required.

Controls:
Left/Right arrows : move
Up arrow / X      : rotate clockwise
Z                 : rotate counter-clockwise
Down arrow        : soft drop
Space             : hard drop
C                 : hold (optional toggle in this version? not implemented)
Esc               : quit
"""

import pygame
import random
import sys

# ---------- Configuration ----------
CELL_SIZE = 30
COLUMNS = 10
ROWS = 20
PLAY_WIDTH = CELL_SIZE * COLUMNS
PLAY_HEIGHT = CELL_SIZE * ROWS
SIDE_PANEL = 200
WINDOW_WIDTH = PLAY_WIDTH + SIDE_PANEL
WINDOW_HEIGHT = PLAY_HEIGHT
FPS = 60

# On-screen arrow pad settings (in side panel)
PAD_RADIUS = 28
PAD_GAP = 12
PAD_REPEAT_MS = 120  # repeat interval while holding (ms)

# Colors (R,G,B)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
WHITE = (255, 255, 255)
COLORS = [
    (0, 240, 240),   # I - cyan
    (0, 0, 240),     # J - blue
    (240, 160, 0),   # L - orange
    (240, 240, 0),   # O - yellow
    (0, 240, 0),     # S - green
    (160, 0, 240),   # T - purple
    (240, 0, 0),     # Z - red
]

# Tetromino shapes (4x4 matrices using lists of rotation states)
# Rotations are listed as arrays of strings for clarity.
TETROMINOES = {
    'I': [
        ["0000",
         "1111",
         "0000",
         "0000"],
        ["0010",
         "0010",
         "0010",
         "0010"]
    ],
    'J': [
        ["100",
         "111",
         "000"],
        ["011",
         "010",
         "010"],
        ["000",
         "111",
         "001"],
        ["010",
         "010",
         "110"]
    ],
    'L': [
        ["001",
         "111",
         "000"],
        ["010",
         "010",
         "011"],
        ["000",
         "111",
         "100"],
        ["110",
         "010",
         "010"]
    ],
    'O': [
        ["11",
         "11"]
    ],
    'S': [
        ["011",
         "110",
         "000"],
        ["010",
         "011",
         "001"]
    ],
    'T': [
        ["010",
         "111",
         "000"],
        ["010",
         "011",
         "010"],
        ["000",
         "111",
         "010"],
        ["010",
         "110",
         "010"]
    ],
    'Z': [
        ["110",
         "011",
         "000"],
        ["001",
         "011",
         "010"]
    ]
}

# Map piece keys to colors index
PIECE_KEYS = list(TETROMINOES.keys())

# ---------- Helper functions ----------
def rotate(shape):
    """Return rotated version (90 deg clockwise) of a shape (list of strings)."""
    # Convert to grid of chars
    grid = [list(row) for row in shape]
    h = len(grid)
    w = len(grid[0])
    # New grid is w x h
    new = []
    for x in range(w):
        new_row = []
        for y in range(h - 1, -1, -1):
            new_row.append(grid[y][x])
        new.append("".join(new_row))
    return new

def shape_cells(shape, offset_x, offset_y):
    """Yield (x,y) positions of occupied cells for a given shape state and offset."""
    for y, row in enumerate(shape):
        for x, ch in enumerate(row):
            if ch == '1':
                yield offset_x + x, offset_y + y

def make_grid(locked_positions={}):
    """Create grid (rows x columns) and fill with locked positions colors or 0."""
    grid = [[None for _ in range(COLUMNS)] for _ in range(ROWS)]
    for (x, y), color in locked_positions.items():
        if 0 <= y < ROWS and 0 <= x < COLUMNS:
            grid[y][x] = color
    return grid

def valid_space(shape, offset_x, offset_y, locked):
    """Return True if shape at offset doesn't collide or go out of bounds."""
    for x, y in shape_cells(shape, offset_x, offset_y):
        if x < 0 or x >= COLUMNS or y >= ROWS:
            return False
        if y >= 0 and (x, y) in locked:
            return False
    return True

def clear_lines(grid, locked):
    """Check for full lines, remove them, shift down, return lines_cleared."""
    lines_to_clear = []
    for y in range(ROWS):
        if all(grid[y][x] is not None for x in range(COLUMNS)):
            lines_to_clear.append(y)
    if not lines_to_clear:
        return 0
    # Remove from locked and move everything above down
    for row in reversed(lines_to_clear):
        for x in range(COLUMNS):
            if (x, row) in locked:
                del locked[(x, row)]
    # Shift down
    for y in sorted([r for r in range(ROWS) if r < max(lines_to_clear)], reverse=True):
        # for each piece above highest cleared line
        shift = sum(1 for cleared in lines_to_clear if y < cleared)
        if shift > 0:
            for x in range(COLUMNS):
                if (x, y) in locked:
                    locked[(x, y + shift)] = locked.pop((x, y))
    return len(lines_to_clear)

# ---------- Piece class ----------
class Piece:
    def __init__(self, type_key):
        self.type = type_key
        self.rotations = TETROMINOES[type_key]
        self.rotation = 0
        self.shape = self.rotations[self.rotation]
        self.x = COLUMNS // 2 - len(self.shape[0]) // 2
        self.y = -len(self.shape)  # start above the grid
        self.color = COLORS[PIECE_KEYS.index(type_key)]
    def rotate(self, locked):
        old = self.rotation
        self.rotation = (self.rotation + 1) % len(self.rotations)
        self.shape = self.rotations[self.rotation]
        if not valid_space(self.shape, self.x, self.y, locked):
            # try simple wall kicks (left/right)
            for dx in (-1, 1, -2, 2):
                if valid_space(self.shape, self.x + dx, self.y, locked):
                    self.x += dx
                    return True
            # revert
            self.rotation = old
            self.shape = self.rotations[self.rotation]
            return False
        return True
    def rotate_ccw(self, locked):
        old = self.rotation
        self.rotation = (self.rotation - 1) % len(self.rotations)
        self.shape = self.rotations[self.rotation]
        if not valid_space(self.shape, self.x, self.y, locked):
            for dx in (-1, 1, -2, 2):
                if valid_space(self.shape, self.x + dx, self.y, locked):
                    self.x += dx
                    return True
            self.rotation = old
            self.shape = self.rotations[self.rotation]
            return False
        return True

# ---------- Game class ----------
class Tetris:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Tetris - Python")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 20)
        self.large_font = pygame.font.SysFont("monospace", 36, bold=True)
        self.reset()

        # on-screen pad state: map action -> {'holding': bool, 'last': timestamp}
        # actions: 'left','right','down','rotate'
        self.pad_state = {a: {'holding': False, 'last': 0} for a in ('left', 'right', 'down', 'rotate')}

    def reset(self):
        self.locked = {}  # (x,y) -> color
        self.grid = make_grid(self.locked)
        self.current = self.get_new_piece()
        self.next_piece = self.get_new_piece()
        self.fall_time = 0.0
        self.fall_speed = 0.6  # seconds per cell (will speed up as level increases)
        self.score = 0
        self.lines = 0
        self.level = 1
        self.game_over = False

    def get_new_piece(self):
        key = random.choice(PIECE_KEYS)
        return Piece(key)

    def draw_grid(self):
        # background
        self.screen.fill(BLACK)
        # play area border
        pygame.draw.rect(self.screen, GRAY, (0, 0, PLAY_WIDTH, PLAY_HEIGHT), 4)

        # grid lines
        for x in range(COLUMNS):
            for y in range(ROWS):
                rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                pygame.draw.rect(self.screen, (20, 20, 20), rect, 1)

        # locked blocks
        for (x, y), color in self.locked.items():
            if y >= 0:
                pygame.draw.rect(self.screen, color,
                                 (x * CELL_SIZE + 1, y * CELL_SIZE + 1, CELL_SIZE - 2, CELL_SIZE - 2))

        # current piece
        for x, y in shape_cells(self.current.shape, self.current.x, self.current.y):
            if y >= 0:
                pygame.draw.rect(self.screen, self.current.color,
                                (x * CELL_SIZE + 1, y * CELL_SIZE + 1, CELL_SIZE - 2, CELL_SIZE - 2))

        # next piece panel
        nx = PLAY_WIDTH + 20
        ny = 20
        label = self.font.render("Next:", True, WHITE)
        self.screen.blit(label, (nx, ny))
        for x, y in shape_cells(self.next_piece.shape, 0, 0):
            px = nx + (x) * CELL_SIZE
            py = ny + 30 + (y) * CELL_SIZE
            pygame.draw.rect(self.screen, self.next_piece.color,
                             (px + 1, py + 1, CELL_SIZE - 2, CELL_SIZE - 2))
        # scoreboard
        score_label = self.font.render(f"Score: {self.score}", True, WHITE)
        lines_label = self.font.render(f"Lines: {self.lines}", True, WHITE)
        level_label = self.font.render(f"Level: {self.level}", True, WHITE)
        self.screen.blit(score_label, (nx, 200))
        self.screen.blit(lines_label, (nx, 230))
        self.screen.blit(level_label, (nx, 260))
    # (arrow pad drawn from run loop to avoid indentation issues)

    def draw_arrow_pad(self):
        """Draw four circular buttons (left, right, down, rotate) in side panel."""
        # center x of side panel
        cx = PLAY_WIDTH + SIDE_PANEL // 2
        # place pad near bottom of side panel
        base_y = PLAY_HEIGHT - 120
        # positions: rotate (top), left (left), down (bottom center), right (right)
        positions = {
            'rotate': (cx, base_y - PAD_RADIUS - PAD_GAP),
            'left': (cx - PAD_RADIUS - PAD_GAP - PAD_RADIUS, base_y),
            'down': (cx, base_y),
            'right': (cx + PAD_RADIUS + PAD_GAP + PAD_RADIUS, base_y)
        }
        for name, (x, y) in positions.items():
            color = (80, 80, 80) if not self.pad_state[name]['holding'] else (150, 150, 150)
            pygame.draw.circle(self.screen, color, (x, y), PAD_RADIUS)
            pygame.draw.circle(self.screen, WHITE, (x, y), PAD_RADIUS, 2)
            # draw symbol
            if name == 'left':
                pts = [(x + 8, y - 12), (x - 8, y), (x + 8, y + 12)]
            elif name == 'right':
                pts = [(x - 8, y - 12), (x + 8, y), (x - 8, y + 12)]
            elif name == 'down':
                pts = [(x - 12, y - 2), (x + 12, y - 2), (x, y + 12)]
            else:  # rotate / up
                pts = [(x - 10, y + 8), (x + 10, y + 8), (x, y - 8)]
            pygame.draw.polygon(self.screen, WHITE, pts)

    def _point_in_circle(self, px, py, cx, cy, r):
        return (px - cx) ** 2 + (py - cy) ** 2 <= r * r

    def _pad_action_at(self, mx, my):
        """Return action name if (mx,my) is over a pad button, else None."""
        cx = PLAY_WIDTH + SIDE_PANEL // 2
        base_y = PLAY_HEIGHT - 120
        positions = {
            'rotate': (cx, base_y - PAD_RADIUS - PAD_GAP),
            'left': (cx - PAD_RADIUS - PAD_GAP - PAD_RADIUS, base_y),
            'down': (cx, base_y),
            'right': (cx + PAD_RADIUS + PAD_GAP + PAD_RADIUS, base_y)
        }
        for name, (x, y) in positions.items():
            if self._point_in_circle(mx, my, x, y, PAD_RADIUS):
                return name
        return None

    def _perform_pad_action(self, act):
        """Map pad action to game moves (immediate)."""
        if act == 'left':
            if valid_space(self.current.shape, self.current.x - 1, self.current.y, self.locked):
                self.current.x -= 1
        elif act == 'right':
            if valid_space(self.current.shape, self.current.x + 1, self.current.y, self.locked):
                self.current.x += 1
        elif act == 'down':
            if valid_space(self.current.shape, self.current.x, self.current.y + 1, self.locked):
                self.current.y += 1
        elif act == 'rotate':
            self.current.rotate(self.locked)

    def _handle_pad_repeats(self, current_time_ms):
        for act, state in self.pad_state.items():
            if state['holding']:
                if current_time_ms - state['last'] >= PAD_REPEAT_MS:
                    self._perform_pad_action(act)
                    state['last'] = current_time_ms

    def lock_piece(self):
        for x, y in shape_cells(self.current.shape, self.current.x, self.current.y):
            # Game over condition if locked above top
            if y < 0:
                self.game_over = True
            else:
                self.locked[(x, y)] = self.current.color
        # update grid
        self.grid = make_grid(self.locked)
        cleared = clear_lines(self.grid, self.locked)
        if cleared:
            # scoring: standard Tetris scoring (single, double, triple, tetris)
            score_table = {1: 40, 2: 100, 3: 300, 4: 1200}
            self.score += score_table.get(cleared, 0) * self.level
            self.lines += cleared
            # level up every 10 lines
            self.level = self.lines // 10 + 1
            # speed up (make fall_speed smaller)
            self.fall_speed = max(0.05, 0.6 - (self.level - 1) * 0.05)
        # spawn next
        self.current = self.next_piece
        self.next_piece = self.get_new_piece()

    def hard_drop(self):
        while valid_space(self.current.shape, self.current.x, self.current.y + 1, self.locked):
            self.current.y += 1
        self.lock_piece()

    def run(self):
        drop_event = pygame.USEREVENT + 1
        pygame.time.set_timer(drop_event, int(self.fall_speed * 1000))
        last_time = pygame.time.get_ticks()
        while True:
            if self.game_over:
                self.show_game_over()
                return

            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    if event.key == pygame.K_LEFT:
                        if valid_space(self.current.shape, self.current.x - 1, self.current.y, self.locked):
                            self.current.x -= 1
                    if event.key == pygame.K_RIGHT:
                        if valid_space(self.current.shape, self.current.x + 1, self.current.y, self.locked):
                            self.current.x += 1
                    if event.key in (pygame.K_UP, pygame.K_x):
                        self.current.rotate(self.locked)
                    if event.key == pygame.K_z:
                        self.current.rotate_ccw(self.locked)
                    if event.key == pygame.K_DOWN:
                        # soft drop by moving down one cell
                        if valid_space(self.current.shape, self.current.x, self.current.y + 1, self.locked):
                            self.current.y += 1
                    if event.key == pygame.K_SPACE:
                        self.hard_drop()

                # Mouse / touch handling for on-screen pad
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    act = self._pad_action_at(mx, my)
                    if act:
                        # perform immediate action
                        self._perform_pad_action(act)
                        # mark holding for repeat
                        self.pad_state[act]['holding'] = True
                        self.pad_state[act]['last'] = pygame.time.get_ticks()
                        continue

                if event.type == pygame.MOUSEBUTTONUP:
                    # release all pad holds
                    for s in self.pad_state.values():
                        s['holding'] = False

                if event.type == pygame.MOUSEMOTION:
                    # if pointer moves while holding, stop holds when moving off
                    if any(s['holding'] for s in self.pad_state.values()):
                        mx, my = event.pos
                        act = self._pad_action_at(mx, my)
                        if not act:
                            for s in self.pad_state.values():
                                s['holding'] = False

            # gravity handling with timer
            current_time = pygame.time.get_ticks()
            # dynamic timer based on level/fall_speed
            if current_time - last_time > int(self.fall_speed * 1000):
                last_time = current_time
                if valid_space(self.current.shape, self.current.x, self.current.y + 1, self.locked):
                    self.current.y += 1
                else:
                    # lock piece
                    self.lock_piece()
                    if self.game_over:
                        self.show_game_over()
                        return

            # Draw
            self.draw_grid()
            # draw pad overlay (separate so layout is stable)
            self.draw_arrow_pad()
            # handle pad repeats (actions while mouse held)
            self._handle_pad_repeats(pygame.time.get_ticks())
            pygame.display.update()

    def show_game_over(self):
        self.screen.fill(BLACK)
        over = self.large_font.render("GAME OVER", True, WHITE)
        score_text = self.font.render(f"Score: {self.score}", True, WHITE)
        inst = self.font.render("Press R to restart or Esc to quit", True, WHITE)
        self.screen.blit(over, (PLAY_WIDTH // 2 - over.get_width() // 2, PLAY_HEIGHT // 2 - 60))
        self.screen.blit(score_text, (PLAY_WIDTH // 2 - score_text.get_width() // 2, PLAY_HEIGHT // 2 - 10))
        self.screen.blit(inst, (PLAY_WIDTH // 2 - inst.get_width() // 2, PLAY_HEIGHT // 2 + 30))
        pygame.display.update()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    if event.key == pygame.K_r:
                        self.reset()
                        self.run()
                        return

# ---------- Run the game ----------
if __name__ == "__main__":
    game = Tetris()
    game.run()
