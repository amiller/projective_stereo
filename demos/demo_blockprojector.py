import numpy as np
import pylab
from OpenGL.GL import *
from OpenGL.GLUT import *
import opennpy
import os
import cv
from blockplayer.blockwindow import BlockWindow
from wxpy3d import Window
from wxpy3d.opengl_state import opengl_state

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

    preview = BlockWindow(size=(500,500), title="Preview")
    preview.Move((0,0))

window.canvas.SetCurrent()


from blockplayer import config
from blockplayer import opencl
from blockplayer import lattice
from blockplayer import grid
from blockplayer import stencil
from blockplayer import blockdraw
from blockplayer import dataset
from blockplayer import main
from blockplayer import colormap
from blockplayer import blockcraft

import projective_stereo.projector; reload(projective_stereo.projector)
from projective_stereo.projector import DELL_M109S, OPTOMA_HD33, load_projector


def calib(grid, modelmat):
    global img_points
    img_points = []

    try:
        going = True

        @window.eventx
        def EVT_MOUSE_EVENTS(evt):
            global going, img_points
            if evt.ButtonUp(wx.MOUSE_BTN_LEFT):
                img_points.append(evt.Position)
                print('Picked point %d of 6' % (len(img_points)))
                if len(img_points) == len(obj_points):
                    print "Done"
                    going = False

        print("""[Kinect-to-projector Calibration]

Make sure the current frame contains a calibration cube, an L shape
bracket that's 6x6 duplo units.

Click the two:
""")

        while going: cv.WaitKey(10)

    finally:
        pass

def once():
    global depth, rgb
    preview.canvas.SetCurrent()

    opennpy.sync_update()
    depth,_ = opennpy.sync_get_depth()
    rgb,_ = opennpy.sync_get_video()

    main.update_frame(depth, rgb)

    blockdraw.clear()
    #blockdraw.show_grid('o1', main.occvac.occ, color=np.array([1,1,0,1]))
    if 'RGB' in stencil.__dict__:
        blockdraw.show_grid('occ', grid.occ, color=grid.color)
    else:
        blockdraw.show_grid('occ', grid.occ, color=np.array([1,0.6,0.6,1]))

    preview.clearcolor=[0,0,0,0]
    preview.flag_drawgrid = True

    if 'R_correct' in main.__dict__:
        preview.modelmat = main.R_display
    else:
        preview.modelmat = main.R_aligned

    preview.Refresh()
    window.Refresh()
    pylab.waitforbuttonpress(0.005)


def resume():
    while 1: once()


def start():
    main.initialize()
    config.load('data/newest_calibration')
    opennpy.align_depth_to_rgb()
    dataset.setup_opencl()


def go():
    start()
    resume()


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


def draw_blocks():
    with opengl_state():
        glMultMatrixf(np.linalg.inv(preview.modelmat).transpose())
        LH,LW = config.LH, config.LW
        glScale(LW,LH,LW)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
        glPushMatrix()
        glTranslate(*config.bounds[0])
        blockdraw.draw()
        glPopMatrix()

        # Draw the axes for the model coordinate space
        glLineWidth(3)
        glBegin(GL_LINES)
        glColor3f(1,0,0); glVertex3f(0,0,0); glVertex3f(1,0,0)
        glColor3f(0,0,1); glVertex3f(0,0,0); glVertex3f(0,0,1)
        glEnd()


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
        # draw_decals()

    # For each projection surface plane, we need to do a render
    eye = projector.RT[:3,3]

    for plane_index in [0, 1]:
        with projector.viewpoint_projection(eye, plane_index):
            draw_decals()
            draw_blocks()


@preview.event
def post_draw():
    draw_decals()


surfaces = [
    [(0,1,0,0), [[[-10,0,-10], [-10,0,10], [10,0,10], [10,0,-10]]]],
    [(0,0,1,0), [[[-10,-10,0], [-10,10,0], [10,10,0], [10,-10,0]]]],
    ]

window.canvas.SetCurrent()
#projector = DELL_M109S()
#projector = OPTOMA_HD33()
projector = load_projector()
projector.surfaces = surfaces
projector.prepare_stencil()

preview.Refresh()
window.Refresh()

