from wxpy3d import PointWindow
from OpenGL.GL import *
from rtmodel import mesh
from rtmodel import camera
from wxpy3d.opengl_state import opengl_state

if not 'window' in globals():
    window = PointWindow(size=(640,480))#, pos=(20,20))
    window.rotangles[0] = 20
    print """
    Demo Objrender:
        refresh()
        load_obj(): select a random object and load it
    """

def load_obj(name='gamecube'):
    global obj

    window.canvas.SetCurrent()
    obj = mesh.load(name)

    obj.RT = np.eye(4, dtype='f')
    obj.RT[:3,3] = -obj.vertices[:,:3].mean(0)

    window.lookat = obj.RT[:3,3] + obj.vertices[:,:3].mean(0)
    window.Refresh()


@window.eventx
def EVT_CHAR(evt):
    key = evt.GetKeyCode()
    if key == ord('f'):
        window.ShowFullScreen(not window.IsFullScreen())
    if key == ord(' '):
        pass


# Animation
if not 'is_animating' in globals():
    is_animating = False

def resume():
    global is_animating
    is_animating = True

def stop():
    global is_animating
    is_animating = False

anim_angle = 0.0
@window.eventx
def EVT_IDLE(evt):
    if is_animating:
        anim_angle += 0.03 
        window.Refresh()

# Render the mesh before drawing points
@window.event
def on_draw():

    camera = None
    proj = lambda mode: make_projection(camera, mode)

    class NoDraw: draw = lambda _: None

    def render(mode):
        glDrawBuffer(dict(left=GL_BACK_LEFT,
                          right=GL_BACK_RIGHT,
                          center=GL_BACK)[mode])

        glClearColor(0,0,0,0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_PROJECTION)
        glLoadMatrixf(proj(mode))
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        if 1:
            with opengl_state():
                stereo_image.draw(dict(left='left', right='right',
                                       center='right')[mode])
        with opengl_state(): draw_thing()
        
    if glGetInteger(GL_STEREO):
        render('left')
        render('right')
    else:
        render('center')


class SplitImage:
    def __init__(self, filename):
        self.filename = filename

    def __load__(self):
        import pygame
        filename = self.filename
        imgsurf = pygame.image.load(filename)
        imgstring = pygame.image.tostring(imgsurf, "RGBA", 1)
        width, height = imgsurf.get_size()
        texid = glGenTextures(1)
        glBindTexture(GL_TEXTURE_RECTANGLE, texid)
        glTexImage2D(GL_TEXTURE_RECTANGLE, 0, GL_RGBA, width, height, 0,
                     GL_RGBA, GL_UNSIGNED_BYTE, imgstring)
        self.texid = texid
        self.size = width, height

    def draw(self, mode):
        assert mode in ('left','right')

        if not 'texid' in dir(self):
            self.__load__()

        glBindTexture(GL_TEXTURE_RECTANGLE, self.texid)
        glEnable(GL_TEXTURE_RECTANGLE)

        w,h = self.size
        L = dict(left=0, right=w/2)[mode]
        glBegin(GL_QUADS)
        glTexCoord(L+0,  0); glVertex(-1,-1)
        glTexCoord(L+0,  h); glVertex(-1, 1)
        glTexCoord(L+w/2,h); glVertex( 1, 1)
        glTexCoord(L+w/2,0); glVertex( 1,-1)
        glEnd()

    def __del__(self):
        glDeleteTextures([self.texid])

stereo_image = SplitImage('data/reflect.jpg')

def draw_thing():
    global obj
    if not 'obj' in globals():
        load_obj()
        window.Refresh()

    glLightfv(GL_LIGHT0, GL_POSITION, (-40, 200, 100, 0.0))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.3, 0.3, 0.3, 0.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.3, 0.3, 0.3, 0.0))
    glEnable(GL_LIGHT0)
    glEnable(GL_LIGHTING)
    #glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glEnable(GL_COLOR_MATERIAL)
    glEnable(GL_DEPTH_TEST)
    glShadeModel(GL_SMOOTH)


def make_projection(camera, mode):
    assert mode in ('left','right','center')
    # Copy the matrix projection mode given camera parameters
    return np.eye(4)

@window.event
def post_draw():
    glScale(-1,1,1)
    # glRotate for pitch down and rotation
    glRotate(np.rad2deg(anim_angle), 0,1,0)
    obj.draw()
    glScale(-1,1,1)
    glDisable(GL_LIGHTING)
    glColor(1,1,1,1)


window.Refresh()
