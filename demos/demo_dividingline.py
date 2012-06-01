from projective_stereo import dividingline; reload(dividingline)
from projective_stereo.dividingline import DividingLine

line = [1,1,-300]
im = dividingline.synthetic_image((640,480), line)
dbg = np.zeros_like(im)
d = dividingline.DividingLine(im)

res = d._traverse(line, ((0,0),im.shape[::-1]), debug=dbg)
