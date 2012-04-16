from OpenGL.GL import *
from OpenGL.GLUT import *
import numpy as np
from rtmodel import mesh
from rtmodel import camera
from wxpy3d import Window
from wxpy3d.opengl_state import opengl_state
import opennpy
import calibkinect
import cv
import scipy.ndimage
import os
import cPickle as pickle

opennpy.align_depth_to_rgb(); opennpy.sync_update()
np.set_printoptions(2)


"""
My best guess for the intrinsic calibration values for the dell projector are:
KK = [[2460, 0, 1152/2],
      [0, 2460, 863],
      [0, 0, 1]]

This is based on measuring the focal length with a tape measure, averaging
between my measurements for X and Y. Assume the principal point is at the bottom
and pixels are square.
      
"""

if not 'window' in globals():
    #window = CameraWindow(size=(1920,1080))
    window = Window(size=(1152,864), title="Chessboard")
    glutInit()
    window.Move((1152,0))
    window.ShowFullScreen(True)

class Checkerboard(object):
    def __init__(self, size, n_squares=(12,8)):
        w,h = size
        self.n_squares = n_squares
        self.pattern_size = (n_squares[0]-1, n_squares[1]-1)
        n_w, n_h = n_squares

        # Build a table of vertices
        X,Y = np.meshgrid(range(n_w+1), range(n_h+1))
        X = X.astype('f') * w / n_w
        Y = Y.astype('f') * h / n_h

        vertices = np.dstack((X, Y, np.zeros_like(X))).astype('f')

        # Store the inner coordinates as the img_points
        self.img_points = vertices[1:-1,1:-1,:2].reshape(-1,2)

        # Create 4 sets of coordinates for the vertices
        vertices = vertices.reshape(n_h+1, n_w+1, 1, 3)
        vertices = np.dstack((vertices[ :-1, :-1],
                              vertices[1:  , :-1],
                              vertices[1:  ,1:  ],
                              vertices[ :-1,1:  ]))
        self.vertices = vertices.reshape(-1, 3)
        self.quad_inds = np.array(range(self.vertices.shape[0]), dtype='i')

        # Build a table of colors
        X,Y = np.meshgrid(range(n_w), range(n_h))
        colors = ((X%2) ^ (Y%2)).reshape(-1,1)
        colors = np.hstack(4*[colors]).reshape(-1,1)
        colors = (colors * [1,1,1,0] + [0,0,0,1]) * 255
        self.colors = colors.astype('u1')

    def draw(self):
        w,h = window.Size
        with opengl_state():
            glEnableClientState(GL_VERTEX_ARRAY)
            glVertexPointerf(self.vertices)

            glEnableClientState(GL_COLOR_ARRAY)
            glColorPointerub(self.colors)

            glTranslate(-1,-1,1)
            glScale(2./w,2./h,1)
            glDrawElementsui(GL_QUADS, self.quad_inds)

checkerboard = Checkerboard(window.Size)

@window.event
def on_draw():
    glClearColor(0,0,0,1)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    checkerboard.draw()


def once():
    opennpy.sync_update()
    (depth,_), (rgb,_) = opennpy.sync_get_depth(), opennpy.sync_get_video()

    # Look for chessboard corners in the image
    was_found, corners = cv.FindChessboardCorners(cv.fromarray(255-rgb),
                                                  checkerboard.pattern_size)
    preview = cv.fromarray(rgb.copy())
    if was_found:
        cv.DrawChessboardCorners(preview, checkerboard.pattern_size,
                                 corners, was_found)
    cv.ShowImage("RGB", preview)
    if not was_found: return

    # Sample the kinect depth image X,Y,Z points at the corners
    XYZ = calibkinect.convertOpenNI2Real(depth)
    XYZ = [scipy.ndimage.map_coordinates(im, np.array(corners).transpose()[::-1,:],
                                         order=0, prefilter=False) for im in XYZ]
    XYZ = np.vstack(XYZ).transpose()
    return XYZ


def calibrate(img_points, frames):
    # We still need to convert the obj_points to a single plane
    def fit_plane(obj_points):
        # Fit a plane to the 3D points, and apply the rotation so that
        # X and Y are principal axes and Z is projected to 0
        assert obj_points.dtype == np.float32
        assert obj_points.shape[1] == 3
        obj_points = np.hstack((obj_points, np.ones((obj_points.shape[0],1))))
        vals,v = np.linalg.eig(np.cov(obj_points[:,:3].transpose()))
        i = np.argsort(vals)[::-1]
        # Construct M so that obj_points = M * planar_points 
        # with Z approximately 0
        M = np.eye(4)
        M[:3,:3] = v[:,i]                  # Store the inverse rotation
        M[:3,3] = obj_points[:,:3].mean(0) # Store the inverse translation
        planar_points = np.dot(np.linalg.inv(M), obj_points.transpose()).transpose()
        means = (planar_points**2).mean(0)
        assert means[2] < min(means[0], means[1])
        planar_points[:,2] = 0
        return planar_points[:,:3], M

    points_Ms = map(fit_plane, frames)
    obj_points = np.vstack([points for points,_ in points_Ms])
    obj_points = obj_points * [1,-1,1] + [0,864,0]
    all_img_points = np.tile(img_points, (len(frames),1))
    KK = cv.fromarray(np.array([[2460, 0, 1152/2.],
                                [0, 2460, 864],
                                [0,0,1]], dtype='f'))
    dc = cv.CreateMat(4,1, cv.CV_32F)
    rvecs = cv.CreateMat(len(frames), 3, cv.CV_32F)
    tvecs = cv.CreateMat(len(frames), 3, cv.CV_32F)
    npoints = np.array(len(frames)*[[len(img_points)]])

    cv.CalibrateCamera2(cv.fromarray(obj_points),
                        cv.fromarray(all_img_points),
                        cv.fromarray(npoints), (1152,864),
                        KK, dc, rvecs, tvecs, 
                        flags=(cv.CV_CALIB_ZERO_TANGENT_DIST |
                               cv.CV_CALIB_FIX_K1 |
                               cv.CV_CALIB_FIX_K2 |
                               cv.CV_CALIB_FIX_ASPECT_RATIO))
    # At this point we could use the KK and use rvecs and tvecs to construct
    # the projector's pose for each view. We would also need to compensate for
    # the flattening operation we did during fit_plane.
    return np.array(KK)
    

def go():
    global frames
    #frames = []
    print "Collecting calibration frames"
    print "Press 'c'"
    while 1:
        try:
            frame = once()
        except ZeroDivisionError:
            continue
        c = cv.WaitKey(50)
        if c == ord('c') and frame is not None:
            frames.append(frame)
            print len(frames), 'frames'
        if c in (ord('x'), ord('q'), 27):
            print 'done'
            break
    KK = calibrate(checkerboard.img_points, frames)

    pickle.dump(KK, open('data/newest_calibration/projector_KK.pkl','w'))
    pickle.dump(dict(img_points=checkerboard.img_points, frames=frames),
        open('data/newest_calibration/projector_frames.pkl','w'))
    return KK

window.Refresh()
docstring = """
Intrinsic calibration for a projector using a kinect.
Point the projector at a flat screen. The projector will
project a chessboard pattern. Now point a kinect at the
pattern. When you run 'go', the kinect will look for the 
pattern. Collect a few frames at varying distances. The
kinect doesn't need to stay stationary; you can move it 
around. 'q' or 'x' to finish.

   $ ipython
   In [1] run -i demos/demo_projector_calib_intrinsic
   In [2] go()

Results are saved in data/newest_calibration/projector_intrinsic.pkl
"""
if __name__ == "__main__": 
    print docstring
