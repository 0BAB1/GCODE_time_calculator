from math import floor

class Profil():
    def __init__(self) -> None:
        self.isDefinitionTakingPlace : bool = False
        self.points = [] 
        # [(0, 0), (20.0, 0), (20.0, -20.0), (15.0, -20.0), (15.0, -10.0), (10.0, -10.0), (5.0, -5.0)]
        self.begin : int
        self.end : int
        self.deltaPasses : float # is used to get the number of passes
        
    def get_mean_Z(self, initialZ : float) -> float:
        """returns the means ponderated Z for a G71 cycle"""
        totalX, totalZ = 0 , 0
        for i in range(len(self.points)-1):
            DX = abs(self.points[i+1][0] - self.points[i][0])
            DZ = abs(self.points[i+1][1] - initialZ)
            totalX += abs(DX)
            totalZ += abs(DZ*DX)
            
            print(self.points[i][1] ,DZ, totalZ, DX)
        
        print("total : ", totalZ, totalX, "mean : ", totalZ/totalX)
        #after verification : function looks good and problem comes from initalZ and is interprestation
        return abs(totalZ/totalX)
                        
    def get_number_of_passes(self) -> int:
        """divides total height by delata passes, returns the floore number of passes"""
        #get the total Z thckness
        lowest = 99999999
        highest = -999999
        for point in self.points :
            if point[0] < lowest : lowest = point[0]
            if point [0] > highest : highest = point[0]
        
        return floor((highest - lowest)/self.deltaPasses)
        