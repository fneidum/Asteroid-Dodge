"""
Asteroid Dodge
"""

import sys
import os
import random
import pygame

def resource_path(relative_path: str) -> str:
    
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative_path)

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)

# --- Window ------------------------------------------------------------------
SCREEN_W, SCREEN_H = 1200, 900
TARGET_FPS = 60

# --- Game states -------------------------------------------------------------
STATE_MENU     = 0
STATE_PLAYING  = 1
STATE_DYING    = 2
STATE_GAMEOVER = 3

# --- Player ------------------------------------------------------------------
PLAYER_W, PLAYER_H    = 65, 75
PLAYER_HITBOX_INSET   = 8   

# --- Asteroids ---------------------------------------------------------------
ASTEROID_BASE_SIZE  = max(PLAYER_W, PLAYER_H)   # 75 px (default value)
ASTEROID_SIZE_MIN   = int(ASTEROID_BASE_SIZE * 2)    
ASTEROID_SIZE_MAX   = 600                            # hard cap 
ASTEROID_SPEED_MIN  = 1.5   # pixels per frame
ASTEROID_SPEED_MAX  = 5.0
ASTEROID_SPIN_MAX   = 1.8   # degrees per frame

ASTEROID_HITBOX_RATIO = 0.14   


SPAWN_RATE_INITIAL  = 55
SPAWN_RATE_MINIMUM  = 20
SPAWN_RATE_SCORE_STEP = 500   

# --- Coins -------------------------------------------------------------------
COIN_W, COIN_H        = 44, 44
COIN_SPEED_MIN        = 2.0
COIN_SPEED_MAX        = 4.5
COIN_SPAWN_INTERVAL   = 145   

# --- Scoring -----------------------------------------------------------------
SCORE_MAX          = 999_999_999
SCORE_TICK_VALUE   = 1     
SCORE_TICK_INTERVAL = 6   
SCORE_COIN_BONUS   = 100

# --- Explosion ---------------------------------------------------------------
EXPLOSION_W, EXPLOSION_H = 210, 210

# --- UI ----------------------------------------------------------------------
BUTTON_W, BUTTON_H  = 320, 85
BLINK_HALF_PERIOD   = 35  

# --- Scroll speeds -----------------------------------------------------------
MENU_SCROLL_SPEED  = 1.5  
GAME_SCROLL_SPEED  = 2.0   


# =============================================================================
# WINDOW
# =============================================================================
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Asteroid Dodge")
clock = pygame.time.Clock()


# =============================================================================
# ASSET HELPERS
# =============================================================================
def load_image(path: str, per_pixel_alpha: bool = False) -> pygame.Surface:
    surface = pygame.image.load(resource_path(path))
    return surface.convert_alpha() if per_pixel_alpha else surface.convert()


def load_sound(path: str) -> pygame.mixer.Sound:
    return pygame.mixer.Sound(resource_path(path))


def load_font(path: str, size: int) -> pygame.font.Font:
    try:
        return pygame.font.Font(resource_path(path), size)
    except FileNotFoundError:
        return pygame.font.SysFont(None, size)


# =============================================================================
# IMAGES
# =============================================================================

# --- Menu background ----------------------------------
_menu_bg = pygame.transform.scale(
    load_image("img/start_gamebg.jpg"), (SCREEN_W, SCREEN_H)
)
menu_tile = pygame.Surface((SCREEN_W * 2, SCREEN_H))
menu_tile.blit(_menu_bg, (0, 0))
menu_tile.blit(pygame.transform.flip(_menu_bg, True, False), (SCREEN_W, 0))

# --- In-game background ---------------------------------
_game_bg = pygame.transform.scale(
    load_image("img/ingame_bg.png"), (SCREEN_W, SCREEN_H)
)

game_tile = pygame.Surface((SCREEN_W, SCREEN_H * 2))
game_tile.blit(_game_bg, (0, 0))
game_tile.blit(pygame.transform.flip(_game_bg, False, True), (0, SCREEN_H))

# --- UI --------------------------------------------------------------
_start_btn_raw = load_image("img/start_button.jpg")
_start_btn_raw.set_colorkey((255, 255, 255))   
start_button = pygame.transform.scale(_start_btn_raw, (BUTTON_W, BUTTON_H))

coin_image      = pygame.transform.scale(load_image("img/coin.png",    True), (COIN_W, COIN_H))
player_image    = pygame.transform.scale(load_image("img/player.png",  True), (PLAYER_W, PLAYER_H))
asteroid_source = load_image("img/Asteroid.png", True)   

_explosion_raw = load_image("img/death_explode.jpg")
_explosion_raw.set_colorkey((255, 255, 255))   
explosion_image = pygame.transform.scale(_explosion_raw, (EXPLOSION_W, EXPLOSION_H))


# =============================================================================
# FONTS
# =============================================================================
font_title    = load_font("font/font.ttf", 82)
font_gameover = load_font("font/font.ttf", 96)
font_score_lg = load_font("font/font.ttf", 60)   
font_score_hud = load_font("font/font.ttf", 46)  
font_small    = load_font("font/font.ttf", 38)   


# =============================================================================
# SOUNDS
# =============================================================================
snd_menu_theme    = load_sound("sound/menu_theme.mp3")
snd_game_theme    = load_sound("sound/game_theme.mp3")
snd_start_click   = load_sound("sound/start_game.mp3")
snd_coin_collect  = load_sound("sound/coin.mp3")
snd_death_impact  = load_sound("sound/death_sound.mp3")
snd_death_music   = load_sound("sound/death_music.mp3")
snd_gameover      = load_sound("sound/gameover_music.mp3")

# Channels
channel_music    = pygame.mixer.Channel(0)
channel_sequence = pygame.mixer.Channel(1)
channel_sfx      = pygame.mixer.Channel(2)

EVENT_SEQUENCE_DONE = pygame.USEREVENT + 1
channel_sequence.set_endevent(EVENT_SEQUENCE_DONE)


# =============================================================================
# SHARED / CACHED SURFACES
# =============================================================================
_gameover_overlay = pygame.Surface((SCREEN_W, SCREEN_H))
_gameover_overlay.set_alpha(165)
_gameover_overlay.fill((0, 0, 0))


# =============================================================================
# TEXT RENDERING HELPER
# =============================================================================

_OUTLINE_OFFSETS = [(-2, -2), (-2, 0), (-2, 2),
                    ( 0, -2),           ( 0, 2),
                    ( 2, -2), ( 2, 0), ( 2, 2)]

def draw_outlined_text(
    surface: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    x: int,
    y: int,
    center: bool = False,
    align_right: bool = False,
) -> None:

    white_surf = font.render(text, True, (255, 255, 255))
    black_surf = font.render(text, True, (  0,   0,   0))
    text_w, text_h = white_surf.get_size()

    if center:
        draw_x = x - text_w // 2
        draw_y = y - text_h // 2
    elif align_right:
        draw_x = x - text_w
        draw_y = y
    else:
        draw_x, draw_y = x, y

    for ox, oy in _OUTLINE_OFFSETS:
        surface.blit(black_surf, (draw_x + ox, draw_y + oy))
    surface.blit(white_surf, (draw_x, draw_y))


# =============================================================================
# GAME OBJECTS
# =============================================================================

class Asteroid:
    def __init__(self) -> None:
        size_factor  = random.uniform(2.0, 10.0)
        self.size    = min(int(ASTEROID_BASE_SIZE * size_factor), ASTEROID_SIZE_MAX)

        # rotate rck
        self.base_image     = pygame.transform.scale(asteroid_source, (self.size, self.size))
        self.angle          = random.uniform(0.0, 360.0)
        self.rotation_speed = random.uniform(-ASTEROID_SPIN_MAX, ASTEROID_SPIN_MAX)

        # Spawn rock 
        self.x          = float(random.randint(-self.size // 4, SCREEN_W - self.size * 3 // 4))
        self.y          = float(-self.size - 5)
        self.fall_speed = random.uniform(ASTEROID_SPEED_MIN, ASTEROID_SPEED_MAX)

        self._rebuild_rotated_surface()

    def _rebuild_rotated_surface(self) -> None:
        self.image = pygame.transform.rotate(self.base_image, self.angle)
        self.rect  = self.image.get_rect(
            center=(int(self.x + self.size // 2),
                    int(self.y + self.size // 2))
        )

    def update(self) -> None:
        self.y     += self.fall_speed
        self.angle += self.rotation_speed
        self._rebuild_rotated_surface()

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.image, self.rect.topleft)

    def is_off_screen(self) -> bool:
        return self.y > SCREEN_H + self.size

    def collision_rect(self) -> pygame.Rect:
        cx, cy    = self.rect.center
        half_size = int(self.size * ASTEROID_HITBOX_RATIO)
        return pygame.Rect(cx - half_size, cy - half_size,
                           half_size * 2,  half_size * 2)


class Coin:

    def __init__(self) -> None:
        self.x     = random.randint(20, SCREEN_W - COIN_W - 20)
        self.y     = float(-COIN_H)
        self.speed = random.uniform(COIN_SPEED_MIN, COIN_SPEED_MAX)
        self.rect  = pygame.Rect(self.x, 0, COIN_W, COIN_H)

    def update(self) -> None:
        self.y      += self.speed
        self.rect.y  = int(self.y)

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(coin_image, (self.x, int(self.y)))

    def is_off_screen(self) -> bool:
        return self.y > SCREEN_H


# =============================================================================
# MAIN GAME CONTROLLER
# =============================================================================

class Game:

    def __init__(self) -> None:
        self.state = STATE_MENU
        self.score = 0

        # bg scroll positions 
        self.menu_scroll_x = 0.0   # wraps at SCREEN_W * 2
        self.game_scroll_y = 0.0   # wraps at SCREEN_H * 2

        # Player ship position
        self.player_x = float(SCREEN_W // 2 - PLAYER_W // 2)
        self.player_y = float(SCREEN_H - 200)

        # game objs
        self.asteroids: list = []
        self.coins:     list = []

        # counter
        self.asteroid_timer = 0
        self.coin_timer     = 0
        self.score_timer    = 0

        # Start-button 
        self.blink_counter  = 0
        self.button_visible = True

        # xplosion position
        self.explosion_x = 0
        self.explosion_y = 0

        #   0 = idle,  1 = impact SFX,  2 = death music
        self.death_step = 0

        channel_music.play(snd_menu_theme, loops=-1)

    # -------------------------------------------------------------------------
    # State 
    # -------------------------------------------------------------------------

    def _go_to_playing(self) -> None:

        channel_sfx.play(snd_start_click)
        channel_music.stop()
        channel_sequence.stop()

        self.score          = 0
        self.asteroids.clear()
        self.coins.clear()
        self.asteroid_timer = 0
        self.coin_timer     = 0
        self.score_timer    = 0
        self.game_scroll_y  = 0.0
        self.state          = STATE_PLAYING

        pygame.mouse.set_visible(False)
        channel_music.play(snd_game_theme, loops=-1)

    def _go_to_dying(self) -> None:
        channel_music.stop()
        channel_sfx.stop()

        # player explosion 
        self.explosion_x = int(self.player_x + PLAYER_W // 2 - EXPLOSION_W // 2)
        self.explosion_y = int(self.player_y + PLAYER_H // 2 - EXPLOSION_H // 2)

        self.state      = STATE_DYING
        self.death_step = 1

        pygame.mouse.set_visible(True)
        channel_sequence.play(snd_death_impact)

    def _go_to_gameover(self) -> None:
        self.state      = STATE_GAMEOVER
        self.death_step = 0
        channel_sequence.play(snd_gameover)

    def _go_to_menu(self) -> None:
        self.state = STATE_MENU
        channel_sequence.stop()
        channel_sfx.stop()
        pygame.mouse.set_visible(True)
        channel_music.play(snd_menu_theme, loops=-1)

    # -------------------------------------------------------------------------
    # Event 
    # -------------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == EVENT_SEQUENCE_DONE and self.state == STATE_DYING:
            if self.death_step == 1:
                channel_sequence.play(snd_death_music)
                self.death_step = 2
            elif self.death_step == 2:
                self._go_to_gameover()

        if self.state == STATE_MENU:
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                self._go_to_playing()

        if self.state == STATE_GAMEOVER:
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                self._go_to_menu()

    # -------------------------------------------------------------------------
    # Update logic
    # -------------------------------------------------------------------------

    def update(self) -> None:
        if self.state == STATE_MENU:
            self._update_menu()
        elif self.state == STATE_PLAYING:
            self._update_playing()

    def _update_menu(self) -> None:
        self.menu_scroll_x += MENU_SCROLL_SPEED
        if self.menu_scroll_x >= SCREEN_W * 2:
            self.menu_scroll_x -= SCREEN_W * 2

        self.blink_counter += 1
        if self.blink_counter >= BLINK_HALF_PERIOD:
            self.button_visible = not self.button_visible
            self.blink_counter  = 0

    def _update_playing(self) -> None:
        # --- mouse controller -----------------------------------
        mouse_x, mouse_y = pygame.mouse.get_pos()
        self.player_x = max(0.0, min(float(SCREEN_W - PLAYER_W), float(mouse_x - PLAYER_W // 2)))
        self.player_y = max(0.0, min(float(SCREEN_H - PLAYER_H), float(mouse_y - PLAYER_H // 2)))

        # --- scroll the background tile downward -----------------------------
        self.game_scroll_y += GAME_SCROLL_SPEED
        if self.game_scroll_y >= SCREEN_H * 2:
            self.game_scroll_y -= SCREEN_H * 2

        # --- Spawn asteroids ---------
        self.asteroid_timer += 1
        spawn_rate = max(SPAWN_RATE_MINIMUM,
                         SPAWN_RATE_INITIAL - self.score // SPAWN_RATE_SCORE_STEP)
        if self.asteroid_timer >= spawn_rate:
            self.asteroids.append(Asteroid())
            self.asteroid_timer = 0

        # --- Spawn coin ---------------------------------
        self.coin_timer += 1
        if self.coin_timer >= COIN_SPAWN_INTERVAL:
            self.coins.append(Coin())
            self.coin_timer = 0

        # --- Advance ingame (remove asteroid) -----------------------------
        for asteroid in self.asteroids[:]:
            asteroid.update()
            if asteroid.is_off_screen():
                self.asteroids.remove(asteroid)

        for coin in self.coins[:]:
            coin.update()
            if coin.is_off_screen():
                self.coins.remove(coin)

        # --- core increase ovt ------------------------------
        self.score_timer += 1
        if self.score_timer >= SCORE_TICK_INTERVAL:
            self.score       = min(self.score + SCORE_TICK_VALUE, SCORE_MAX)
            self.score_timer = 0

        # --- Player collision --------
        player_rect = pygame.Rect(
            int(self.player_x) + PLAYER_HITBOX_INSET,
            int(self.player_y) + PLAYER_HITBOX_INSET,
            PLAYER_W - PLAYER_HITBOX_INSET * 2,
            PLAYER_H - PLAYER_HITBOX_INSET * 2,
        )

        # --- Coin collection -------------------------------------------------
        for coin in self.coins[:]:
            if player_rect.colliderect(coin.rect):
                self.coins.remove(coin)
                channel_sfx.play(snd_coin_collect)
                self.score = min(self.score + SCORE_COIN_BONUS, SCORE_MAX)

        # --- Asteroid collision----------------------------------------
        for asteroid in self.asteroids:
            if player_rect.colliderect(asteroid.collision_rect()):
                self._go_to_dying()
                return   

    # -------------------------------------------------------------------------
    # Drawing
    # -------------------------------------------------------------------------

    def draw(self) -> None:
        screen.fill((0, 0, 0))

        if self.state == STATE_MENU:
            self._draw_menu()
        elif self.state == STATE_PLAYING:
            self._draw_playing()
        elif self.state == STATE_DYING:
            self._draw_dying()
        elif self.state == STATE_GAMEOVER:
            self._draw_gameover()

        pygame.display.flip()

    def _draw_menu(self) -> None:
        scroll = int(self.menu_scroll_x)
        screen.blit(menu_tile, (-scroll,               0))
        screen.blit(menu_tile, (-scroll + SCREEN_W * 2, 0))

        draw_outlined_text(screen, "ASTEROID DODGE", font_title,
                           SCREEN_W // 2, 165, center=True)

        if self.button_visible:
            screen.blit(start_button, (SCREEN_W // 2 - BUTTON_W // 2,
                                       SCREEN_H // 2 - BUTTON_H // 2))

        draw_outlined_text(screen, "Press any key to continue", font_small,
                           SCREEN_W // 2, SCREEN_H // 2 + 85, center=True)

    def _draw_space_scene(self) -> None:

        scroll = int(self.game_scroll_y)
        screen.blit(game_tile, (0, -scroll))
        screen.blit(game_tile, (0, -scroll + SCREEN_H * 2))

        for asteroid in self.asteroids:
            asteroid.draw(screen)
        for coin in self.coins:
            coin.draw(screen)

    def _draw_playing(self) -> None:
        self._draw_space_scene()

        screen.blit(player_image, (int(self.player_x), int(self.player_y)))

        score_text = str(self.score).zfill(9)
        draw_outlined_text(screen, score_text, font_score_hud,
                           SCREEN_W - 15, 15, align_right=True)

    def _draw_dying(self) -> None:
        self._draw_space_scene()
        screen.blit(explosion_image, (self.explosion_x, self.explosion_y))

    def _draw_gameover(self) -> None:
        scroll = int(self.game_scroll_y)
        screen.blit(game_tile, (0, -scroll))
        screen.blit(game_tile, (0, -scroll + SCREEN_H * 2))

        screen.blit(_gameover_overlay, (0, 0))

        draw_outlined_text(screen, "GAME OVER", font_gameover,
                           SCREEN_W // 2, SCREEN_H // 2 - 135, center=True)
        draw_outlined_text(screen, str(self.score).zfill(9), font_score_lg,
                           SCREEN_W // 2, SCREEN_H // 2 + 10, center=True)
        draw_outlined_text(screen, "Press any key to continue", font_small,
                           SCREEN_W // 2, SCREEN_H // 2 + 115, center=True)


# =============================================================================
# MAIN LOOP
# =============================================================================

def main() -> None:
    game = Game()
    while True:
        for event in pygame.event.get():
            game.handle_event(event)
        game.update()
        game.draw()
        clock.tick(TARGET_FPS)


if __name__ == "__main__":
    main()
