"""
Andrew Miller   May 2012

An adaptation of Scott Ettinger's optimization for
fitting a line
"""

cimport numpy as np
import numpy as np
import cython


cdef struct Moment:
    np.uint32_t m0
    np.uint32_t m1
    np.uint64_t m2


cdef struct Result:
    Moment pos
    Moment neg


cdef _traverse_moments(np.uint32_t *m1,
                       np.uint64_t *m2,
                       int width, int height,
                       int l, int t, int r, int b,
                       float A, float B, float C,
                       dbg=None):

    cdef Result result
    cdef Moment moment

    if r-l < 1 or b-t < 1:
        return result

    p0 = l*A + t*B + C > 0
    p1 = l*A + b*B + C > 0
    p2 = r*A + t*B + C > 0
    p3 = r*A + b*B + C > 0

    if (p0 == p1 == p2 == p3):
        # We can stop traversing here - entirely on one side of the line

        if dbg is not None:
            dbg[t+1:b-1,l+1:r-1] = 1

        moment.m0 = (l-r)*(b-t)

        lt = m1[t*width+l]
        rt = m1[t*width+r]
        lb = m1[b*width+l]
        rb = m1[b*width+r]
        moment.m1 = lt + rb - lb - rt

        lt = m2[t*width+l]
        rt = m2[t*width+r]
        lb = m2[b*width+l]
        rb = m2[b*width+r]
        moment.m2 = lt + rb - lb - rt

        if p0: result.pos = moment
        else:  result.neg = moment

        return result

    else:
        # Recursively call the four sub-quadrants

        x = (l+r)/2
        y = (t+b)/2

        lt = _traverse_moments(m1, m2, width, height, l, t, x, y, A, B, C, dbg)
        rt = _traverse_moments(m1, m2, width, height, x, t, r, y, A, B, C, dbg)
        lb = _traverse_moments(m1, m2, width, height, x, y, r, b, A, B, C, dbg)
        rb = _traverse_moments(m1, m2, width, height, l, y, x, b, A, B, C, dbg)

        result.pos.m0 = lt.pos.m0 + rt.pos.m0 + lb.pos.m0 + rb.pos.m0
        result.pos.m1 = lt.pos.m1 + rt.pos.m1 + lb.pos.m1 + rb.pos.m1
        result.pos.m2 = lt.pos.m2 + rt.pos.m2 + lb.pos.m2 + rb.pos.m2

        result.neg.m0 = lt.neg.m0 + rt.neg.m0 + lb.neg.m0 + rb.neg.m0
        result.neg.m1 = lt.neg.m1 + rt.neg.m1 + lb.neg.m1 + rb.neg.m1
        result.neg.m2 = lt.neg.m2 + rt.neg.m2 + lb.neg.m2 + rb.neg.m2

        return result


def traverse_moments(np.ndarray[np.uint32_t, ndim=2, mode='c'] m1,
                     np.ndarray[np.uint16_t, ndim=2, mode='c'] m2,
                     line, rect, dbg=None):

    height, width = m1.shape[0], m1.shape[1]
    (A,B,C) = line
    ((l,t),(r,b)) = rect

    return _traverse_moments(<np.uint32_t *> m1.data,
                             <np.uint64_t *> m2.data,
                             width, height,
                             l, t, b, r, A, B, C, dbg)
