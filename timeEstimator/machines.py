from math import sqrt, pi, cos, acos, asin
from .utils import *
import re

class Biglia():
    """go inside machine.py to configure the lathe to correspond to your lathe's specifications"""
    def __init__(self) -> None:
        self.position = (0,0) # mm x,z
        self.cuttingSpeed = 0 #m/min
        self.feed = 0 #mm/tour
        self.perRevolutionFeed = True #IS SPEED ? mm/min si false
        self.maxSpeed = 12500 #mm/min
        self.rotation = 0 #1/min
        self.maxRotation = 5000#G92
        self.isRotationConstant = False #are we in G97 mode (True) or in G96 (False => we use Vc cuttingSpeed to calculate N - the rotation - to get time)
        self.toolName = ""
        
        self.isProfileDefinitionTakingPlace = False # if we are in a cycle that requires a definition of a profile
        self.profileLenght = 0 #we also store the profile lenght
        
        self.variables = {}
        
        self.currentCycle = ""
        self.cycleTime = 0 #current cycle accumulated time
        self.deadCycleTime = 0 #not machining (fast interpolations)
        
        self.csvData = {} #to return at the end later on
        self.globalTime = 0.0  #to return for testing purpuses
    
    def move_and_get_time(self, X,Z, distance, fast = False) -> float:
        """moves the tool to its new position in a linear trajectory. returns the necessary time"""

        #determine the speed depending on the machinning factors
            
        #=== speed setter ===
        
        if not self.perRevolutionFeed :
            speed = self.feed
        elif self.isRotationConstant:
            speed = self.rotation * self.feed
        elif not fast and not self.isRotationConstant:
            D_moyen = X + self.position[0]
            rot_moyen = 1000 * self.cuttingSpeed / (pi * D_moyen)
            if rot_moyen > self.maxRotation : rot_moyen = self.maxRotation
            speed = rot_moyen * self.feed
                
        #=== distance setter ===
            
        #dist = sqrt((X-self.position[0])**2 + (Z-self.position[1])**2)
        dist = distance
        
        if fast:
            time = dist / self.maxSpeed
        elif not fast:
            time = dist / speed
            
        self.position = (X,Z)
        self.globalTime += time*60
        return time*60 #return seconds
    
    def determineDistanceFromCurrentPos(self, X : float = 0, Z : float = 0, kind : str = "linear", *args, **kwargs) -> float:
        """determine distance from the current lathe's position to the new point"""
        if kind == "linear":
            return sqrt((X-self.position[0])**2 + (Z-self.position[1])**2)
        
        if kind == "circular":
            I = kwargs["I"]
            J = kwargs["J"]
            R = kwargs["R"]
            
            if I or J:
                if not R == None:
                    #ignonore R by dfault if I or J is set (or both btw)
                    R = None
                    
            if not R: #if we are using I and J to calc our distance
                #set vars to floats and 0 if not set
                if I and not J :
                    J = 0
                    I = float(I[1:])
                elif J and not I :
                    I = 0
                    J = float(J[1:])
                elif I and J:
                    I = float(I[1:])
                    J = float(J[1:])
                elif not I and not J: return
            
                #then the math begins :
                #determine u and v vectors (to old and new pos)
                u = (-J + self.position[0], -I + self.position[1])
                v = (X - J, Z - I)
                #check if valid (determine R and apply 2R > distance)
                if 2 * min(magnitude(u), magnitude(v)) < self.determineDistanceFromCurrentPos(X,Z):
                    raise ValueError("incorrect I and J values in code resulting in an impossible profile, please check yout program or use R")
                
                #determine theta, the angle, always between old and new one
                theta = acos(dotProduct(u,v)/(magnitude(u)*magnitude(v)))
                dist = theta * magnitude(v) #here, magnitude(u) == magnitude(v) == R, the radius
                return dist
                #determine the distance by multiplying
            elif not R == None:
                #if we using the radius to code the G2/3 interpolation :
                R = float(R[1:])
                #check if valid (determine R and apply 2R > distance)
                if 2 * R < self.determineDistanceFromCurrentPos(X,Z):
                    raise ValueError("you use a too small value of R in your program, resulting in an impossible profile")
                #determine theta (cf formula on paper)
                theta = 2 * (asin((self.determineDistanceFromCurrentPos(X,Z)/2)/R))
                dist = theta * R
                return(dist)
    def sendDataAndReset(self) -> None:
        """returns all the current cycle data for logging and reset the cycle time"""
        if (self.cycleTime == 0 and self.deadCycleTime == 0) or len(self.toolName) <= 1:
            return
        #print(self.toolName + " => " + str(self.cycleTime + self.deadCycleTime) + " seconds")
        self.cycleTime = 0
        self.deadCycleTime = 0
        return
    
    def interpret(self, line):
        """get a line, interprets it and stores toolname, op type and time for csv indentation in its (the lathe) inernal dataset"""
        
        line = re.sub("\(.*?\)","",line)
        var = getVar(line)
        if var:
            self.variables[var[0]] = var[1]
        
        #\/ \/ \/ \/ to treat variables : should add a dict "self.varibles" stocking vars id "[]" is detected in a non G line and then self.readVar() is called if a "[]" is detected in a G line\/ \/ \/ \/ 
            
        #=====================
        #   TOOL NAME GETTER 
        #=====================
        
        T = getParam(line, "T")
        
        if T != None:
            self.toolName = T
            #if this is a new tool, we return the tool times and procced to treat the next
            #HERE SHOUL ADD A NEW ENTRY TO THE DATA DICT
            
        #=====================
        #  FEED SPEED GETTER
        #=====================
        
        F = getParam(line, "F")
        
        if F != None and F != "":
            self.feed = float(F[1:])
        
        #=====================
        # G CODES INTERPRETER
        #=====================
        
        #we get the current cycle so we can spread it across lines
        G = getParam(line, "G")
        if G != None and G != self.currentCycle and "G" in G:
            self.currentCycle = G
            
        #and now, we cover all G codes possibilities...
        
        #-----------------------------
        #Cutting speeds G getters
        #-----------------------------
        
        #look for G95 or G94 to determine thje state of self.perRevoltionFeed (true id mm/tr and false if mm/min)
        if "G95" in line or "G99" in line:
            self.perRevolutionFeed = True
        if "G94" in line or "G98" in line:
            self.perRevolutionFeed = False
        
        #G97 says we use constant rotation speed, thus using cuuting speed useless
        if "G97" in line:
            #Definition de vitesse de rotation constante
            S = getParam(line, "S")
            if S:
                self.isRotationConstant = True
                self.rotation = float(S[1:])
                
        #G92 here, maximum rotation speed rate
        if "G92" in line:
            S = getParam(line, "S")
            if S:
                self.maxRotation = float(S[1:])
                
        #G96 tells us we use cutting speed to move the  tool
        if "G96" in line:
            S = getParam(line, "S")
            if S:
                self.isRotationConstant = False
                self.cuttingSpeed = float(S[1:])
        
        #-----------------------------
        # Machinning cycles G getters
        #-----------------------------
        
        X = getParam(line, "X", self.variables)
        Z = getParam(line, "Z", self.variables)
        U = getParam(line, "U", self.variables)
        W = getParam(line, "W", self.variables)
            
        #=====position setter =======
        
        #a little dirty but who cares really ? it was a quick fix. maybe do it a little better and rework the "param getting" when i have the time
        if not X and U:
            X = self.position[0] + float(U[1:])
        elif not X and not U:
            X = self.position[0]
        elif X:
            X = float(X[1:].replace(",",""))
            
            
        if not Z and W:
            Z = self.position[1] + float(W[1:])
        elif Z and not W:
            Z = float(Z[1:].replace(",",""))
        elif not Z and not W:
            Z = self.position[1]
            
        #G0 : fast linear interpolation
        if self.currentCycle in ["G00", "G0"]:
            dist = self.determineDistanceFromCurrentPos(X,Z,"linear")
            self.deadCycleTime += self.move_and_get_time(X,Z, dist,fast = True) #add the cycle time to the current time cycle
            
        #G01 : linear mouvement
        if self.currentCycle in ["G01", "G1"]:
            dist = self.determineDistanceFromCurrentPos(X,Z,"linear")
            self.cycleTime += self.move_and_get_time(X,Z, dist,fast = False) #add the cycle time to the current time cycle
            
        #G02 and G03 (time is bascaly the same lol)
        if self.currentCycle in ["G02", "G2", "G03", "G3"]:
            i = getParam(line, "I")
            j = getParam(line, "J")
            r = getParam(line, "R")
            
            dist = self.determineDistanceFromCurrentPos(X, Z, "circular", I = i, J = j, R = r)
            print(X,Z,i,j,r,dist)
            if i or j or r:
                self.cycleTime += self.move_and_get_time(X,Z, dist, fast = False)