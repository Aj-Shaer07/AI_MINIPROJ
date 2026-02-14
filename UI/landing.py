import pygame
import sys


def show_and_run(start_callable):
    """Display a landing + settings flow. When the user chooses options
    and clicks Play, call `start_callable(start_time_seconds, increment_seconds, human_color)`.
    """
    import values

    pygame.init()
    window_w, window_h = values.LANDING_WINDOW_WIDTH, values.LANDING_WINDOW_HEIGHT
    screen = pygame.display.set_mode((window_w, window_h))
    pygame.display.set_caption('Chess — Landing')
    clock = pygame.time.Clock()

    try:
        title_font = pygame.font.SysFont(None, values.LANDING_TITLE_FONT_SIZE)
        body_font = pygame.font.SysFont(None, values.LANDING_BODY_FONT_SIZE)
    except Exception:
        pygame.font.init()
        title_font = pygame.font.SysFont(None, values.LANDING_TITLE_FONT_SIZE)
        body_font = pygame.font.SysFont(None, values.LANDING_BODY_FONT_SIZE)

    # UI state
    state = 'landing'  # or 'settings'
    time_options = [60, 180, 300, 600]
    time_labels = ['1m', '3m', '5m', '10m']
    selected_time = 300
    increment_options = [0, 1, 2, 5]
    selected_increment = 0

    def draw_button(rect, text, active=False):
        # Active buttons should not show hover effect; hover only applies to non-active buttons
        if active:
            color = values.LANDING_BUTTON_BG
        else:
            try:
                hover = rect.collidepoint(pygame.mouse.get_pos())
            except Exception:
                hover = False
            color = values.LANDING_BUTTON_HOVER if hover else values.LANDING_BUTTON_INACTIVE
        pygame.draw.rect(screen, color, rect, border_radius=values.LANDING_BUTTON_RADIUS)
        txt = body_font.render(text, True, values.LANDING_BUTTON_TEXT)
        screen.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))

    # Precompute common rects so drawing and hit-testing match exactly
    start_rect = pygame.Rect((window_w - values.LANDING_BUTTON_WIDTH) // 2, 220, values.LANDING_BUTTON_WIDTH, values.LANDING_BUTTON_HEIGHT)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if state == 'landing':
                    # Start button — use precomputed rect for hit-testing
                    if start_rect.collidepoint((mx, my)):
                        state = 'settings'
                else:
                    # settings interactions
                    # time option buttons (match drawing y=140)
                    for i in range(len(time_options)):
                        tr = pygame.Rect(40 + i * 150, 140, 120, 36)
                        if tr.collidepoint((mx, my)):
                            selected_time = time_options[i]
                    # increment buttons (match drawing y=210)
                    for i in range(len(increment_options)):
                        ir = pygame.Rect(40 + i * 120, 210, 100, 32)
                        if ir.collidepoint((mx, my)):
                            selected_increment = increment_options[i]
                    # play and back
                    play_rect = pygame.Rect(window_w - 160, window_h - 84, 120, 48)
                    back_rect = pygame.Rect(40, window_h - 84, 120, 48)
                    if back_rect.collidepoint((mx, my)):
                        state = 'landing'
                    if play_rect.collidepoint((mx, my)):
                        # launch game with selected options
                        try:
                            pygame.display.quit()
                            pygame.quit()
                        except Exception:
                            pass
                        start_callable(start_time=selected_time, increment=selected_increment)
                        return

        screen.fill(values.LANDING_BG_COLOR)

        if state == 'landing':
            title_surf = title_font.render("Chess — AI Engine", True, values.LANDING_TITLE_COLOR)
            screen.blit(title_surf, (window_w // 2 - title_surf.get_width() // 2, 48))
            subtitle = body_font.render("A lightweight chess UI with a simple AI", True, values.LANDING_SUBTITLE_COLOR)
            screen.blit(subtitle, (window_w // 2 - subtitle.get_width() // 2, 110))
            # Start button (use same rect for drawing and hit-testing)
            # Do NOT apply hover effect for the main Start Game button — always render as primary
            pygame.draw.rect(screen, values.LANDING_BUTTON_BG, start_rect, border_radius=values.LANDING_BUTTON_RADIUS)
            btn_text = title_font.render("Start Game", True, values.LANDING_BUTTON_TEXT)
            screen.blit(btn_text, (start_rect.centerx - btn_text.get_width() // 2, start_rect.centery - btn_text.get_height() // 2))
        else:
            # Settings screen
            title_surf = title_font.render("Game Settings", True, values.LANDING_TITLE_COLOR)
            screen.blit(title_surf, (40, 24))

            # Time options
            ts = body_font.render("Time:", True, values.LANDING_SUBTITLE_COLOR)
            screen.blit(ts, (40, 120))
            for i, t in enumerate(time_options):
                tr = pygame.Rect(40 + i * 150, 140, 120, 36)
                label = time_labels[i]
                draw_button(tr, label, active=(selected_time == t))

            # Increment options
            ins = body_font.render("Increment (s):", True, values.LANDING_SUBTITLE_COLOR)
            screen.blit(ins, (40, 190))
            for i, inc in enumerate(increment_options):
                ir = pygame.Rect(40 + i * 120, 210, 100, 32)
                draw_button(ir, str(inc), active=(selected_increment == inc))

            # Controls
            back_rect = pygame.Rect(40, window_h - 84, 120, 48)
            play_rect = pygame.Rect(window_w - 160, window_h - 84, 120, 48)
            draw_button(back_rect, "Back")
            pygame.draw.rect(screen, values.LANDING_BUTTON_BG, play_rect, border_radius=10)
            play_txt = body_font.render("Play", True, values.LANDING_BUTTON_TEXT)
            screen.blit(play_txt, (play_rect.centerx - play_txt.get_width() // 2, play_rect.centery - play_txt.get_height() // 2))

            # summary
            summary = body_font.render(f"Time: {selected_time//60}m    Inc: {selected_increment}s", True, values.LANDING_SUBTITLE_COLOR)
            screen.blit(summary, (40, window_h - 128))

        pygame.display.flip()
        clock.tick(30)
