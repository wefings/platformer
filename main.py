import os
import math
import glob

import pygame
from os.path import join
import json

pygame.init()
pygame.display.set_caption("Platformer")

FPS = 60

resourcePath = "."
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w,info.current_h
window = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
offset_x = 0
objects = []

_sound_library = {}

def playSound(name, loops = 0):
  global _sound_library
  sound = _sound_library.get(name)
  if sound == None:
    sound = pygame.mixer.Sound(join(resourcePath, "sounds", name))
    _sound_library[name] = sound
  sound.play(loops)

# path, file mask, number of sprites, flip/rotate, new name

def load_sprite_sheets(path, width=0, height=0, direction=False):
    images = [f for f in glob.glob(join(resourcePath, path))]  #if isfile(join(path, f))
    all_sprites = {}

    for image in images:
        #print("Loading ", image)
        sprite_sheet = pygame.image.load(image).convert_alpha()
        if(height == 0): height = sprite_sheet.get_height()
        if(width == 0): width = sprite_sheet.get_width()
        sprites = []
        for i in range(sprite_sheet.get_width() // width):
            surface = pygame.Surface((width, height), pygame.SRCALPHA, 32)
            rect = pygame.Rect(i * width, 0, width, height)
            surface.blit(sprite_sheet, (0, 0), rect)
            sprites.append(pygame.transform.scale2x(surface))

        name = os.path.basename(image).replace(".png", "")
        if direction:
            all_sprites[name + "_right"] = sprites
            all_sprites[name + "_left"] = [pygame.transform.flip(sprite, True, False) for sprite in sprites]
        else:
            all_sprites[name] = sprites

    return all_sprites


class Object(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, name=None):
        pygame.sprite.Sprite.__init__(self)
        self.rect = pygame.Rect(x, y, width, height)
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        self.width = width
        self.height = height
        self.name = name

    def draw(self, win, offset_x):
        pygame.draw.rect(win, (255, 255, 255), pygame.Rect(self.rect.x - offset_x, self.rect.y, self.rect.width, self.rect.height), 1)
        if hasattr(self, "lastobj"): pygame.draw.line(window, (255, 255, 255), (self.rect.center[0] - offset_x, self.rect.center[1]), (self.lastobj.rect.center[0] - offset_x, self.lastobj.rect.center[1]))
        win.blit(self.image, (self.rect.x - offset_x, self.rect.y))

    def loop(self, fps):
        pass

    def encode(self):
        return dict(name=self.name, x=self.rect.x, y=self.rect.y)

    def collideTop(self, obj):
        return True

    def collideBottom(self, obj):
        return True

    def collideLeft(self, obj):
        return True

    def collideRight(self, obj):
        return True

    def move(self, dx, dy):
        global objects, window
        prevx = self.rect.x
        self.rect.x += dx
        self.rect.y += dy
        for obj in objects:
            if pygame.sprite.collide_mask(self, obj):
                self.lastobj = obj

                cx = self.rect.center[0] - obj.rect.center[0]
                cy = self.rect.center[1] - obj.rect.center[1]

                if abs(cx) > abs(cy):
                    if cx < 0:
                        self.collideRight(obj)
                        obj.collideLeft(self)
                    else:
                        self.collideLeft(obj)
                        obj.collideRight(self)

                    for i in range(50):
                        if cx < 0:
                            self.rect.x -= 1  #change to obj.move(1, 0) to move objects
                        else:
                            self.rect.x += 1  #change to obj.move(-1, 0)
                        if not pygame.sprite.collide_mask(self, obj): break
                else:
                    if cy < 0 and dy >= 0:
                        self.collideBottom(obj)
                        obj.collideTop(self)
                    elif cy > 0:
                        self.collideTop(obj)
                        obj.collideBottom(self)
        return True

class ObjectEncoder(json.JSONEncoder):
    def default(self, o):
        if hasattr(o, "encode"):
            return o.encode()
        #else:
         #   return super().default(o)

class Player(Object):
    GRAVITY = 1.5
    JUMPVELOCITY = GRAVITY * 8
    VELOCITY = 5
    ANIMATION_DELAY = 3
    SPRITES = load_sprite_sheets("assets/MainCharacters/VirtualGuy/*.png", 32, 0, True)
    MAXHEALTH = 5

    def __init__(self, x, y, width, height):
        Object.__init__(self, x, y,  width, height, "player")
        self.rect = pygame.Rect(x, y, width, height)
        self.mask = None
        self.restart()

    def restart(self):
        global offset_x
        offset_x = 0
        self.rect.x = 100
        self.rect.y = 100
        self.fall_count = 0
        self.hit = False
        self.hit_count = 0
        self.x_vel = 0
        self.y_vel = 0
        self.health = self.MAXHEALTH
        self.jump_count = 0
        self.animation_count = 0
        self.direction = "right"

    def getHealth(self):
        return self.health

    def addHealth(self, amount):
        self.health += amount
        playSound("apple.mp3")
        if self.health > self.MAXHEALTH: self.health = self.MAXHEALTH

    def make_hit(self):
        if not self.hit:
            self.health -= 1
        self.hit = True

    def jump(self):
        if self.jump_count < 2:
            playSound("swing.mp3")
            self.y_vel = -self.JUMPVELOCITY
            self.animation_count = 0
            self.jump_count += 1
            if self.jump_count == 1:
                self.fall_count = 0

    def move_left(self, vel):
        self.x_vel = -vel
        if self.direction != "left":
            self.direction = "left"
            self.animation_count = 0

    def move_right(self, vel):
        self.x_vel = vel
        if self.direction != "right":
            self.direction = "right"
            self.animation_count = 0

    def handleCollision(self, obj):
        global objects
        if obj.name == "saw": self.make_hit()
        if obj.name == "fruit":
            objects.remove(obj)
            self.addHealth(1)
            return True
        return False

    def collideTop(self, obj):
        if self.handleCollision(obj): return True
        self.count = 0
        self.y_vel *= -1
        self.rect.top = obj.rect.bottom

    def collideBottom(self, obj):
        if self.handleCollision(obj): return True
        if obj.name == "fire": self.make_hit()
        self.rect.bottom = obj.rect.top
        self.fall_count = 0
        self.y_vel = 0
        self.jump_count = 0
        self.rect.bottom = obj.rect.top

    def collideLeft(self, obj):
        if self.handleCollision(obj): return True
        self.x_vel = 0
        #self.rect.left = obj.rect.right

    def collideRight(self, obj):
        if self.handleCollision(obj): return True
        self.x_vel = 0
        #self.rect.right = obj.rect.left

    def loop(self, fps):
        if self.hit:
            self.hit_count += 1
        if self.hit_count > 30:
            self.hit = False
            self.hit_count = 0

        self.fall_count += 1

        # update sprite
        sprite_sheet = "idle"
        if self.hit:
            sprite_sheet = "hit"
        elif self.y_vel < 0:
            if self.jump_count == 1:
                sprite_sheet = "jump"
            elif self.jump_count == 2:
                sprite_sheet = "double_jump"
        elif self.y_vel > self.GRAVITY * 2:
            sprite_sheet = "fall"
        elif self.x_vel != 0:
            sprite_sheet = "run"

        sprite_sheet_name = sprite_sheet + "_" + self.direction
        sprites = self.SPRITES[sprite_sheet_name]
        sprite_index = (self.animation_count // self.ANIMATION_DELAY) % len(sprites)
        self.image = sprites[sprite_index]
        self.animation_count += 1

        self.y_vel += min(1, (self.fall_count / fps) * self.GRAVITY)
        self.update()
        self.move(self.x_vel, self.y_vel)

    def update(self):
        self.rect = self.image.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.image)

class Block(Object):
    sx = 96
    sy = 96
    SPRITES = load_sprite_sheets("assets/Terrain/Terrain.png", 48, 48)
    def __init__(self, x, y):
        Object.__init__(self, x, y, self.sx, self.sy, "block")
        self.image = self.SPRITES["Terrain"][2]
        self.mask = pygame.mask.from_surface(self.image)

class Trap(Object):
    ANIMATION_DELAY = 5
    def __init__(self, x, y, sx, sy, state, name):
        Object.__init__(self, x, y, sx, sy, name)
        self.animation_name = state
        self.animation_count = 0
        self.image = self.sprites[self.animation_name][0]
        self.mask = pygame.mask.from_surface(self.image)

    def collideTop(self, obj):
        if(self.animation_name == "on"):
            if("hit" in self.sprites): self.animation_name = "hit"

    def loop(self, fps):
        sprites = self.sprites[self.animation_name]
        sprite_index = (self.animation_count // self.ANIMATION_DELAY) % len(sprites)
        self.image = sprites[sprite_index]
        self.animation_count += 1

        self.rect = self.image.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.image)

        if self.animation_count // self.ANIMATION_DELAY > len(sprites):
            self.animation_count = 0
            if(self.animation_name == "hit"): self.animation_name = "on"

class Fire(Trap):
    sx, sy = 32, 64
    sprites = load_sprite_sheets("assets/Traps/Fire/*.png", sx // 2, sy // 2)
    def __init__(self, x, y):
        Trap.__init__(self, x, y, self.sx, self.sy, "on", "fire")

class Fruit(Trap):
    sx, sy = 64, 64
    sprites = load_sprite_sheets("assets/Items/Fruits/*.png", sx // 2, sy // 2)
    def __init__(self, x, y, name):
        Trap.__init__(self, x, y, self.sx, self.sy, name, "fruit")
        self.fruitName = name

    def encode(self):
        res = Trap.encode(self)
        res['state'] = self.fruitName
        return res

class Saw(Trap):
    sx, sy = 38 * 2, 38 * 2
    sprites = load_sprite_sheets("assets/Traps/Saw/on.png", sx // 2, sy // 2)
    chain = load_sprite_sheets("assets/Traps/Saw/Chain.png")
    def __init__(self, x, y, path=[(0, 96 * 3), (0, 0)]):
        self.origx = x
        self.origy = y
        #self.path = [(200,200),(400,0),(500,100), (0,0)]
        #self.path = [(96 * 2,0), (96 * 2,96 * 2), (0,96 * 2), (0,0)]
        self.path = path
        self.distance = 0
        Trap.__init__(self, x, y, self.sx, self.sy, "on", "saw")

    def getPathPos(self, distance):
        for i in range(0, len(self.path)):
            dx = self.path[i][0] - self.path[i - 1][0]
            dy = self.path[i][1] - self.path[i - 1][1]
            r = math.sqrt(dx * dx + dy * dy)
            if(distance < r): return (self.path[i - 1][0] + dx * distance / r, self.path[i - 1][1] + dy * distance / r)
            distance -= r
        return (0, 0)

    def loop(self, fps):
        self.distance += 5
        pos = self.getPathPos(self.distance)
        if(pos[0] == 0 and pos[1] == 0): self.distance = 0
        self.rect.x = self.origx + pos[0]
        self.rect.y = self.origy + pos[1]
        Trap.loop(self, fps)

    def draw(self, win, offset_x):
        distance = 0

        while(True):
            distance += 30
            pos = self.getPathPos(distance)
            chain = self.chain["Chain"][0]
            win.blit(chain, (self.origx + pos[0] - offset_x + (self.sx - chain.get_width())// 2, self.origy + pos[1] + (self.sy - chain.get_height()) // 2))
            if (pos[0] == 0 and pos[1] == 0): break

        Trap.draw(self, win, offset_x)

    def encode(self):
        return dict(name="saw", x=self.origx, y=self.origy, path=self.path)


def handle_player_move(player, objects):
    global offset_x

    keys = pygame.key.get_pressed()

    player.x_vel = 0
    if keys[pygame.K_a]: player.move_left(Player.VELOCITY)
    if keys[pygame.K_d]: player.move_right(Player.VELOCITY)

    player.loop(FPS)

    scroll_area_width = WIDTH / 5

    if (player.rect.right - offset_x > WIDTH - scroll_area_width): offset_x = player.rect.right - (WIDTH - scroll_area_width)
    if (player.rect.left - offset_x < scroll_area_width): offset_x = player.rect.left - scroll_area_width

    if (player.rect.y > HEIGHT or player.getHealth() == 0):
        loadMap(objects)
        player.restart()

currentObject = -1
def getCurrentObject(pos, offset_x):
    if(currentObject == -1): return None
    if (currentObject == 0): return Block(((pos[0] + offset_x) // Block.sx) * Block.sx, (pos[1] // Block.sy) * Block.sy)
    if (currentObject == 1): return Fire(((pos[0] + offset_x) // Block.sx) * Block.sx + (Block.sx - Fire.sx) // 2, (pos[1] // Block.sy) * Block.sy + (Block.sy - Fire.sy))
    if (currentObject == 2): return Saw(((pos[0] + offset_x) // Block.sx) * Block.sx + (Block.sx - Saw.sx) // 2, (pos[1] // Block.sy) * Block.sy + (Block.sy - Saw.sy) // 2)

    fruits = ["Apple", "Bananas", "Cherries", "Kiwi", "Melon", "Orange", "Pineapple", "Strawberry"]
    if (currentObject >= 3): return Fruit(((pos[0] + offset_x) // Block.sx) * Block.sx + (Block.sx - Fruit.sx) // 2,
                                         (pos[1] // Block.sy) * Block.sy + (Block.sy - Fruit.sy), fruits[currentObject - 3])


def get_background(name):
    image = pygame.image.load(join(resourcePath, "assets", "Background", name)).convert()
    _, _, width, height = image.get_rect()
    tiles = []

    for i in range(WIDTH // width + 1):
        for j in range(HEIGHT // height + 1):
            pos = (i * width, j * height)
            tiles.append(pos)

    return tiles, image

def drawInfo(window, player, fps):
    if not hasattr(__name__, "heart"):
        drawInfo.heart = pygame.transform.scale2x(pygame.image.load("assets/heart.png").convert_alpha())

    for i in range(player.getHealth()): window.blit(drawInfo.heart, (10 + i * 35, 10))

    myFont = pygame.font.SysFont("showcardgothic", 50)
    text = myFont.render(str(int(fps)) + " FPS", True, (0, 0, 255))
    window.blit(text, (800, 10))

def draw(window, background, bg_image, player, objects, offset_x, fps):
    for tile in background: window.blit(bg_image, tile)
    #window.fill((255,255,255))

    for obj in objects:
        obj.draw(window, offset_x)

    drawInfo(window, player, fps)

    if currentObject == -1: player.draw(window, offset_x)

    curobj = getCurrentObject(pygame.mouse.get_pos(), offset_x)
    if curobj: curobj.draw(window, offset_x)

    pygame.display.update()

    # x, y  = 0, 0
    # for f in pygame.font.get_fonts():
    #     try:
    #         myFont = pygame.font.SysFont(f, 20)
    #         text = myFont.render(f, 1, (0, 0, 0))
    #         window.blit(text, (x, y))
    #         y += 20
    #         if(y > HEIGHT):
    #             y = 0
    #             x += 300
    #     except:
    #         print("ERROR")

    # pygame.display.update()

def saveMap(objects):
    with open(join(resourcePath, 'game.map'), 'w') as f: json.dump(objects, f, cls=ObjectEncoder, indent=4)

def loadMap(objects):
    try:
        with open(join(resourcePath, 'game.map')) as f:
            objects.clear()
            for i in json.load(f):
                if (i["name"] == "block"): objects.append(Block(i["x"], i["y"]))
                if (i["name"] == "saw"): objects.append(Saw(i["x"], i["y"], i["path"]))
                if (i["name"] == "fire"): objects.append(Fire(i["x"], i["y"]))
                if (i["name"] == "fruit"): objects.append(Fruit(i["x"], i["y"], i["state"]))
    except Exception as e: print(e)

def handleEvents(objects, player):
    global currentObject, offset_x

    if currentObject != -1:
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a]: offset_x -= 20
        if keys[pygame.K_d]: offset_x += 20

    for event in pygame.event.get():
        if event.type == pygame.QUIT: return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: return False
            if event.key == pygame.K_w: player.jump()
       #     if event.key == pygame.K_s: saveMap(objects)
            if event.key == pygame.K_r:
                loadMap(objects)
                player.restart()
            if event.key == pygame.K_e:
                if currentObject == -1:
                    currentObject = 0
                    loadMap(objects)
                else:
                    currentObject = -1
                    saveMap(objects)
                    player.restart()

        if event.type == pygame.MOUSEBUTTONDOWN and currentObject != -1:

            pressed = pygame.mouse.get_pressed(3)
            if (pressed[0]):
                pos = pygame.mouse.get_pos()
                bRemoved = False
                for obj in objects:
                    if obj.rect.collidepoint((pos[0] + offset_x, pos[1])):
                        objects.remove(obj)
                        bRemoved = True
                        break

                if (not bRemoved): objects.append(getCurrentObject(pos, offset_x))
            # objects.append(Fire(pos[0] + offset_x - Fire.sx, pos[1] - Fire.sy, "on"))
            if (pressed[2]): currentObject = (currentObject + 1) % 11
    return True



def main(window):
    global objects

    clock = pygame.time.Clock()
    background, bg_image = get_background("Blue.png")
    player = Player(100, 100, 64, 64)
    loadMap(objects)

    #playSound("music1.mp3")
    pygame.mixer.music.load(join(resourcePath, 'sounds/music1.mp3'))
    #pygame.mixer.music.play(-1)
    pygame.mixer.music.set_volume(0.1)

    while True:
        clock.tick(FPS)
        if not handleEvents(objects, player): break
        for obj in objects: obj.loop(FPS)
        if currentObject == -1:
            handle_player_move(player, objects)
        draw(window, background, bg_image, player, objects, offset_x, clock.get_fps())

    pygame.quit()
    quit()

if __name__ == "__main__":
    main(window)
