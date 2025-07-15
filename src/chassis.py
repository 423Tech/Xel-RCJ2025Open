import math
from ReasonData.config import QkJson
import time


class Car:
    def __init__(self,SetMotorFunc,GetYaw=None):
        self.SetMotorFunc = SetMotorFunc
        self.GetYaw = GetYaw

        self.Kp = 0.8
        
        self.cfg = QkJson()
        self.SaveData = self.cfg.read("Advanced","Database")
        if self.SaveData:
            from ReasonData.data import Outputs
            self.DataBase = Outputs()
        self.SaveLog = self.cfg.read("Advanced","logger")
        if self.SaveLog:
            from ReasonData import logger
            self.logger = logger
    
    def SetMotor(self,Speed1,Speed2,Speed3,Speed4):
        self.SetMotorFunc(int(Speed1), int(Speed2), int(Speed3), int(Speed4))
    
    def SetKp(self,Kp):
        self.Kp = Kp
    
    def Compass(self):
        return self.GetYaw() if self.GetYaw is not None else None

    def Go(self,SpeedX,SpeedY,SpeedZ):
        '''
        stand for a vector movement (SpeedX,SpeedY,SpeedZ)
        '''
        Speed1 = SpeedX + SpeedY + SpeedZ
        Speed2 = SpeedY - SpeedX + SpeedZ
        Speed3 = SpeedY - SpeedX - SpeedZ
        Speed4 = SpeedX + SpeedY - SpeedZ
        if self.SaveData:
            self.DataBase.SetOutput(Speed1,Speed2,Speed3,Speed4)
        self.SetMotor(Speed1, Speed2, Speed3, Speed4)
    
    def GoA(self,FacingAngle,MovingAngle,Speed,Kp=None):
        if self.GetYaw is None:
            return False
        Yaw = self.GetYaw()
        rad = math.radians(MovingAngle+360-Yaw)
        SpeedX = int(math.sin(rad) * Speed)
        SpeedY = int(math.cos(rad) * Speed)
        if Kp is not None:
            self.GoV(SpeedX,SpeedY,FacingAngle, Kp)
        else:
            self.GoV(SpeedX,SpeedY,FacingAngle)
        

    def GoV(self,SpeedX,SpeedY,FacingAngle,Kp=None):
        '''
        stand for a vector movement (SpeedX,SpeedY,SpeedZ)
        '''
        if self.GetYaw is None:
            return False
        Yaw = self.GetYaw()
        Error = Yaw - FacingAngle
        Error = (Error + 180) % 360 - 180  # Normalize to [-180, 180]
        if Kp is None:
            Kp = self.Kp
        SpeedZ = - Error * Kp
        self.Go(SpeedX, SpeedY, SpeedZ)
    
    def GoX(self,Angle,Speed):
        if self.GetYaw is None:
            return False
        self.GoA(Angle,90,Speed)
   
    def GoY(self,Angle,Speed,Kp=None):
        if self.GetYaw is None:
            return False
        self.GoA(Angle,0,Speed,Kp)

    def GoZ(self,Angle,Kp=None):
        if self.GetYaw is None:
            return False
        self.GoA(Angle,0,0,Kp)

    def GoZSpeed(self,Speed): #自转
        self.Go(0,0,Speed)
    
    def Turn(self,Angle,AimSpeed,Kp=None):

        while True:
            Error = self.GetYaw() - Angle
            Error = (Error + 180) % 360 - 180

            Speed = AimSpeed
            
            if Error < -5:
                self.GoZSpeed(Speed)
            elif Error > 5:
                Speed = -Speed
                self.GoZSpeed(Speed)
            else:
                break
            print(Error,Speed)
            time.sleep(0.03)
            
    def stop(self):
        self.SetMotor(0,0,0,0)


class Peripherals:
    def __init__(self,IOFunc):
        self.SetIO = IOFunc
        from ReasonData import QkJson
        self.cfg = QkJson()
        from ReasonData import logger
        self.logger = logger
        self.ElecMagnetIO = self.cfg.read("Ports","ElecMagnet")
        self.DribbleIO = self.cfg.read("Ports","Dribble")
        self.SetIO(self.ElecMagnetIO,1)

    def ShootBall(self):
        self.SetIO(self.ElecMagnetIO,0)
        time.sleep(0.3)
        self.SetIO(self.ElecMagnetIO,1)
        self.logger.info("Used ElecMagnet")

    def DribbleBall(self):
        '''
        Warning: This function will be unused.
        '''
        self.SetIO(self.DribbleIO,1)
        # self.logger.info("Start Dribble")

    def StopDribble(self):
        '''
        Warning: This function will be unused.
        '''
        self.SetIO(self.DribbleIO,0)
        # self.logger.info("Stop Dribble")

    def Dribble(self,Status:bool):
        if Status:
            self.SetIO(self.DribbleIO,1)
        else:
            self.SetIO(self.DribbleIO,0)
        self.logger.info("Dribble set to %s" % ("ON" if Status else "OFF"))