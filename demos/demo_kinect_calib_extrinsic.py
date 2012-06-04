import numpy as np
import pylab
from OpenGL.GL import *
from OpenGL.GLUT import *
import opennpy
import os
import cv
from wxpy3d import Window
from wxpy3d.opengl_state import opengl_state

if not 'window' in globals():
    window = Window(title="Projector")
    window.MoveXY(1600,0)
    window.ShowFullScreen(True)
    window.canvas.SetCurrent()
    glutInit()



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
from projective_stereo.projector import load_projector


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

    preview.Refresh()
    window.Refresh()
    pylab.waitforbuttonpress(0.005)


def resume():
    while 1: once()


def start():
    config.load('data/newest_calibration')
    opennpy.align_depth_to_rgb()


def fit_lines(rgb):
    color = cv.fromarray(rgb)
    gray = cv.CreateImage((color.width, color.height), 8, 1)
    cv.CvtColor(color, gray, cv.CV_RGB2GRAY)
    storage = cv.CreateMemStorage()
    lines = cv.HoughLines2(gray, storage, cv.CV_HOUGH_PROBABILISTIC, 1, 3.14/180, 100)
    print lines


def go():
    start()
    resume()


def draw_line_XZ(L=np.array([0,1,1],'f')):
    glClearColor(0,0,0,1)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glEnable(GL_DEPTH_TEST)

    eye = projector.RT[:3,3]
    with projector.viewpoint_projection(eye, 0):
        a,b,c = L

        # Solve for the point on the line nearest to the origin
        p = (a, b, - (a*a + b*b) / c)
        within_eps = lambda a, b: np.abs(a-b) < 1e-5
        assert within_eps(np.dot(L, p), 0)

        perp = np.array([a, b],'f')
        v = np.array([b, -a],'f')
        p = np.array(p[:2])/p[2]

        glColor(1,1,1,1)
        glBegin(GL_QUADS)
        print p
        for p_ in (p - 100*v,
                   p - 100*v + 100*perp,
                   p + 100*v + 100*perp,
                   p + 100*v):
            glVertex(p_[0], 0, p_[1])
        glEnd()

    window.canvas.SwapBuffers()


surfaces = [
    [(0,1,0,0), [[[-10,0,-10], [-10,0,10], [10,0,10], [10,0,-10]]]],
    [(0,0,1,0), [[[-10,-10,0], [-10,10,0], [10,10,0], [10,-10,0]]]],
    ]

window.canvas.SetCurrent()
#projector = DELL_M109S()
#projector = OPTOMA_HD33()
projector = load_projector()
projector.surfaces = surfaces
projector.prepare_stencil() # Prepare stencil seems to need to be called twice

window.Refresh()
