import json
import posixpath
import math

from OpenGL.GL import *

from pathlib import Path
from PIL import Image

flags = {'enable_text_rendering': True, "show_debug_screen": True, "enable_joystick": True}

Fonts = {}

class Joystick:
    """Virtual joystick for mobile players"""
    def __init__(self, x, y, base_radius=60, stick_radius=20):
        self.base_x = x  # Base position X (usually bottom-left)
        self.base_y = y  # Base position Y
        self.base_radius = base_radius  # Outer circle radius
        self.stick_radius = stick_radius  # Inner stick radius
        
        self.stick_x = x  # Current stick X position
        self.stick_y = y  # Current stick Y position
        
        self.is_active = False  # Whether joystick is being touched
        self.touch_id = None  # Touch identifier for multi-touch support
        
    def update(self, mouse_x, mouse_y, is_pressed):
        """Update joystick state based on mouse/touch input"""
        # Check if click is within the base radius
        dist_to_base = math.sqrt((mouse_x - self.base_x)**2 + (mouse_y - self.base_y)**2)
        
        if is_pressed and dist_to_base <= self.base_radius:
            self.is_active = True
            # Clamp stick position to within base radius
            angle = math.atan2(mouse_y - self.base_y, mouse_x - self.base_x)
            distance = min(dist_to_base, self.base_radius - self.stick_radius)
            
            self.stick_x = self.base_x + math.cos(angle) * distance
            self.stick_y = self.base_y + math.sin(angle) * distance
        else:
            self.is_active = False
            # Reset stick to center when not pressed
            self.stick_x = self.base_x
            self.stick_y = self.base_y
    
    def get_direction(self):
        """Get normalized direction vector from joystick [-1, 1] for x and y"""
        dx = self.stick_x - self.base_x
        dy = self.stick_y - self.base_y
        
        # Normalize to [-1, 1] range
        if self.base_radius > 0:
            dx = dx / self.base_radius
            dy = dy / self.base_radius
        
        return dx, dy
    
    def draw(self, color_base=(0.3, 0.3, 0.3, 0.7), color_stick=(0.7, 0.7, 0.7, 0.9)):
        """Draw the joystick on screen"""
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        # Draw base circle
        glColor4f(*color_base)
        self._draw_circle(self.base_x, self.base_y, self.base_radius)
        
        # Draw stick circle
        glColor4f(*color_stick)
        self._draw_circle(self.stick_x, self.stick_y, self.stick_radius)
        
        glEnable(GL_TEXTURE_2D)
    
    def _draw_circle(self, x, y, radius, segments=20):
        """Draw a filled circle"""
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(x, y)
        for i in range(segments + 1):
            angle = 2.0 * math.pi * i / segments
            glVertex2f(x + radius * math.cos(angle), y + radius * math.sin(angle))
        glEnd()

# Global joystick instance - positioned at bottom-left for mobile
joystick = Joystick(x=100, y=700, base_radius=60, stick_radius=20)

def load_fonts():
    for file in Path(Path(__file__).parent / "assets/fonts").iterdir():
        if file.is_file() and file.suffix == ".json":
            Fonts[file.stem] = BitmapFont(file)

def load_texture(texture_path: Path):
    if texture_path.is_file() and (texture_path.suffix == ".png" or texture_path.suffix == ".jpg"):
        assets_path = Path(__file__).parent / "assets"
        img = Image.open(assets_path / texture_path)
        img_data = img.convert('RGBA').tobytes()

        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.width, img.height, 0,
                     GL_RGBA, GL_UNSIGNED_BYTE, img_data)

        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

        return texture, img.width, img.height
    return None

class BitmapFont:
    def __init__(self, json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.cell_size = data["cellSize"]
        self.line_height = data["lineHeight"]
        self.chars = data["chars"]

        self.texture = self._load_texture(Path(json_path).parent / data["texture"])
        self.tex_w = self.tex_width
        self.tex_h = self.tex_height

    def _load_texture(self, path):
        img = Image.open(path).convert("RGBA")
        self.tex_width, self.tex_height = img.size

        datas = img.getdata()
        new_data = []
        for item in datas:
            r, g, b, a = item
            if r == 0 and g == 0 and b == 0 and a == 255:
                new_data.append((0, 0, 0, 0))
            else:
                new_data.append(item)

        img.putdata(new_data)
        img_data = img.tobytes()
        self.tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.tex_id)

        glTexImage2D(
            GL_TEXTURE_2D, 0, GL_RGBA,
            self.tex_width, self.tex_height,
            0, GL_RGBA, GL_UNSIGNED_BYTE, img_data
        )

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        return self.tex_id

def begin_ortho(width, height):
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, width, height, 0, -1, 1)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

def end_ortho():
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()

    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()

def draw_text_2d(x, y, text, font, scale=1.0):
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, Fonts[font].tex_id)

    cursor_x = x
    cursor_y = y

    if flags['enable_text_rendering']:
        for ch in text:
            if ch == "\n":
                cursor_x = x
                cursor_y += Fonts[font].line_height * scale
                continue

            if ch not in Fonts[font].chars:
                cursor_x += Fonts[font].cell_size * scale
                continue

            g = Fonts[font].chars[ch]

            u0 = g["x"] / Fonts[font].tex_w
            v0 = g["y"] / Fonts[font].tex_h
            u1 = (g["x"] + g["w"]) / Fonts[font].tex_w
            v1 = (g["y"] + g["h"]) / Fonts[font].tex_h

            yoff = g.get("yoffset", 0) * scale
            glBegin(GL_QUADS)
            glTexCoord2f(u0, v0); glVertex2f(cursor_x, cursor_y + yoff)
            glTexCoord2f(u1, v0); glVertex2f(cursor_x + g["w"], cursor_y + yoff)
            glTexCoord2f(u1, v1); glVertex2f(cursor_x + g["w"], cursor_y + yoff + g["h"])
            glTexCoord2f(u0, v1); glVertex2f(cursor_x, cursor_y + yoff + g["h"])
            glEnd()

            cursor_x += g["advance"] * scale

def draw_crosshair(texture, tw, th, screen_width, screen_height):
    glEnable(GL_TEXTURE_2D)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    glBindTexture(GL_TEXTURE_2D, texture)

    x = screen_width / 2.0 - tw / 2.0
    y = screen_height / 2.0 - th / 2.0

    glBegin(GL_QUADS)
    glTexCoord2f(0, 0); glVertex2f(x, y)
    glTexCoord2f(1, 0); glVertex2f(x+tw, y)
    glTexCoord2f(1, 1); glVertex2f(x+tw, y+th)
    glTexCoord2f(0, 1); glVertex2f(x, y+th)
    glEnd()

    glDisable(GL_TEXTURE_2D)