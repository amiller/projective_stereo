from OpenGL.GL import *
from OpenGL.GL import shaders
from contextlib import contextmanager
from wxpy3d.opengl_state import opengl_state
from rtmodel.camera import Camera
import numpy as np
import cv


def make_opencv_intrinsic(F, cx, cy):
        return np.array([[F, 0, cx],
                         [0, F, cy],
                         [0, 0, 1 ]], dtype='f')


def cv2opengl(KK_CV, size, near=0.01, far=10.0):
    W,H = size
    assert KK_CV[0,0] == KK_CV[1,1]
    F = KK_CV[0,0]
    cx = KK_CV[0,2]
    cy = KK_CV[1,2]

    left  =  near*(0-cx)/F
    right =  near*(W-cx)/F
    bottom = near*(cy-H)/F
    top =    near*(cy-0)/F

    with opengl_state():
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glFrustum(left, right, bottom, top, near, far)
        GL_KK = glGetFloatv(GL_PROJECTION_MATRIX).transpose()
        return GL_KK


def make_projector_cv(KK_CV, size):
    assert KK_CV[0,0] == KK_CV[1,1]
    F = KK_CV[0,0]
    cx = KK_CV[0,2]
    cy = KK_CV[1,2]
    return make_projector(F, size, cx, cy)


def make_projector(F, size, cx, cy):
    KK_CV = make_opencv_intrinsic(F, cx, cy)
    KK = cv2opengl(KK_CV, size)
    projector = Projector(KK)    
    projector.F = F
    projector.cx = cx
    projector.cy = cy
    return projector


class ViewpointProjectionProgram():
    vertex_code = """
    #version 120

    uniform mat4 KKp_invRTp_RTe; // Takes us to projector clip coordinates
    uniform mat4 KKe_invRTe;     // Takes us to eye-image-plane coordinates
    uniform float A, B;          // Depth clipping coordinates

    const float near = 0.01;
    const float far = 5.0;

    void main(void) {
        // Project onto the image plane in eye coordinates
        vec4 e = KKe_invRTe * gl_ModelViewMatrix * gl_Vertex;

        // Stash enough to recover z for now
        float z_clip = (A * e.w + B) / e.w;

        // Now project the homogeneous coordinates back to the projector
        vec4 p = KKp_invRTp_RTe * e;

        // Pass through the clip depth coordinates
        // p.z = 0.2;
        // p.z = 0; //z_clip;
        // FIXME clipping seems to be off
        p.z = z_clip/100.;
        gl_Position = p;

        // Correct for the texture coordinates
        vec4 t = gl_MultiTexCoord0;
        //t.s = t.t = e.w;
        gl_TexCoord[0] = t;
        gl_FrontColor = gl_Color;

        // TODO: Add lighting parameters?
        // TODO: Add normals calculation and other mapping features
        // TODO: Does texturing actually work?
    }
    """
    fragment_code = """
    #version 120
    void main(void) {
        gl_FragColor = gl_Color;
    }
    """

    def __init__(self):
        # Create the opengl textures we need
        vert = shaders.compileShader(ViewpointProjectionProgram.vertex_code,
                                     GL_VERTEX_SHADER)
        #frag = shaders.compileShader(ViewpointProjectionProgram.fragment_code,
        #                             GL_FRAGMENT_SHADER)

        self.program = shaders.compileProgram(vert)

    @contextmanager
    def projection(self, projector, eye, plane):
        KKp = projector.KK
        RTp = projector.RT

        # Construct a projection matrix that projects onto the plane.
        # Additionally the scale should be set so w is the actual depth. 
        # Then (A*w + B)/w is the clipped depth for eye coordinates
        F = np.dot(np.concatenate((eye,[1])), plane.transpose())
        if F < 0: F *= -1

        KKe = np.array([[F, 0, 0, 0],
                        [0, F, 0, 0],
                        [0, 0, F, 0],
                        [0, 0,-1, 0]]) # Note - a projection, not invertible

        near = 0.01
        far = 5.0
        A = -(far + near) / (far - near)
        B = -(2*far*near) / (far - near)

        # Sanity checks
        within_epsilon = lambda a, b: (np.abs(a-b) < 1E-5).all()
        near_zero = lambda x: within_epsilon(x, np.float32(0))
        def check():
            #print near, far
            #print A, B
            divide = lambda w: (A * w + B) / w
            assert within_epsilon(divide(-near),1)
            assert within_epsilon(divide(-far),-1)
        check()


        # Construct the Eye view matrix from the plane and the projector
        RTe = np.eye(4, dtype='f')
        magnitude = lambda x: np.sqrt(np.sum(x*x))
        normalize = lambda x: x / magnitude(x)
        RTe[:3,3] = eye             # Last column is the actual eye position
        RTe[:3,2] = normalize(plane[:3])  # Take Z to be the plane normal
        RTe[:3,0] = normalize(np.cross(RTp[:3,1], RTe[:3,2]))
        RTe[:3,1] = normalize(np.cross(RTe[:3,2], RTe[:3,0]))

        # Pack everything up and configure the shader
        KKe_invRTe = np.dot(KKe, np.linalg.inv(RTe))
        KKp_invRTp_RTe = np.dot(np.dot(KKp, np.linalg.inv(RTp)), RTe)
        homo_divide = lambda x: (x[0]/x[3], x[1]/x[3], x[2]/x[3])
        
        if 0:
            print 'KKe_invRTe'
            print KKe_invRTe
            print

            print 'KKe'
            print KKe
            print

            print 'KKp_invRTp_RTe'
            print KKp_invRTp_RTe
            print

            print homo_divide(np.dot(KKe_invRTe, [0,0,0,1]))

        self.RTe = RTe
        self.KKe = KKe

        toplane = np.dot(RTe, KKe_invRTe)
        KKp_invRTp = np.dot(KKp, np.linalg.inv(RTp))
        full = np.dot(KKp_invRTp, toplane)

        # Some sanity checks to demonstrate how this works
        within_epsilon = lambda a, b: (abs(a-b) < 1E-5).all()
        near_zero = lambda x: within_epsilon(x, np.float32(0))

        assert within_epsilon(full, np.dot(KKp_invRTp_RTe, KKe_invRTe))

        # For any point on the plane, 
        # (RTe) (KKe)(RTe^-1) P should also be on the plane
        def check_plane(P):
            assert near_zero(np.dot(P, plane))
            RTe_KKe_invRTe = np.dot(RTe, KKe_invRTe)
            assert near_zero(np.dot(np.dot(RTe_KKe_invRTe, P), plane))
            return homo_divide(np.dot(RTe_KKe_invRTe, P))

        assert near_zero(check_plane([0,0,0,1])) # Origin is untouched
        if within_epsilon(plane, [0,1,0,0]):
            check_plane([1,0,1,1])
            check_plane([-1,0,-1,1])
        if within_epsilon(plane, [0,0,1,0]):
            check_plane([1,1,0,1])
            check_plane([-1,-1,0,1])


        def point_journey(P=[0,0,0,1]):
            toplane = np.dot(RTe, KKe_invRTe)
            full = np.dot(KKp_invRTp, toplane)
            print 'P:                        ', P
            print '(invRTe)P:                ', homo_divide(np.dot(np.linalg.inv(RTe), P))
            print '(KKe_invRTe)P:            ', homo_divide(np.dot(KKe_invRTe, P))
            print '(RTe_KKe_invRTe)P: (plane)', homo_divide(np.dot(toplane, P))
            print '(full)P: ', homo_divide(np.dot(full, P))

        #point_journey()        
        p = self.program
        loc = lambda x: glGetUniformLocation(p, x)
        matrix = lambda k, f: glUniformMatrix4fv(k, 1, True, f.astype('f'))
        assert glIsProgram(p)

        with opengl_state():
            """Load the appropriate matrices for projection and view

               KK_e * RTe^-1 * P 

            where P is a point in world coordinates
            """
            # Set up GL_MODELVIEW with identity so that
            # consumers can use world (model) coordinates
            try:
                glUseProgram(self.program)

                matrix(loc("KKe_invRTe"), KKe_invRTe)
                matrix(loc("KKp_invRTp_RTe"), KKp_invRTp_RTe)
                glUniform1f(loc("A"), A)
                glUniform1f(loc("B"), B)

                glMatrixMode(GL_MODELVIEW)
                glLoadIdentity()

                yield
            finally:
                glUseProgram(0)    


class Projector(Camera):
    def __init__(self, KK, RT=np.eye(4,dtype='f'), surfaces={}):
        assert KK.shape == RT.shape == (4,4)
        assert KK.dtype == RT.dtype == np.float32
        self.KK = KK
        self.RT = RT

        # Surfaces is of the form {plane => [poly1, poly2, etc]}
        self.surfaces = surfaces
        self.viewpoint_program = ViewpointProjectionProgram()

    def prepare_stencil(self):
        # Deal with each of the surfaces
        glClearStencil(0)
        glClear(GL_DEPTH_BUFFER_BIT | GL_COLOR_BUFFER_BIT)
        with opengl_state():
            glColorMask(0,0,0,0)
            glEnable(GL_STENCIL_TEST)
            glEnable(GL_DEPTH_TEST)
            #glColorMask(0,0,0,0)  # Only care about stencil buffer            
            self.setup_projection_matrix()
            for i,(plane,quads) in enumerate(self.surfaces):
                ref = i+1
                glStencilFunc(GL_ALWAYS, ref, ref)
                glStencilOp(GL_KEEP, GL_KEEP, GL_REPLACE)
                glBegin(GL_QUADS)
                colors = [[1,0,0],[0,1,0],[0,0,1]]
                glColor3f(*colors[ref])
                for quad in quads:
                    for q in quad: glVertex(*q)
                glEnd()


    def make_opencv_intrinsic(self):
        assert all([i in dir(self) for i in ('F','cx','cy')])
        return make_opencv_intrinsic(self.F, self.cx, self.cy)


    def setup_projection_matrix(self):
        """
        This sets up a simple projection for when the projector itself 
        is the intended viewpoint. This is good for when the objects being
        drawn are known to coincide with the projection surface(s). If it's
        correct for the projector, in these cases, then it will be correct
        from all viewpoints. In particular no head tracking is needed.
        """
        glMatrixMode(GL_PROJECTION)
        glLoadMatrixf(self.KK.transpose())
        glMatrixMode(GL_MODELVIEW)
        glLoadMatrixf(np.linalg.inv(self.RT).transpose())


    def calibrate_extrinsic(self, img_points, obj_points):
        KK_CV = self.make_opencv_intrinsic()
        img_p = cv.fromarray(img_points)
        obj_p = cv.fromarray(obj_points*[1,1,1])
        KK = cv.fromarray(KK_CV)
        dc = cv.fromarray(np.zeros((4,1),'f'))
        rvec = cv.fromarray(np.zeros((3,1),'f'))
        rmat = cv.fromarray(np.zeros((3,3),'f'))
        tvec = cv.fromarray(np.zeros((3,1),'f'))
        cv.FindExtrinsicCameraParams2(obj_p, img_p, KK,
                                      dc, rvec, tvec)
        cv.Rodrigues2(rvec,rmat)
        RT = np.eye(4,dtype='f')
        RT[:3,:3] = rmat
        RT[:3,3] = np.array(tvec).flatten()

        # This is the place where we correct for opencv's different opinion
        # of how a camera matrix is oriented.
        self.RT = np.dot(np.linalg.inv(RT), np.diag([1,-1,-1,1]))


    @contextmanager
    def viewpoint_projection(self, eye, plane_index):
        ref = plane_index+1
        plane,_ = self.surfaces[plane_index]
        with opengl_state():
            glEnable(GL_STENCIL_TEST)
            glStencilFunc(GL_EQUAL, ref, 0xFF)
            glStencilOp(GL_KEEP, GL_KEEP, GL_KEEP)
            with self.viewpoint_program.projection(self, eye, np.array(plane)):
                yield


def DELL_M109S():
    F = 2460.
    W = 1152.
    H = 864.
    cx = W/2
    cy = H
    return make_projector(F, (W, H), cx, cy)
