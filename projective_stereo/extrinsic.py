from pylab import *
import wx
import cv

from projective_stereo.projector import OPTOMA_HD33
from wxpy3d import Window


newest_folder = "data/newest_calibration"

def run_calib(projector=OPTOMA_HD33()):
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

    global img_points, going
    img_points = []

    try:
        window = Window()
        window.MoveXY(1600,0)
        window.ShowFullScreen(True)
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

        print("""[Extrinsic Calibration] 

There should be 6 points marked on the table and backdrop. 
Moving the mouse over the projected display, click each of the points
in order:
   (left top, on the backdrop),
   (right top, on the backdrop),
   (left center, on the crease),
   (right center, on the crease),
   (left bottom, on the table),
   (right bottom, on the table)

Follow along with this illustration: http://imgur.com/asfsfd.jpg

Click the six points:
""")

        while going: cv.WaitKey(10)

    finally:
        window.Close()

    img_points = np.array(img_points, 'f')
    projector.calibrate_extrinsic(img_points, obj_points)

    np.save('%s/config/projector' % (newest_folder), (projector.KK, projector.RT))
    print('OK')
