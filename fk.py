# -*- coding: utf-8 -*-
#!/usr/bin/env python

import rospy
from std_msgs.msg import Float32MultiArray
from geometry_msgs.msg import Twist

import math
import numpy
import matplotlib.pyplot as plt

import time

def ik(bPos, pPos, a, ik=True):
    """Finds leg lengths L such that the platform is in position defined by
    a = [x, y, z, alpha, beta, gamma]
    """
    phi = a[3]
    th = a[4]
    psi = a[5]
    #Must translate platform coordinates into base coordinate system
    #Calculate rotation matrix elements
    cphi = math.cos(phi)
    sphi = math.sin(phi)
    cth = math.cos(th)
    sth = math.sin(th)
    cpsi = math.cos(psi)
    spsi = math.sin(psi)   
    #Hence calculate rotation matrix
    #Note that it is a 3-2-1 rotation matrix
    Rzyx = numpy.array([[cpsi*cth, cpsi*sth*sphi - spsi*cphi, cpsi*sth*cphi + spsi*sphi] \
                        ,[spsi*cth, spsi*sth*sphi + cpsi*cphi, spsi*sth*cphi - cpsi*sphi] \
                        , [-sth, cth*sphi, cth*cphi]])
    #Hence platform sensor points with respect to the base coordinate system
    xbar = a[0:3] - bPos
    
    #Hence orientation of platform wrt base
    
    uvw = numpy.zeros(pPos.shape)
    for i in xrange(6):
        uvw[i, :] = numpy.dot(Rzyx, pPos[i, :])
        
    
    L = numpy.sum(numpy.square(xbar + uvw),1)
	
    #In the IK, the leg lengths are the length of the vector (xbar+uvw)
    return numpy.sqrt(L)
    
    

def fk(bPos, pPos, L):  
    
    #newton-raphson
    tol_f = 1e-3;
    tol_a = 1e-3;
    #iteration limits
    maxIters = 1e3
    iterNum = 0
    
    #initial guess position
    # a = [x, y, z, phi, theta, psi] - angles in degrees initially
    #a = [20, 20, 100, 10, 10, 10]
    a = [0, 0, 100, 0, 0, 0]
    a[3:] = [math.radians(x) for x in a[3:]] #convert to radians
    a = numpy.array(a).transpose()
    while iterNum < maxIters:
        iterNum += 1
        
        
        phi = a[3]
        th = a[4]
        psi = a[5]
        #Must translate platform coordinates into base coordinate system
        #Calculate rotation matrix elements
        cphi = math.cos(phi)
        sphi = math.sin(phi)
        cth = math.cos(th)
        sth = math.sin(th)
        cpsi = math.cos(psi)
        spsi = math.sin(psi)   
        #Hence calculate rotation matrix
        #Note that it is a 3-2-1 rotation matrix
        Rzyx = numpy.array([[cpsi*cth, cpsi*sth*sphi - spsi*cphi, cpsi*sth*cphi + spsi*sphi] \
                            ,[spsi*cth, spsi*sth*sphi + cpsi*cphi, spsi*sth*cphi - cpsi*sphi] \
                            , [-sth, cth*sphi, cth*cphi]])
        #Hence platform sensor points with respect to the base coordinate system
        xbar = a[0:3] - bPos
        
        #Hence orientation of platform wrt base
        
        uvw = numpy.zeros(pPos.shape)
        for i in range(6):
            uvw[i, :] = numpy.dot(Rzyx, pPos[i, :])
            
        
        l_i = numpy.sum(numpy.square(xbar + uvw),1)
            
        
        
        
        
        
        #Hence find value of objective function
        #The calculated lengths minus the actual length
        f = -1 * (l_i - numpy.square(L))
        sumF = numpy.sum(numpy.abs(f))
        if sumF < tol_f:
            #success!
            print("Converged! Output is in 'a' variable")
            break
        
        #As using the newton-raphson matrix, need the jacobian (/hessian?) matrix
        #Using paper linked above:
        dfda = numpy.zeros((6, 6))
        dfda[:, 0:3] = 2*(xbar + uvw)
        for i in range(6):
            #Numpy * is elementwise multiplication!!
            #Indicing starts at 0!
            #dfda4 is swapped with dfda6 for magic reasons!  
            dfda[i, 5] = 2*(-xbar[i,0]*uvw[i,1] + xbar[i,1]*uvw[i,0]) #dfda4
            dfda[i, 4] = 2*((-xbar[i,0]*cpsi + xbar[i,1]*spsi)*uvw[i,2] \
                            - (pPos[i,0]*cth + pPos[i,1]*sth*sphi)*xbar[i,2]) #dfda5
            dfda[i, 3] = 2*pPos[i, 1]*(numpy.dot(xbar[i,:],Rzyx[:,2])) #dfda
    
        #Hence solve system for delta_{a} - The change in lengths
        delta_a = numpy.linalg.solve(dfda, f)
    
        if abs(numpy.sum(delta_a)) < tol_a:
            print("Small change in lengths -- converged?")
            break
        a = a + delta_a
    
    #for i in xrange(3,6):
    #    a[i] = math.degrees(a[i])
    print("In %d iterations" % (iterNum))
    return a
    
    
def process():   

	#Load S-G platform configuration and convert to numpy arrays
    #from configuration import *
    #from configuration import bAngles, bR, bPos, pAngles, pR, pPos, height, legMin, legMax, A, B
    #import configuration

    #define coord system origin as the center of the bottom plate
    #Find base plate attachment locations
    bAngles = [15, 105, 135, 225, 255, 345]
    bAngles = [math.radians(x) for x in bAngles]
    bR = 50
    bPos = [[bR*math.cos(theta), bR*math.sin(theta), 0] for theta in bAngles]

    #Platform attachment locations
    pAngles = [45, 75, 165, 195, 285, 315]
    pAngles = [math.radians(x) for x in pAngles]
    pR = 50
    pPos = [[pR*math.cos(theta), pR*math.sin(theta), 0] for theta in pAngles]

    height = 100

    legMin = [50]*6
    legMax = [100]*6

    #Base UV joint limits
    A = [math.pi/4]*6
    #Platform ball joint limits
    B = [math.pi/2]*6

    bPos = numpy.array(bPos)
    pPos = numpy.array(pPos)

    #pub = rospy.Publisher('stewart/platform_twist', Twist, qeue_size=100)
    rospy.init_node('forward_kinematics_node')
    rate = rospy.Rate(100)
    iter = 0

    while not rospy.is_shutdown():
            start_time = time.time()
            L = numpy.array([122.759+iter, 122.759, 122.759, 122.759, 122.759, 122.759]).transpose()
            a = fk(bPos, pPos, L)
            print(a)
            print("time :", time.time()-start_time)
            iter = iter + 1
            rate.sleep()
    
    #print ik(bPos, pPos, a)
    #a = numpy.array([0,0,0, 1, 0, 0]).transpose()
    #print ik(bPos, pPos, a)
    
    #Other test
    #lengths = []
    #t = numpy.arange(0, math.pi/6, 0.01)
    #for i in t:
    #    a = numpy.array([0,0,0, i, 0, 0]).transpose()
    #    l = ik(bPos, pPos, a)
    #    lengths.append(l)
    #angle = []
    #for L in lengths:
    #    print "L", L
    #    a = fk(bPos, pPos, L)
    #    angle.append(a[3])
    #plt.plot(t, angle)
    #plt.xlabel('Input Angle (rad)')
    #plt.ylabel('Calculated Angle')
    #plt.show()
    #plt.plot(t, angle-t)
    #plt.xlabel('Input Angle (rad)')
    #plt.ylabel('Error (rad)')
    #plt.show()


if __name__ == "__main__":
    try:
        process()
    except rospy.ROSInterruptException:
        pass

