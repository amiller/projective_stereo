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

import projective_stereo.projector; reload(projective_stereo.projector)
from projective_stereo.projector import DELL_M109S

from projective_stereo.projector import Projector
from projective_stereo.projector import cv2opengl

np.set_printoptions(2)


"""
There are 6 known points projector projects. The scenario is 
a table surface with a 90 degree backdrop. An 8.5"x11" paper
is folded in half (hamburger style) and placed in the 90 degree
nook.
"""
w, h = (0.2160, 0.2794)
obj_points = np.array([[-w/2, h/2, 0], [w/2, h/2, 0],
                       [-w/2, 0,   0], [w/2, 0,   0],
                       [-w/2, 0, h/2], [w/2, 0, h/2]])

img_points = np.array([
        (113, 102),
        (961, 85),
        (156, 613),
        (927, 596),
        (81, 832),
        (1019, 811)],'f')

surfaces = [
    [(0,1,0,0), [[[-10,0,-10], [-10,0,10], [10,0,10], [10,0,-10]]]],
    [(0,0,1,0), [[[-10,-10,0], [-10,10,0], [10,10,0], [10,-10,0]]]],
    ]


def show_stencil():
    window.canvas.SetCurrent()
    projector.prepare_stencil()


def load_obj(name='gamecube'):
    global obj
    window.canvas.SetCurrent()
    obj = mesh.load(name)
    obj.RT = np.eye(4, dtype='f')
    obj.RT[:3,3] = -obj.vertices[:,:3].mean(0)
    window.Refresh()


if not 'window' in globals():
    #window = CameraWindow(size=(1920,1080))
    window = Window(size=(1152,864), title="Chessboard")
    glutInit()
    window.Move((1152,0))
    window.ShowFullScreen(True)

    preview = PointWindow(size=(500,500), title="Preview")
    preview.Move((0,0))


def draw_decals():
    # Only draw things that are known to be on the projection surfaces
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
    with opengl_state():
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

        def crosses(rad):
            glRotate(45,0,0,1)
            glBegin(GL_LINES)
            glVertex(-rad*2,-rad)
            glVertex( rad*2,-rad)
            glVertex(-rad*2, rad)
            glVertex( rad*2, rad)
            glVertex(-rad,-rad*2)
            glVertex(-rad, rad*2)
            glVertex( rad,-rad*2)
            glVertex( rad, rad*2)
            glEnd()

        glMultMatrixf(rot.transpose())
        glColor(1,0,0)
        rad = 0.05
        circle(rad)
        glTranslate(0, 0, -mag(eye)/2)
        circle(rad)
        crosses(rad*0.6)
        
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


window.canvas.SetCurrent()
projector = DELL_M109S()
projector.surfaces = surfaces
projector.calibrate_extrinsic(img_points, obj_points)
eye = projector.RT[:3,3] + [0.2,0.4,.0]
projector.prepare_stencil()


def calibrate():
    projector.calibrate_extrinsic(img_points, obj_points)
    preview.Refresh()
    window.Refresh()


@preview.event
def post_draw():
    glClearColor(0,0,0,1)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    draw_decals()
    draw_objects(eye)
    projector.render_frustum()


def go():
    going = True
    img_points = []
    try:
        window.event
        @window.eventx
        def EVT_MOUSE_EVENTS(evt):
            if not going: return
            if evt.ButtonUp(wx.MOUSE_BTN_LEFT):
                img_points.append(evt.Position)
                print len(obj_points), 'points'
                if len(image_points) == len(obj_points):
                    print "Done"
                    going = False

        print """
There should be 6 points marked on the table and backdrop. 
Moving the mouse over the projected display, click each of the points
in order:
   (left top, on the backdrop),
   (right top, on the backdrop),
   (left center, on the crease),
   (right center, on the crease),
   (left bottom, on the table),
   (right bottom, on the table)
"""
        while 1:
            cv.WaitKey(20)
    finally:
        going = False

window.Refresh()
preview.Refresh()

docstring = """
Extrinsic projector calibration
"""
if __name__ == "__main__": 
    pass
    #print docstring
