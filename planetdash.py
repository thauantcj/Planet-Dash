import pgzrun
from pgzero.actor import Actor
from pgzero.builtins import Rect, keyboard

# --- CONFIGURAÇÕES E ESTADO GLOBAL ---
WIDTH = 800
HEIGHT = 600
GRAVITY = 1
CAMERA_X = 0

GAME_STATE = "menu"  # Estados: "menu", "playing", "victory"
SOUND_ON = True

# --- CONSTANTES DO MAPA ---
WIDTH_BLOCK = 64
MAP_LENGTH = 80
PIXEL_LENGTH_MAP = WIDTH_BLOCK * MAP_LENGTH

# --- DEFINIÇÃO DOS BOTÕES ---
def make_button(y_offset):
    """Cria um retângulo de botão com um deslocamento Y."""
    x_pos = WIDTH / 2 - 125
    y_pos = HEIGHT / 2 + y_offset
    return Rect(x_pos, y_pos, 250, 50)

# --- BOTÕES DO MENU PRINCIPAL ---
start_button = make_button(-25)
sound_button = make_button(45)
exit_button = make_button(115)

# --- BOTÕES DA TELA DE VITÓRIA ---
restart_button = make_button(-25)
menu_button = make_button(45)

class GameObject:
    """Classe base para todos os objetos do mundo."""
    def __init__(self, image, center):
        self.sprite = Actor(image, center=center)
        self.position_x = self.sprite.x
        self.hitbox = self.sprite._rect.copy()
        self.is_active = True

    def update(self, delta_time, camera_x):
        self.sprite.x = self.position_x - camera_x
        self.hitbox.center = self.sprite.center

    def draw(self):
        if self.is_active:
            self.sprite.draw()

class Hero:
    """Classe que controla o personagem do jogo."""
    def __init__(self, position):
        self.sprite = Actor("herostand_0", position)
        self.frame = 0
        self.timer = 0
        self.interval = 10
        self.step_timer = 0
        self.speed = 5
        self.jump_force = -23
        self.velocity_y = 0
        self.on_ground = False
        self.direction = "stand"
        self.state = "stand"

    def reset(self):
        """Onde o personagem irá renascer caso colida com inimigo"""
        self.sprite_position = (WIDTH // 5, 400)
        self.velocity_y = 0

    def update(self, platforms, enemies):
        global CAMERA_X, GAME_STATE
        keys = keyboard
        moving = keys.right or keys.left

        #Lógica de Movimento
        if keys.right:
            CAMERA_X += self.speed
            self.direction = "right"

        elif keys.left:
            CAMERA_X -= self.speed
            self.direction = "left"

        if keys.up and self.on_ground:
            self.velocity_y = self.jump_force
            self.on_ground = False
            if SOUND_ON:
                sounds.sfx_jump.play() 

        #Ativar/Desativar som quando andar
        if moving and self.on_ground and SOUND_ON:
            self.step_timer += 1
            if self.step_timer >= 15:
                sounds.sfx_walk.play()
                self.step_timer = 0
        else:
            self.step_timer = 15 

        #Física e Limites da Camera
        CAMERA_X = max(0, min(CAMERA_X,
                      PIXEL_LENGTH_MAP - WIDTH))
        self.sprite.y += self.velocity_y
        self.velocity_y += GRAVITY

        #Colisão com Plataformas
        self.on_ground = False
        feet_hitbox = Rect(self.sprite.x - 10, 
                           self.sprite.bottom, 5, 5)
        
        for platform_collide in platforms:
            rect = getattr(platform_collide, 'hitbox', 
                           platform_collide.sprite._rect)
            if self.velocity_y >= 0 and feet_hitbox.colliderect(rect):
                self.sprite.bottom = rect.top
                self.velocity_y = 0
                self.on_ground = True
        
        # Colisão com inimigos
        for enemy in enemies:
            if enemy.is_active and self.sprite.colliderect(enemy.hitbox):
                reset_game()
                return
        
        #lógica para ativar a tela de vitória
        for sign in exit_sign:
            if self.sprite.colliderect(sign.sprite):
                GAME_STATE = "victory"
                music.stop()
                if SOUND_ON:
                    sounds.sfx_select.play()
                return 

        # Lógica de animação
        if not self.on_ground:
            self.state = "jump"
        elif moving:
            self.state = "walk"
        else:
            self.state = "stand"
            self.direction = "stand"
        
        self.timer += 1
        if self.timer >= self.interval:
            self.frame = (self.frame + 1) % 2
            self.timer = 0

            if self.state == "jump" and self.direction in ["left","right"]:
                self.sprite.image = f"herojump_{self.direction}"
            else:
                self.sprite.image = f"hero{self.direction}_{self.frame}"

    def draw(self):
        self.sprite.draw()

class Platform(GameObject):
    """Plataforma estática do cenário,podendo ter hitbox personalizada."""
    
    def __init__(self, image, 
                center, hitbox_size=None):
        super().__init__(image, center)
        if hitbox_size:
            self.hitbox = Rect(0,0,hitbox_size[0],hitbox_size[1])

class SpinningSpike(GameObject):
    """Ojeto de espinho giratório com colisão."""

    def __init__(self,center):
        super().__init__("espinho",center)
        self.hitbox = Rect(0, 0, 20, 20)

    def update(self,delta_time,camera_x):
        super().update(delta_time,camera_x)
        self.sprite.angle += 180 * delta_time
        self.hitbox.center = self.sprite.center

class SleepySlime(GameObject):
    """Um inimigo imóvel, com animação"""

    def __init__(self,frames,center,fps=4):
        super().__init__(frames[0],center)
        self.frames = frames
        self.fps = fps
        self.frame_idx = 0.0
        self.hitbox = Rect(0,0,20,20)

    def update(self,delta_time,camera_x):
        """estabilidade com a camera e controle de animação"""
        super().update(delta_time,camera_x)
        self.frame_idx = (self.frame_idx + self.fps
                         * delta_time) % len(self.frames)
        self.sprite.image = self.frames[int(self.frame_idx)]

class AnimatedObject(GameObject):
    """classe para objetos que tem animação"""
    
    def __init__(self, frames, center, fps=4):
        super().__init__(frames[0], center)
        self.frames = frames
        self.fps = fps
        self.frame_idx = 0.0

    def update(self, delta_time, camera_x):
        """atualiza animação e posição do sprite."""
        super().update(delta_time, camera_x)
        self.frame_idx = (self.frame_idx + self.fps * delta_time) % len(self.frames)
        self.sprite.image = self.frames[int(self.frame_idx)]

class PatrollingEnemy(GameObject):
    """Um inimigo genérico que patrulha uma área e opcionalmente pula."""

    def __init__(self, base_name, center, patrol_range, can_jump=False):
        """Inicia o inimigo e a patrulha, onde ele fica posicionado e o alcance da patrulha"""
        
        super().__init__(f"{base_name}left_0", center)
        self.base_name = base_name
        self.patrol_start, self.patrol_end = patrol_range
        self.can_jump = can_jump
        
        self.is_active = False
        self.direction = "left"
        self.speed = 2
        self.is_jumping = False
        self.velocity_y = 0
        self.gravity = 1
        self.jump_cooldown = 0
        self.frame = 0
        self.timer = 0
        self.interval = 10
        self.hitbox = Rect(0, 0, 30, 30)

    def update(self, delta_time, camera_x):
        """Ativar o inimigo quando entrar na area de visão do jogador"""
        if not self.is_active and camera_x >= self.position_x - WIDTH:
            self.is_active = True
        if not self.is_active:
            return
            
        super().update(delta_time, camera_x)

        #Lógica do pulo(se ativado)
        if self.can_jump and not self.is_jumping and self.jump_cooldown <= 0:
            self.velocity_y = -15
            self.is_jumping = True
            self.jump_cooldown = 90
            if SOUND_ON:
                sounds.sfx_frog_jump.play()

        #Física do Pulo
        if self.is_jumping:
            self.sprite.y += self.velocity_y
            self.velocity_y += self.gravity
            if self.sprite.y >= 460:
                self.sprite.y = 460
                self.velocity_y = 0
                self.is_jumping = False
        
        """Lógica utilizada para patrulhar a área
        esquerda/direita,"""
        self.position_x += self.speed if self.direction == "right" else -self.speed
        """se posição do objeto for igual ou menor o inicio da patrulha:
        ir para direita,se posição igualou maior do fim da patrulha:
        ir para esquerda"""
        if self.position_x <= self.patrol_start:
            self.direction = "right"
        elif self.position_x >= self.patrol_end:
            self.direction = "left"

        """lógica da animação do pulo,se pular usa o paramêtro abaixo"""
        if self.is_jumping:
            self.sprite.image = f"{self.base_name}jump_{self.direction}"
        else:
            self.timer += 1
            if self.timer >= self.interval:
                self.frame = (self.frame + 1) % 2
                self.timer = 0
            self.sprite.image = f"{self.base_name}{self.direction}_{self.frame}"
        
        self.jump_cooldown = max(0, self.jump_cooldown - 1)

    def reset(self):
        self.is_active = False
        self.is_jumping = False
        self.velocity_y = 0
        self.jump_cooldown = 0
        self.sprite.y = 460

# Geração do Mundo

platforms, water_blocks, enemies,exit_sign, all_objects = [], [], [], [],[]
hero = Hero((WIDTH // 5, 400))

def create_world():
    """Limpa as listas e cria todos os objetos do mundo do zero."""
    global platforms, water_blocks, all_objects, enemies, exit_sign

    # Dados das plataformas/obstáculos
    platform_data = [
        ("obstaculo_1", 600, 400, 128, 50), ("obstaculo_0", 800, 350, 90, 40),
        ("obstaculo_1", 2650, 420, 128, 50), ("obstaculo_0", 2750, 310, 90, 40),
        ("obstaculo_1", 2850, 310, 128, 50), ("obstaculo_0", 2950, 310, 90, 40),
        ("sign_begin", 80, 460, 64, 64)
    ]
    # Dados dos inimigos
    spike_pos = [(920, 380), (2000, 300), (2850, 420), (2950, 400), (3050, 370)]
    slime_pos = [(1214, 465), (2240, 465),(2850,250)]
    frog_pos = [
        ((1800, 460), (1700, 1900)), ((2400, 460), (2300, 2500)),
        ((3150, 460), (3100, 3800)), ((3400, 460), (3350, 4000))
    ]
    purple_pos = [((600,460),(500,900)),((2850,460),(2750,2950)),
                        ((1400,460),(1300,1500)),((3200,460),(3100,3300))
    ]

    # Criação dos objetos usando os dados
    platforms = ([Platform("floor", (i * WIDTH_BLOCK, 520)) 
                for i in range(MAP_LENGTH)] + 
                [Platform(img, (x, y), (w, h)) 
                for img, x, y, w, h in platform_data]
    )
    water_blocks = [GameObject("water", (i * WIDTH_BLOCK, 584)) 
                   for i in range(MAP_LENGTH)]

    exit_sign = [GameObject("sign_exit", center=(4225, 460))]
              #comando onde cria os objetos de acordo com a posição(c)
              #alcance de patrulha(r) e se pode pular"""
    enemies =([SpinningSpike(c) for c in spike_pos] + 
              [SleepySlime(['slime_0', 'slime_1'], c)
              for c in slime_pos] + 
              [PatrollingEnemy(base_name="frog", center=c,
              patrol_range=r, can_jump=True) for c, r in frog_pos] + 
              [PatrollingEnemy(base_name="purple", center=c,
              patrol_range=r, can_jump=False) for c, r in purple_pos]
    )

    decorations = [GameObject("bush", (i * WIDTH_BLOCK, 460))
                  for i in range(4, MAP_LENGTH, 4)] + \
                  [GameObject("cactus", (i * WIDTH_BLOCK, 465))
                  for i in range(15, MAP_LENGTH, 15)] + \
                  [AnimatedObject(['hill_0', 'hill_1'], (i * WIDTH_BLOCK, 426))
                  for i in range(3, MAP_LENGTH, 20)]

    all_objects = platforms + water_blocks + enemies + decorations + exit_sign

# Funções de controle do jogo

def start_game():
    """Prepara um novo jogo, criando o mundo e resetando o jogador."""
    global CAMERA_X
    CAMERA_X = 0
    create_world()
    hero.reset()
    if SOUND_ON:
        music.play("game_music.mp3")
        music.set_volume(0.4)


def reset_game():
    """Reseta a posição do herói durante o jogo."""
    global CAMERA_X
    CAMERA_X = 0
    hero.reset()
    sounds.sfx_hurt.play()
    for enemy in enemies:
        if isinstance(enemy, (PatrollingEnemy)):
            enemy.reset()

# Funções principais da lógica

def update_game(delta_time):
    """Atualiza a lógica do jogo principal."""
    hero.update(platforms, enemies)
    for obj in all_objects:
        obj.update(delta_time, CAMERA_X)


def draw_game():
    """Desenha a tela do jogo principal."""
    offset = -(CAMERA_X * 0.5 % WIDTH)
    screen.blit("background_0", (offset, 0))
    screen.blit("background_0", (offset + WIDTH, 0))
    for obj in all_objects:
        obj.draw()
    for enemy in enemies:
        enemy.draw()
    hero.draw()


# --- FUNÇÕES DE UI (MENU E VITÓRIA) ---

def draw_button(rect, text, background_color, text_color="white"):
    """Função auxiliar para desenhar um botão."""
    screen.draw.filled_rect(rect, background_color)
    screen.draw.text(text, center=rect.center, fontsize=35, color=text_color)


def draw_menu():
    """Desenha a tela do menu principal."""
    screen.fill((250, 128, 114))
    screen.draw.text("Utilize as teclas do teclado para se mover",center=(WIDTH/2,550),fontsize=30,color="black")
    screen.draw.text("Planet Dash", center=(WIDTH / 2, 200), fontsize=80, color="brown")
    draw_button(start_button, "Iniciar Jogo", (139, 69, 19))
    draw_button(sound_button, f"Som: {'LIGADO' if SOUND_ON else 'DESLIGADO'}", (139, 69, 19))
    draw_button(exit_button, "Sair", (139, 69, 19))


def draw_victory():
    """Desenha a tela de vitória."""
    screen.fill((250, 128, 114))
    screen.draw.text("Você Venceu!", center=(WIDTH / 2, 150), fontsize=60, color="white")
    draw_button(restart_button, "Reiniciar Fase", "brown")
    draw_button(menu_button, "Voltar ao Menu", "red")

# gerenciador de estados

def update(delta_time):
    """Chama a função de update apropriada baseada no estado do jogo."""
    if GAME_STATE == "playing":
        update_game(delta_time)

def draw():
    """Chama a função de desenho apropriada baseada no estado do jogo."""
    screen.clear()
    if GAME_STATE == "playing":
        draw_game()
    elif GAME_STATE == "menu":
        draw_menu()
    elif GAME_STATE == "victory":
        draw_victory()


def on_mouse_down(pos):
    """Lida com cliques do mouse para os diferentes estados do jogo."""
    global GAME_STATE, SOUND_ON

    # Lógica de clique para o menu
    if GAME_STATE == "menu":
        if start_button.collidepoint(pos):
            music.stop()
            if SOUND_ON: sounds.sfx_select.play()
            GAME_STATE = "playing"
            start_game()
        elif sound_button.collidepoint(pos):
            if SOUND_ON: sounds.sfx_select.play()
            SOUND_ON = not SOUND_ON
            if not SOUND_ON:
                music.stop()
            else:
                music.play("menu_music.mp3")
        elif exit_button.collidepoint(pos):
            if SOUND_ON: sounds.sfx_select.play()
            quit()
    
    # Lógica de clique para a tela de vitória
    elif GAME_STATE == "victory":
        if restart_button.collidepoint(pos):
            if SOUND_ON: sounds.sfx_select.play()
            GAME_STATE = "playing"
            start_game()
        elif menu_button.collidepoint(pos):
            if SOUND_ON: sounds.sfx_select.play()
            GAME_STATE = "menu"
            music.play("menu_music.mp3")


# --- INICIALIZAÇÃO DO JOGO ---
music.play("menu_music.mp3")
pgzrun.go()