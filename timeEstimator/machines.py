from math import sqrt, pi,  acos, asin
from .profile import Profil
from .utils import *
import re

class FanucLathe():
    """
        Description :
            FANUC Gcode interpreter for lathe with Y axis support
            This object works as a state machine.
        Usage :
            On each program line, use the interpret(line) to read a program
            line and alter the state.
            Changes will get stored for CSV conversion and analysis later on.
    """
    def __init__(self) -> None:
        #position
        self.posX = 0
        self.posY = 0
        self.posZ = 0
        #cutting params
        self.cuttingSpeed = 0 #m/min
        self.feed = 0 #mm/tour
        self.perRevolutionFeed = True #IS SPEED ? mm/min si false
        self.maxSpeed = 12500 #mm/min
        self.rotation = 0 #1/min
        self.maxRotation = 99999999#G92
        self.isRotationConstant = False #are we in G97 mode (True) or in G96 (False => we use Vc cuttingSpeed to calculate N - the rotation - to get time)
        self.speed = 0 #mm/min #actual speed
        
        
        #current cycle info for data/ouput save
        self.toolName = ""
        self.currentCycle = ""
        self.cycleTime = 0 #current cycle accumulated time
        self.deadCycleTime = 0 #not machining (fast interpolations)
        self.distance = 0
        self.Profil = Profil()
        
        #general interpreting infos
        self.variables = {}
        
        # global data (outup and testting vars)
        self.lineNumber = 0 #the number of the line being interpreted
        self.csvData = [] #to return for web interface data display
        self.globalTime = 0.0 #to return for testing purposes
        self.globalDist = 0.0 #to return for testing purposes
        self.line = ""
        
    def move_and_get_time(self, X, Y, Z, distance, fast = False) -> float:
        """moves the tool to its new position in a linear trajectory. returns the necessary time"""
        
        #=== distance setter ===
        
        dist = abs(distance)
        
        if fast:
            time = dist / self.maxSpeed
            self.speed = self.maxSpeed
            
        elif not fast:
            
            #=== speed setter ===
            #determine the speed depending on the machinning factors, (should use method cf line 48)
            if not self.perRevolutionFeed :
                self.speed = self.feed
            elif self.isRotationConstant:
                self.speed = self.rotation * self.feed
            elif not fast and not self.isRotationConstant:
                D_moyen = X + self.posX
                rot_moyen = 1000 * self.cuttingSpeed / (pi * D_moyen)
                self.rotation = rot_moyen
                if rot_moyen > self.maxRotation : rot_moyen = self.maxRotation
                self.speed = rot_moyen * self.feed
                
            time = dist / self.speed
            
        self.posX, self.posY, self.posZ = X, Y, Z
        #increment global variables for thes tests
        self.globalTime += time*60
        self.globalDist += dist
        self.distance += distance
        return time*60 #return seconds
    
    def determineDistanceFromCurrentPos(self, X : float = 0, Y : float = 0, Z : float = 0, kind : str = "linear", **kwargs) -> float:
        """determine distance from the current lathe's position to the new point"""
        if kind == "linear":
            return sqrt((X-self.posX)**2 + (Y-self.posY)**2 + (Z-self.posZ)**2)
        
        if kind == "circular":
            I = kwargs["I"]
            J = kwargs["J"]
            K = kwargs["K"]
            R = kwargs["R"]
            
            if not I == 0 or not K == 0 or not J ==0:
                if not R == None:
                    #ignonore R by dfault if I or J is set (or both btw)
                    R = None
                    
            if not R: #if we are using I and J to calc our distance
                #then the math begins :
                #determine u and v vectors (to old and new pos FROM the radius center)
                u = (-I + self.posX, -J + self.posY ,-K + self.posZ)
                v = (X - I,Y-J ,Z - K)
                
                #check if valid (determine R and apply 2R > distance)
                # print(u,v, magnitude(u), magnitude(v), self.determineDistanceFromCurrentPos(X,Y,Z))
                if 2 * min(magnitude(u), magnitude(v)) < self.determineDistanceFromCurrentPos(X,Y,Z):
                    raise ValueError("incorrect I and J values in code resulting in an impossible profile, please check yout program or use R")
                
                #determine theta, the angle, always between old and new one
                theta = acos(round(dotProduct(u,v)/(magnitude(u)*magnitude(v)),3))
                dist = theta * magnitude(v) #here, magnitude(u) == magnitude(v) == R, the radius
                return dist
                #determine the distance by multiplying
            elif not R == None:
                #if we using the radius to code the G2/3 interpolation :
                #check if valid (determine R and apply 2R > distance)
                if 2 * R < self.determineDistanceFromCurrentPos(X, Y, Z):
                    
                    #sometimes R is not valid but interpresters (like biglia's one) still goes on, wo instead of raising error, we adjust and say we did so
            
                    print("WARNING ! R was too small and has been adjusted from %.2f to %.2f" % (R, 0.1 + self.determineDistanceFromCurrentPos(X, Y, Z)/2))
                    R = 0.1 + self.determineDistanceFromCurrentPos(X, Y, Z)/2
                #determine theta (cf formula on paper)
                theta = 2 * (asin((self.determineDistanceFromCurrentPos(X, Y, Z)/2)/R))
                dist = theta * R
                return(dist)
            
    def save_csv_data(self, excel_mode = False) -> None:
        """saves csv data AND RESET current operation params WITH VALIDATION INCLUDED HERE , also call before ending the main program in order to save last bits of info in self.scvData"""
        #insert a new entry in the returned csv data and reset the times

        #csvData line format : [Gxx, TXXXX, time it took, line number of the g instruction, (cutting params)]

        # condition to add a new entry :
        # time  > 0
        # new G has been encountered OR we are at the end of the file

        #if time is 0 the wrap thins up here
        if self.cycleTime + self.deadCycleTime == 0 : return None
        
        if not excel_mode : #classic output
            #for now, the cutting params returned will be the median cutting speed in mm/min (self.speed calculated in self.move_and_get_time)
            self.csvData.append([
                self.currentCycle,
                self.toolName,
                round(self.cycleTime + self.deadCycleTime, 2),
                round(self.speed, 1),
                self.lastGLine, #actual line of the last G to save inside csv data, and not the new one
                #add other stuff here in the future
            ])
            # output structure : [Goperation, tool, time, speed (Vf), line num]
            
        elif excel_mode: #destined to make excel modifications
            currentLine = len(self.csvData) + 1
            time = "=(H"+str(currentLine)+"/G"+str(currentLine)+")*60"
            
            if self.perRevolutionFeed and not "G71" in self.currentCycle and not "G72" in self.currentCycle and not "G74" in self.currentCycle and not "G76" in self.currentCycle and not "G0" in self.currentCycle and not "G00" in self.currentCycle:
                if not self.isRotationConstant:
                    D = int((1000*self.cuttingSpeed)/(pi*self.rotation))
                    Vc = int(self.cuttingSpeed)
                    N = "=1000*D" + str(currentLine) + "/(PI()*C"+ str(currentLine)+")"
                    f = self.feed
                    Vf = "=E"+ str(currentLine) +"*F"+ str(currentLine)
                else :
                    D = 0
                    Vc = 0
                    N = self.rotation
                    f = self.feed
                    Vf = "=E"+ str(currentLine) +"*F"+ str(currentLine)
                    
            elif self.currentCycle in ["G71", "G72", "G74", "G76", "G4", "G04"]:
                #needs imrovement later (make profile methods to get those differents params)
                D = 0
                Vc = 0
                N = 0
                f = 0
                Vf = int(self.speed)
                self.distance = 0
                time = round(self.cycleTime + self.deadCycleTime,2)
            else : #if speed is set set directly in mm/min, set params to 0 (cf changelog v1.1 and readme.md) or if g71/72/74/76
                D = 0
                Vc = 0
                N = 0
                f = 0
                Vf = int(self.feed)
                if self.currentCycle in ["G00", "G0"] : Vf = self.maxSpeed
            
            #write down in csvData :
            self.csvData.append([
                self.currentCycle,
                self.toolName,
                D,
                Vc,
                N,
                f,
                Vf,
                round(self.distance,2),
                time,
                self.lastGLine, #actual line of the last G to save inside csv data, and not the new one
                #add other stuff here in the future
            ])

        self.cycleTime, self.deadCycleTime, self.distance = 0, 0, 0 #
    
    def interpret(self, line, excel_mode = False):
        """get a line, interprets it and stores toolname, op type and time for csv indentation in its (the lathe) inernal dataset"""
        
        self.lineNumber += 1
        self.line = line
        
        #retirer les commentaires de la ligne
        line = re.sub("\(.*?\)","",line)
        line = re.sub(r';.*', '', line)
        
        var = getVar(line) #voir s'il y a une variable dans la ligne
        if var:
            self.variables[var[0]] = var[1]
        
        #=====================
        #  G CYCLE GETTER
        #=====================
         
        try :
            G = getParam(line, "G")
            if "G" in line:
                #set new cycle type
                self.save_csv_data(excel_mode=excel_mode)
                self.lastGLine = self.lineNumber #actual line of the last G to save inside csv data, and not the new one
                self.currentCycle = "G" + str(int(G))
        except:
            ... #some times bugged on "GOTO" lines, i should fix this dirty code when i have some time lying around...
            
        #=====================
        #  FEED SPEED GETTER
        #=====================
        
        F = getParam(line, "F")
        
        if not F == None:
            self.feed = F
            
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
                self.rotation = S
                
        #G92 here, maximum rotation speed rate
        if "G92" in line:
            S = getParam(line, "S")
            if S:
                self.maxRotation = S
                
        #G96 tells us we use cutting speed to move the  tool
        if "G96" in line:
            S = getParam(line, "S")
            if S:
                self.isRotationConstant = False
                self.cuttingSpeed = S
                
        #G28 tells to return to reference point
        if "G28" in line :
            self.posX = 0
            self.posY = 0
            self.posZ = 0
            
        #=====================
        # PROFILE DEFINITION
        #=====================
        
        if self.Profil.isDefinitionTakingPlace :
            if "G71" in line: #this means we are in the second G71 line, so we get params from it
                self.Profil.begin = int(getParam(line,"P"))
                self.Profil.end = int(getParam(line, "Q"))
            
            N = getParam(line,"N")
            if not N : #if there is no N in line, getParams returns None so we handle that
                N = int(0)
            else :
                N = int(N)
            #if we are at the end of profile def, we determine everything
            if not N == 0 and N == self.Profil.end:
                self.Profil.isDefinitionTakingPlace = False
                dist = self.Profil.get_mean_Z(self.posZ)
                for i in range(self.Profil.get_number_of_passes()):
                    #======PARAMS GETTER==========
                    X = getParam(line,"X", self.variables)
                    Y = getParam(line,"Y", self.variables)
                    Z = getParam(line, "Z", self.variables)
                    
                    if X == None : X = self.Profil.points[-1][0]
                    if Y == None : Y = self.Profil.points[-1][1]
                    if Z == None : Z = self.Profil.points[-1][2]
                    #also make fasts passes
                    self.cycleTime += self.move_and_get_time(X , Y, Z, dist, fast=True)
                    #move and makes the passes
                    self.cycleTime += self.move_and_get_time(X , Y, Z, dist, fast = False)
                    #SAVE PROCESS FOR G71
                    self.currentCycle = "G71"
                self.save_csv_data(excel_mode=excel_mode)
                
                self.Profil = Profil()
            else:
                #======PARAMS GETTER==========
                X = getParam(line, "X", self.variables)
                Y = getParam(line, "Y", self.variables)
                Z = getParam(line, "Z", self.variables)
                        
                if X == None :
                    if len(self.Profil.points) >= 1:
                        X = self.Profil.points[-1][0]
                    else:
                        X = self.posX
                
                if Y == None :
                    if len(self.Profil.points) >= 1:
                        Y = self.Profil.points[-1][1]
                    else:
                        Y = self.posY
                        
                if Z == None :
                    if len(self.Profil.points) >= 1:
                        Z = self.Profil.points[-1][2]
                    else:
                        Z = self.posZ
                
                self.Profil.points.append((X, Y, Z))
            
            return #passer a la ligne suivante sans interpreter le reste
        
        #=====================
        # G CODES INTERPRETER
        #=====================
        
       
            
        #and now, we cover all G codes possibilities...
        
        #-----------------------------
        # Machinning cycles G getters
        #-----------------------------
        
        X = getParam(line, "X", self.variables)
        Y = getParam(line, "Y", self.variables)
        Z = getParam(line, "Z", self.variables)
        U = getParam(line, "U", self.variables)
        V = getParam(line, "V", self.variables)
        W = getParam(line, "W", self.variables)
            
        #=====position setter =======
        
        if X == None: X = self.posX
        if not U : U = 0
        X += U
        
        if Y == None : Y = self.posY
        if not V : V = 0
        Y += V
        
        if Z == None: Z = self.posZ
        if not W : W = 0
        Z += W
            
        #G0 : fast linear interpolation
        if self.currentCycle in ["G00", "G0"]:
            dist = self.determineDistanceFromCurrentPos(X, Y, Z, "linear")
            self.deadCycleTime += self.move_and_get_time(X, Y, Z, dist, fast = True) #add the cycle time to the current time cycle
        
        #G01 : linear mouvement
        if self.currentCycle in ["G01", "G1"]:
            dist = self.determineDistanceFromCurrentPos(X, Y, Z, "linear")
            self.cycleTime += self.move_and_get_time(X, Y, Z, dist, fast = False) #add the cycle time to the current time cycle
            
        #G02 and G03 (time is bascaly the same for both Gs)
        if self.currentCycle in ["G02", "G2", "G03", "G3"]:
            i = getParam(line, "I", self.variables)
            j = getParam(line, "j", self.variables)
            k = getParam(line, "K", self.variables)
            r = getParam(line, "R", self.variables)
            
            if not i : i = 0
            if not j : j = 0
            if not k : k = 0
            if not r : r = 0
            
            if i or j or k or r:
                dist = self.determineDistanceFromCurrentPos(X, Y, Z, "circular", I = i, J = j, K = k, R = r)
                self.cycleTime += self.move_and_get_time(X, Y, Z, dist, fast = False)
                
        #G4 temporisation support
        if self.currentCycle in ["G4", "G04"]:
            #in biglia the temp param is U
            U = getParam(line,"U")
            if U :
                self.cycleTime += U
                #add to global time for test manually as we are not moving the tool
                self.globalTime += U
        
        #G71, G72 Stock removal turning/facing => this is an approx given at +-5seconds
        if self.currentCycle in ["G71", "G72"]:
            if "G71" in line or "G72" in line:
                self.Profil.isDefinitionTakingPlace = True
                self.Profil.deltaPasses = getParam(line, "U")
            
            
        if self.currentCycle in ["G74"] :
            #the peck drilling, we estimate the peck to be negligeable, if they are not, then please review your Gcode because you are not doing it right
            Z = getParam(line, "Z")
            if not Z == None:
                X, Y = self.posX, self.posY
                dist = abs(self.posZ-Z)
                self.cycleTime += self.move_and_get_time(X, Y, Z, dist, fast = False)
        
        if self.currentCycle in ["G76"] :
            #this is threading cycle
            #We get P (usually in the firtst line so we set it as an attribute to acces it later) and then Z. Once both are set, we execute the moving
            P = getParam(line, "P", self.variables, True)
            Z = getParam(line, "Z", self.variables)
            if P and len(P) > 3 : self.P = int(P[:2]) #i use len(P) > 3 to eliminate the P i don't want on the second line when using G76
            if Z:
                delta_Z = self.posZ - Z
                for i in range(self.P):
                    self.cycleTime += self.move_and_get_time(self.posX, self.posY, self.posZ, delta_Z, fast=True)
                    self.cycleTime += self.move_and_get_time(self.posX, self.posY, self.posZ, delta_Z, fast=False)
                self.save_csv_data(excel_mode=excel_mode)
                self.P = None
            
        #=====================
        #  TOOL NAME GETTER 
        #=====================
        
        try:
            T = getParam(line, "T", as_string=True)
            if T != None:
                T = "T" + str(T).replace(".","") #T0101 for exemple
                
                #====== RESET DATA FOR NEXT TOOL ======
                self.toolName = T
        except:
            ... #some times bugged on "GOTO" lines
