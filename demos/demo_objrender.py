from wxpy3d import Window
from OpenGL.GL import *
from OpenGL.GLUT import *
from rtmodel import mesh
from rtmodel import camera
from wxpy3d.opengl_state import opengl_state

if not 'window' in globals():
    #window = CameraWindow(size=(1920,1080))
    window = Window(size=(1024,768))
    glutInit()
    window.ShowFullScreen(True)


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
    global anim_angle
    if is_animating:
        anim_angle += 0.005
        window.Refresh()

# Render the mesh before drawing points
@window.event
def on_draw():

    camera = None

    class NoDraw: draw = lambda _: None

    def render(mode):
        glDrawBuffer(dict(left=GL_BACK_LEFT,
                          right=GL_BACK_RIGHT,
                          center=GL_BACK)[mode])

        glClearColor(0,0,0,0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        proj_matrix, model_matrix = make_projection(camera, mode)
        glMatrixMode(GL_PROJECTION)
        glLoadMatrixf(proj_matrix.transpose())
        glMatrixMode(GL_MODELVIEW)
        glLoadMatrixf(model_matrix.transpose())

        with opengl_state(): 
            draw_thing()
        
    if 1 and glGetInteger(GL_STEREO):
        render('left')
        render('right')
    else:
        render('center')


def draw_thing():

    global obj
    if not 'obj' in globals():
        load_obj()
        window.canvas.SetCurrent()
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

    # glRotate for pitch down and rotation
    glRotate(-20*1, 1,0,0)
    glRotate(np.rad2deg(anim_angle), 0,1,0)
    glScale(-0.33,0.33,0.33)
    obj.draw()


def make_projection(camera, mode):
    assert mode in ('left','right','center')

    # Copy the matrix projection mode given camera parameters
    eyesep = 0.063       # Average adult eyes are 60mm apart
    width = 0.736        # Width of the projection image (m)
    focal_length = 1.5   # Distance to the projection image (m)
    ratio = 1920 / 1080. # Width / height
    #ratio = 1024 / 768. # Width / height

    far = 10
    near = 0.5  # Near plane is half meter in front of eyes
    tan_ap = 0.5 * width / focal_length
    wd2 = near * tan_ap
    ndfl = near / focal_length

    offsetx = dict(left=-1,right=1,center=0)[mode] * 0.5 * eyesep

    left  = - ratio * wd2 + offsetx * ndfl
    right =   ratio * wd2 + offsetx * ndfl
    top    =   wd2
    bottom = - wd2

    with opengl_state():
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glFrustum(left, right, bottom, top, near, far)
        projection = glGetFloatv(GL_PROJECTION_MATRIX).transpose()

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glTranslate(offsetx,0,-focal_length)
        glRotate(180, 0,1,0)
        modelview = glGetFloatv(GL_MODELVIEW_MATRIX).transpose()

    return projection, modelview


window.Refresh()
