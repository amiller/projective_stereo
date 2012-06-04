from setuptools import setup
from setuptools.extension import Extension
from Cython.Distutils import build_ext

ext_modules=[]

setup(name='Projective stereo',
      version='0.1',
      author='Andrew Miller',
      email='amiller@cs.ucf.edu',
      packages=['projective_stereo'],
      cmdclass={'build_ext': build_ext},
      ext_modules=ext_modules,
      install_requires=['distribute', 'cython', 'pyopencl', 'PyOpenGL', 'numpy', 'scipy'],
      dependency_links = [
        "https://github.com/amiller/wxpy3d/tarball/master#egg=wxpy3d-1.0",
        "https://github.com/amiller/glxcontext/tarball/master#egg=glxcontext-1.0",
        "https://github.com/amiller/dividingline/tarball/master#egg=dividingline-1.0",
        ])

