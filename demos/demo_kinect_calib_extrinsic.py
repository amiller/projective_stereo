import numpy as np
import pylab
from OpenGL.GL import *
from OpenGL.GLUT import *
import opennpy
import os
import cv
from wxpy3d import Window
from wxpy3d.opengl_state import opengl_state
from blockplayer import table_calibration
from dividingline import synthetic_image, DividingLine
import dividingline

import scipy.optimize

if not 'window' in globals():
    window = Window(title="Projector")
    window.MoveXY(1600,0)
    window.ShowFullScreen(True)
    window.canvas.SetCurrent()
    glutInit()


from blockplayer import config
from blockplayer import main

import projective_stereo.projector; reload(projective_stereo.projector)
from projective_stereo.projector import load_projector


def fit_lines(rgb):
    color = cv.fromarray(rgb)
    gray = cv.CreateImage((color.width, color.height), 8, 1)
    cv.CvtColor(color, gray, cv.CV_RGB2GRAY)
    storage = cv.CreateMemStorage()
    lines = cv.HoughLines2(gray, storage, cv.CV_HOUGH_PROBABILISTIC, 1, 3.14/180, 100)


def line_through_point(p, angle):
    a = np.sin(angle)
    b = np.cos(angle)
    c = -(p[0]*a + p[1]*b)/p[2]
    return np.array((a,b,c))


def plot_line(L, color='k'):
    a,b,c = L

    # Solve for the point on the line nearest to the origin
    p = (a*c, b*c, -(a*a + b*b))
    within_eps = lambda a, b: np.abs(a-b) < 1e-5
    assert within_eps(np.dot(L, p), 0)

    v = np.array([b, -a],'f')
    p = np.array(p[:2])/p[2]

    x0 = p - 10000000*v
    x1 = p + 10000000*v

    plot((x0[0], x1[0]), (x0[1], x1[1]), color)


def finish_calibration(calib):
    mask = table_calibration.make_mask(config.bg['boundpts'])

    # Construct the homography from the camera to the XZ plane
    Hi = np.dot(config.bg['Ktable'], config.bg['KK'])
    Hi = np.linalg.inv(Hi)
    Hi = Hi[(0,1,3),:][:,(0,2,3)]

    L_table = []
    L_image = []
    for i, (L, rgb, depth) in enumerate(calib):
        Li = optimize(rgb)
        L_table.append(L)
        L_image.append(Li)
    L_table, L_image = map(np.array, (L_table, L_image))

    # We need to solve for M.

    #  P_image = Hi * M * P_table
    #  L_table * P_table = 0 when P_table is on L.
    #  L_image * P_image = 0 when P_image is on L.

    # So,
    #  L_image = L_table * np.linalg.inv(Hi * M)
    #  L_table = L_image * Hi * M
    
    # At this point, we could solve by constructing an Ax = 0 and
    # computing SVD (also known as the DLT method)

    # But since we know we're only looking for rigid transformations,
    # we can solve for rotation and translation separately.

    # To solve for rotation, lets look at the vanishing points.
    normalize2 = lambda x: x / np.sqrt((x[:2]**2).sum())

    V_table = np.array([normalize2(x[:2]) for x in L_table])
    V_image = np.array([normalize2(x[:2]) for x in np.dot(L_image, Hi)])

    V = np.dot(V_table.T, V_image)
    assert V.shape == (2,2)

    u,s,v = np.linalg.svd(V)
    R = np.dot(v,u.T)
    within_eps = lambda a, b: np.all(np.abs(a-b) < 1e-2)
    assert within_eps(np.dot(R, V_table.T), V_image.T)

    R_ = np.eye(3)
    R_[:2,:2] = R

    # Now we need to solve for the two translation parameters.
    # First lets normalize the lines so that the C's are the same.

    L_i = np.array(map(normalize2, np.dot(L_image, np.dot(Hi, R_))))
    L_t = np.array(map(normalize2, np.dot(L_table, np.eye(3))))

    A = L_i[:,:2]
    b = L_t[:,2] - L_i[:,2]

    x, _, _, _ = np.linalg.lstsq(A, b)

    R_ = R_.T
    R_[:2,2] = -x.T
    R_ = np.linalg.inv(R_)

    L_final = np.array(map(normalize2, np.dot(L_image, np.dot(Hi, R_))))
    L_gold = np.array(map(normalize2, L_table))
    assert within_eps(L_final, L_gold)

    M = np.eye(4)
    M[0,(0,2,3)] = R_[0,:]
    M[2,(0,2,3)] = R_[1,:]

    # If we've made it this far, then we can patch up the config
    print M
    config.bg['Ktable'] = np.dot(np.linalg.inv(M), config.bg['Ktable']).astype('f')
    config.save('data/newest_calibration')

    return M


middle_offset = dividingline.middle_offset
def optimize(rgb, debug=False):    

    im = rgb.mean(2).astype('u1')
    size = im.shape[::-1]
    mask = table_calibration.make_mask(config.bg['boundpts'])
    d = DividingLine(im, mask)

    def error(x):
        theta, dist = x
        line = middle_offset(theta, dist, size)
        s =  1./(d.score(line, debug) + 1e-5)
        if debug:
            clf()
            imshow(d.debug * d.image)
            pylab.waitforbuttonpress(0.01)
        return s

    for iteration in xrange(5):
        initial = (np.random.rand()*2*pi, (2*np.random.rand()-1)*100)
        r, score, _, _, _ = scipy.optimize.fmin(error, initial, 
                                                full_output=True, disp=False)
        # This threshold is based on empirical observations. Might change.
        if score < 0.02: break
    else:
        print 'Failed %d times' % iteration
        raise ValueError

    line = middle_offset(r[0], r[1], size)
    line = np.array(line) / line[2]
    res = d.traverse(line)

    # Scale the line so that a positive dot product indicates the point is
    # on the 'bright' side of the line
    if res['p1'] / res['p0'] < res['n1'] / res['n0']:
        line *= -1
    return line



def draw_line_XZ(L=np.array([0,1,1],'f')):
    glClearColor(0,0,0,1)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glEnable(GL_DEPTH_TEST)

    eye = projector.RT[:3,3]
    with projector.viewpoint_projection(eye, 0):
        a,b,c = L

        # Solve for the point on the line nearest to the origin
        p = (a*c, b*c, -(a*a + b*b))
        within_eps = lambda a, b: np.abs(a-b) < 1e-5
        assert within_eps(np.dot(L, p), 0)

        perp = np.array([a, b],'f')
        v = np.array([b, -a],'f')
        p = np.array(p[:2])/p[2]

        glColor(1,1,1,1)
        glBegin(GL_QUADS)
        for p_ in (p - 10*v,
                   p - 10*v + 10*perp,
                   p + 10*v + 10*perp,
                   p + 10*v):
            glVertex(p_[0], 0, p_[1])
        glEnd()

    window.canvas.SwapBuffers()
    

def run_calib():
    config.load('data/newest_calibration')
    opennpy.align_depth_to_rgb()

    samples = []

    for i in arange(0,2*np.pi,np.pi/8): 
        line = line_through_point(center, i)
        draw_line_XZ(line)
        pylab.waitforbuttonpress(0.1)
        for _ in range(60):
            opennpy.sync_update()
            rgb, _ = opennpy.sync_get_video()
            depth, _ = opennpy.sync_get_depth()
        samples.append((line, rgb, depth))

    return samples


# surfaces[0] is the horizontal table plane
# surfaces[1] is the vertical back drop
# These might as well extend beyond the projector's view limits.
surfaces = [
    [(0,1,0,0), [[[-10,0,-10], [-10,0,10], [10,0,10], [10,0,-10]]]],
    [(0,0,1,0), [[[-10,-10,0], [-10,10,0], [10,10,0], [10,-10,0]]]],
    ]

# The center point that all the 'calibration lines' should pass through
center = [0,0.45,1]

window.canvas.SetCurrent()
#projector = DELL_M109S()
#projector = OPTOMA_HD33()
projector = load_projector()
projector.surfaces = surfaces
projector.prepare_stencil()

window.Refresh()
