from OpenGL.GL import *
from OpenGL.GLUT import *
import numpy as np
from rtmodel import mesh
from rtmodel.camera import Camera
from wxpy3d import Window
from wxpy3d import PointWindow
from wxpy3d.opengl_state import opengl_state
import cv
import wx


if not 'window' in globals():
    if 0: 
        # Dell M1509
        window = Window(size=(1152,864), title="DELL_1509S")
        window.MoveXY(1152,0)

    else: 
        # Optoma HD33
        window = Window(size=(500,500), title="OPTOMA_HD33")
        window.MoveXY(1600,0)

    glutInit()
    window.ShowFullScreen(True)

    preview = PointWindow(size=(500,500), title="Preview")
    preview.Move((0,0))

window.canvas.SetCurrent()


import projective_stereo.projector; reload(projective_stereo.projector)
from projective_stereo.projector import DELL_M109S, OPTOMA_HD33, load_projector

from projective_stereo.projector import Projector
from projective_stereo.projector import cv2opengl

from projective_stereo import extrinsic
reload(extrinsic)

np.set_printoptions(2)


def load_obj(name='gamecube'):
    global obj
    window.canvas.SetCurrent()
    obj = mesh.load(name)
    obj.RT = np.eye(4, dtype='f')
    obj.RT[:3,3] = -obj.vertices[:,:3].mean(0)
    window.Refresh()


def draw_decals():
    # Only draw things that are known to be on the projection surfaces
    w, h = (0.2160, 0.2794)
    obj_points = np.array([[-w/2, h/2, 0], [w/2, h/2, 0],
                           [-w/2, 0,   0], [w/2, 0,   0],
                           [-w/2, 0, h/2], [w/2, 0, h/2]])

    glBegin(GL_LINES)
    glColor(1,1,1)
    for i in (0,1, 2,3, 4,5,  0,2, 2,4,  1,3, 3,5):
        glVertex(*obj_points[i])
    glEnd()
    with opengl_state():
        glScale(.05,.5,.05)
        glBegin(GL_LINES)
        glColor(1,0,0); glVertex(0,0,0); glVertex(1,0,0)
        glColor(0,1,0); glVertex(0,0,0); glVertex(0,1,0)
        glColor(0,0,1); glVertex(0,0,0); glVertex(0,0,1)
        glEnd()


def draw_sights(eye):
    rot = np.eye(4, dtype='f')
    mag = lambda x : np.sqrt((x*x).sum())
    norm = lambda x : x / mag(x)
    rot[:3,2] = norm(-eye)
    rot[:3,0] = norm(np.cross([0,1,0], rot[:3,2]))
    rot[:3,1] = norm(np.cross(rot[:3,2], rot[:3,0]))

    def circle(rad, N=20):
        glBegin(GL_LINE_LOOP)
        np.tau = np.pi*2
        for h in np.arange(0, np.tau, np.tau/N):
            glVertex(rad*np.cos(h), rad*np.sin(h))
        glEnd()
        
    def cross(rad):
        glRotate(45,0,0,1)
        glScale(rad, rad, rad)
        glBegin(GL_LINES)
        glVertex(-1,0,0); glVertex(1,0,0)
        glVertex(0,-1,0); glVertex(0,1,0)
        glEnd()

    rad = 0.05
    with opengl_state():
        glColor(1,0,0)
        glTranslate(rad,0,0)
        glMultMatrixf(rot.transpose())
        cross(rad*0.6)

    rad = 0.05
    with opengl_state():
        glColor(1,0,0)
        glTranslate(-rad,0,0)
        glMultMatrixf(rot.transpose())
        cross(rad*0.6)

    with opengl_state():
        glColor(1,0,0)
        glMultMatrixf(rot.transpose())
        circle(rad)
        glTranslate(0, 0, -mag(eye)/2)
        circle(rad)
        
def draw_eye(eye):
    with opengl_state():
        glTranslate(*eye)
        glColor(1,1,0)
        glutSolidSphere(.02, 10, 10)

def draw_objects(eye):
    vertices = [[0,0,0],[0,0,1],[0,1,1],[0,1,0],
                [1,1,0],[1,1,1],[1,0,1],[1,0,0]]

    cube_inds = [0,1, 1,2, 2,3, 3,4, 4,5, 5,6, 6,7, 0,3, 4,7, 1,6, 2,5]
    Y_inds = [0,1, 1,6, 6,7, 7,0]
    Z_inds = [0,3, 3,4, 4,7, 7,0]

    draw_eye(eye)
    draw_sights(eye)
    with opengl_state():
        glScale(.05,.05,.05)
        glTranslate(-0.5, 0, 0)
        glBegin(GL_LINES)
        glColor(0,1,0)
        for i in cube_inds: glVertex(*vertices[i])
        glEnd()

    if 'obj' in globals():
        with opengl_state():
            glScale(.1,.1,.1)
            glRotate(rot_angle, 0, 1, 0)
            glScale(-1,1,1)
            obj.draw()

rot_angle = 0.0
is_animating = False
@window.eventx
def EVT_IDLE(evt):
    global rot_angle
    if is_animating:
        rot_angle += 0.1
        window.Refresh()

        
@window.event
def on_draw():
    glClearColor(0,0,0,1)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glEnable(GL_DEPTH_TEST)

    global projector
    if not 'projector' in globals(): return

    # Project decals directly to the projector, no eye needed
    with opengl_state():
        projector.setup_projection_matrix()
        # draw_decals() # Depth is inconsistent between decals and viewpoint

    # For each projection surface plane, we need to do a render
    for plane_index in [0, 1]:
        with projector.viewpoint_projection(eye, plane_index):
            draw_decals()
            draw_objects(eye)


surfaces = [
    [(0,1,0,0), [[[-10,0,-10], [-10,0,10], [10,0,10], [10,0,-10]]]],
    [(0,0,1,0), [[[-10,-10,0], [-10,10,0], [10,10,0], [10,-10,0]]]],
    ]

window.canvas.SetCurrent()
#projector = DELL_M109S()
#projector = OPTOMA_HD33()
projector = load_projector()
projector.surfaces = surfaces

eye = projector.RT[:3,3]# + [0.2,0.4,.4]
projector.prepare_stencil()


def calibrate():
    extrinsic.run_calib()


@preview.event
def post_draw():
    glClearColor(0,0,0,1)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    draw_decals()
    draw_objects(eye)
    projector.render_frustum()


window.Refresh()
preview.Refresh()

if __name__ == "__main__": 
    pass
