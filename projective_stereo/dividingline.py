"""
Andrew Miller   May 2012


"""

import numpy as np
import operator
from dividingline_cy import traverse_moments


class DividingLine(object):
    def __init__(self, image, weights=None):
        assert image.dtype in (np.uint8, np.float32)
        assert len(image.shape) == 2, "Greyscale only for now"

        self.image = image

        # Compute the integral image
        self.m1 = np.cumsum(np.cumsum(image.astype('u4'), 0), 1)
        self.m2 = np.cumsum(np.cumsum(image.astype('u8')**2, 0), 1)


    def traverse(self, line, debug=False):
        debug = None if not debug else np.zeros_like(self.image)
        return self._traverse(line, ((0,0),self.image.shape[::-1]), 
                              debug=debug)

    def traverse_cy(self, line, debug=False):
        debug = None if not debug else np.zeros_like(self.image)
        rect = ((0,0),self.image.shape[::-1])
        return traverse_moments(self.m1, self.m2, line, rect, debug)


    def _traverse(self, line, rect, 
                  f = lambda _: 0,
                  g = operator.add, # addition-like
                  init=0,           # initial value for reduction
                  debug=None):      # debug output image

        (l,t),(r,b) = rect

        points = np.array([[l,t,1], [l,b,1],
                           [r,t,1], [r,b,1]])
        p = np.dot(points, line)

        if np.all(p > 0) or np.all(p < 0) or \
                ((r-l) <= 1 and (b-t) <= 1):

            if debug is not None:
                debug[t+1:b-1,l+1:r-1] = 1

            # We apply the base case when either:
            # a: the entire rectangle is on one side
            #    of the line, or
            # b: there's only one pixel

            return f(rect)
        else:

            # Find the center point...
            x = (l+r)/2
            y = (t+b)/2

            # ... then split into four sub-rectangles
            subs = [((l,t), (x,y)),
                    ((x,t), (r,y)),
                    ((x,y), (r,b)),
                    ((l,y), (x,b))]

            # Apply apply g to the four sub problems
            res = reduce(g, [self._traverse(line, s, f, g, init, debug)
                             for s in subs], init)
            return res


def random_middle_line(size=(640,480)):
    # Returns a line passing through the center of the image
    # at a random orientation
    a,b = np.random.rand(2)-0.5
    c = -(size[0]*a + size[1]*b)
    return np.array([a,b,c], 'f')


def synthetic_image(size, line=[1,1,-300]):
    x,y = np.meshgrid(range(size[0]), range(size[1]))
    w = np.ones_like(x)

    b = np.sum(line * np.dstack((x,y,w)), axis=2)
    return (b > 0).astype('u1') * 255
