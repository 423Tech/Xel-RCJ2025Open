import math
import time
import threading

from ReasonData import QkJson, logger
cfg = QkJson()

from chassis import Car,Peripherals
from headunit import Lidar,ArisuIntelligence
ArisuCam = ArisuIntelligence()
from ReasonBeacon import MisakaNetwork
Beacon = MisakaNetwork()
if cfg.read("model","Bit") == "AB":
    from arisbit import ArisBit
    Bits = ArisBit()
    lidar = Lidar(Bits.GetYaw)
    chassis = Car(Bits.SetMotor,Bits.GetYaw)
    compass = Bits.GetYaw
    peripheral = Peripherals(Bits.SetIO)
    logger.info("Arisu Bit loaded.")
else:
    logger.error("None Bit Model found.")
    raise ImportError("None Bit Model found.")

Dribblingdistance = 9 # Distance of ball

# Warned Flags
WarnedLidar = False

# Values for Connection
SendstatusThreadFuncStarted = False
PeerstatusThreadFuncStarted = False
BallFlag = [0,0]
PeerPosition = [1024,1024]

#Math Methods
def GetBallDistance():
    '''
    ### Get the Distance of the ball
    #### Returns:
        (ballX, ballY, DistanceOfBall)
    '''
    bx, by = GetBallPos()
    x, y, _ = GetPos()
    return (bx, by ,math.sqrt((bx - x) ** 2 + (by - y) ** 2))

# Communicate Functions
def BallOwner():# function for judging whether catch the ball
    '''
    ### function for judging whether catch the ball
    #### no return value, this function will change the global variable `BallFlag`
    '''
    global BallFlag
    BallX, BallY = GetBallPos()
    if [BallX,BallY] == [1207,1207]:
        BallFlag[0] = 1
    else:
        BallFlag[0] = 0
    logger.info("BallFlag Satus: %s"%BallFlag)

def SendStatusThreadFunc(): # send role and the status of the ball
    '''
    ### Warning: This function can't be used directly in the main thread
    ### use `Sendstatus()` instead
    '''
    while (1):
        SelfPosition = GetPos()
        try:
            # make sure all the values are integer
            ball_self = int(BallFlag[0]) if isinstance(BallFlag[0], (int, float, str)) else 0
            pos_x = int(SelfPosition[0])
            pos_y = int(SelfPosition[1])
            msg = f"BallSelf:{ball_self};PositionX:{pos_x};PositionY:{pos_y}"
            Beacon.Send(msg)
            logger.success(f"Sented message: {msg}")  # Debug message
        except Exception as e:
            logger.error(f"Send error: {e}")
            raise e
        time.sleep(0.03) # in case too fast

def SendStatus():
    '''
    ### Function for starting Send Status Thread
    #### return `True` if the Thread is already started
    '''
    global SendstatusThreadFuncStarted
    if not SendstatusThreadFuncStarted:
        SendstatusThread = threading.Thread(target=SendStatusThreadFunc)
        SendstatusThread.daemon = True  # Set as a daemon thread, will auto finished after the main thread finished
        SendstatusThread.start()
        SendstatusThreadFuncStarted = True
    return True

def PeerStatusThreadFunc():
    '''
    ### Warning: This function can't be used directly in the main thread
    ### use `Peerstatus()` instead
    '''
    BallOwner() # Update the Status of catching the ball
    global BallFlag,PeerPosition
    while (1):
        MessageCache = Beacon.MessageCache
        if MessageCache == None:
            logger.error("No Conncted Message")
            time.sleep(1)
        if MessageCache:
            try:
                PeerPositionX, PeerPositionY = 1024, 1024  # Default Value
                for part in MessageCache.split(";"):
                    if part.startswith("BallSelf:"):
                        BallFlag[1] = int(part.split(":")[1])  # convert into int
                    if part.startswith("PositionX:"):
                        PeerPositionX = int(float(part.split(":")[1]))  # process float number
                    if part.startswith("PositionY:"):
                        PeerPositionY = int(float(part.split(":")[1]))  # process float number
                PeerPosition = [PeerPositionX, PeerPositionY]
            except Exception as e:
                BallFlag = [0, 0]
                PeerPosition = [1024, 1024]
                logger.error(f"Failed to parse message '{MessageCache}': {e}")
        time.sleep(0.02)

def PeerStatus():# Trun the Prase Thread On
    '''
    ### Function for starting Prase Status Thread
    #### return `True` if the Thread is already started
    #### This thread will update the BallFlag
    '''
    global PeerstatusThreadFuncStarted
    if not PeerstatusThreadFuncStarted:
        PeerstatusThread = threading.Thread(target=PeerStatusThreadFunc)
        PeerstatusThread.daemon = True  # 设置为守护线程，主线程结束时自动结束
        PeerstatusThread.start()
        PeerstatusThreadFuncStarted = True

def StartConncetion():
    '''
    ### Function for starting Send&Prase Status Thread
    '''
    if not PeerstatusThreadFuncStarted and not SendstatusThreadFuncStarted:
        SendStatus()
        PeerStatus()
    else:
        pass


def EnemyPos():
    '''
    ### Function for giving a relative position of enemy without peer
    #### Returns:
        [0,20] : If founded
        [1024,1024] : If not founded
    '''
    P_Pos = PeerPosition
    Px = P_Pos[0]
    CPos = ArisuCam.GetChassisPos()
    EPos = []
    if len(CPos) >= 1:
        for i in range(len(CPos)):
            x = CPos[i][0]
            rrX = abs(Px-x)
            if rrX < 5 :
                del CPos[i]
            EPos = CPos
        return EPos
    else:
        logger.success("No Enemy in vision")
        return [1024,1024]

def SeeEnemyPosition():# Get the absolute position of enemy's chassis
    '''
    ### Function for getting the absolute position of enemy's chassis
    #### Returns:
        [0,20] : If founded
        [1024,1024] : If not founded
    '''
    EPos = EnemyPos()
    if len(EPos) < 1 or EPos == [1024,1024]:
        # delete self & not founded conditions
        return [1024,1024]
    else:
        min_distance = 10000
        for i in range(len(EPos)):
            x1, y1 = EPos[i][:2]
            distance = math.sqrt((x1) ** 2 + (y1) ** 2)
            if distance < min_distance:
                min_distance = distance
                EPos = EPos[i][:2]
                logger.info("See Enemy at: "%EPos)
                return EPos

# Cacluate Methods
def roundThresholdJudger(iValue, iRound, iMiddleValue, iOffset):
    iValue = iValue % iRound
    
    iLowerThreshold = (iMiddleValue - iOffset) % iRound
    iUpperThreshold = (iMiddleValue + iOffset) % iRound

    if iLowerThreshold <= iUpperThreshold:
        return iLowerThreshold <= iValue <= iUpperThreshold

    else:
        return iValue >= iLowerThreshold or iValue <= iUpperThreshold

def FindNearstAngle(arr, target):
    """
    ### Function for Find a nearst value in given list
    #### Args:
        arr: a list of angles, e.g: [180,20,10]
        Target: a target number

    #### Returns:
        `mapped_value`
    """
    return min(arr, key=lambda x: abs(x - target))

def LinearMap(value, input_range, output_range):
    """
    #### Args:
        value: value need to be mapped
        input_range: input span (min, max)
        output_range: output span (min, max)
    
    #### Returns:
        mapped_value: output value
    """
    input_min, input_max = input_range
    output_min, output_max = output_range
    input_span = input_max - input_min
    output_span = output_max - output_min
    scaled_value = (value - input_min) / input_span
    mapped_value = output_min + (scaled_value * output_span)
    return mapped_value

#Value Methods
def GetBallPos():
    '''
    ### retrun a relative position of the ball
    #### Returns:
        if founded: [20,20]
        if not founded: [0,0]
    '''
    return ArisuCam.GetBallPos()

def GetBallAngle():
    '''
    ### retrun a angle of the ball (Degree)
    #### Returns:
        e.g: 90
    '''
    ballX,ballY = ArisuCam.GetBallPos()
    if ballY == 0:
        return 0
    try:
        if -int(math.degrees(math.atan2(ballY,ballX)) - 90) < 0:
            ballRltAngle = -int(math.degrees(math.atan2(ballY,ballX)) - 90) + 360
        else:
            ballRltAngle = -int(math.degrees(math.atan2(ballY,ballX)) - 90)
        return ballRltAngle
    except ZeroDivisionError:
        return 0
    
def AbsBallAngle():
    '''
    ### retrun a absolute angle of the ball
    #### Returns:
        e.g: 20
    '''
    BallAngleCache = GetBallAngle() + compass()
    if BallAngleCache > 360:
        return BallAngleCache - 360
    else:
        return BallAngleCache

def GetDistance() -> list[int,int,int]:
    '''
    ### Get the raw data of lidar
    #### returns:
        e.g: [100,200,100,200]
        Represent: [FrontDistance, RightDistance, BackDistance, LeftDistance]
    '''
    return lidar.GetDists()

def GetPos() -> list[int,int]:
    '''
    ### Get the absolute Position
    #### returns:
        e.g: [100,200,100]
        Represent: [X(cm),Y(cm),YawAngle(˚)]
    '''
    global WarnedLidar
    Distance = GetDistance()
    if Distance == [0,0,0,0] and not WarnedLidar:
        WarnedLidar = True
        logger.error("Lidar Not Started")
        time.sleep(3)
        return [0,0,compass()]
    if WarnedLidar and Distance != [0,0,0,0]:
        WarnedLidar = False
        logger.success("Lidar Started")
    k = 10
    if Distance[0]+Distance[2] < (cfg.read("Position","Height"))*k:
        if Distance[0] > Distance[2]:
            Y = cfg.read("Position","Height")*k/2 - Distance[0]
        else:
            Y = Distance[2] - cfg.read("Position","Height")*k/2
    else:
        Y = ((cfg.read("Position","Height")*k/2 - Distance[0]) + (Distance[2] - cfg.read("Position","Height")*k/2))/2
    if Distance[1]+Distance[3] < (cfg.read("Position","Width") - 50)*k:
        if Distance[1] > Distance[3]:
            X = -(cfg.read("Position","Width")*k/2 - Distance[1])
        else:
            X = -(Distance[3] - cfg.read("Position","Width")*k/2)
    else:
        X = -((cfg.read("Position","Width")*k/2 - Distance[1]) + (Distance[3] - cfg.read("Position","Width")*k/2))/2
    return [X/10,Y/10,compass()]

def AbsBallPos():
    '''
    ### retrun a absolute position of the ball
    #### Returns:
        [20,20]
    '''
    ballX,ballY = ArisuCam.GetBallPos()
    if [ballX,ballY] == [0,0]:
        return [1024,1024] # if Can't found the ball return [1024,1024]
    if ballX == 0 and 0 < ballY <= 9:
        return [1207,1207] # if found the ball return [1207,1207]
    SelfX,SelfY,SelfZ = GetPos()
    ballDistance = math.sqrt(ballX**2 + ballY**2)
    if ballY == 0:
        ballRltAngle = 0
    try:
        ballRltAngle =  -int(math.degrees(math.atan2(ballY,ballX)) - 90)
    except ZeroDivisionError:
        ballRltAngle =  0
    ballAbsAngle = (ballRltAngle + SelfZ)%360
    if ballAbsAngle > 180:
        k = -1
    else:
        k = 1
    AbsBallPositon = [
        ballDistance * math.sin(math.radians(ballAbsAngle)) + SelfX,
        ballDistance * math.cos(math.radians(ballAbsAngle)) + SelfY
        ]
    return AbsBallPositon

def AbsChassisPos():
    '''
    ### retrun a absolute position list of the Chassises
    #### Returns:
        [
        [xPositon1, yPosition1, Chassis1Distance, Chassis1AbsAngle],
        [xPositon2, yPosition2, Chassis2Distance, Chassis2AbsAngle],
        etc
        ]
    '''
    ChassisRawList = ArisuCam.GetChassisPos()
    SelfX,SelfY,SelfZ = GetPos()
    OutputDistanceList = []
    for c in ChassisRawList:
        cDistance = math.sqrt(c[0]**2 + c[1]**2)
        if c[1] == 0:
            ChassisRltAngle = 0
        try:
            ChassisRltAngle =  -int(math.degrees(math.atan2(c[0],c[1])) - 90)
        except ZeroDivisionError:
            ChassisRltAngle =  0
        ChassisAngleAngle = ChassisRltAngle + SelfZ
        if ChassisAngleAngle > 360:
            ChassisAbsAngle = ChassisAngleAngle - 360
        else:
            ChassisAbsAngle = ChassisAngleAngle
        AbsChassisCache = [
            cDistance * math.cos(math.radians(ChassisAbsAngle)) + SelfX,
            cDistance * math.sin(math.radians(ChassisAbsAngle)) + SelfY,
            cDistance,
            ChassisAngleAngle
            ]
        OutputDistanceList.append(AbsChassisCache)
    return OutputDistanceList

def getChassisAngle():

    '''
    ### retrun a list of the relative angle of the chassis
    #### Returns
        [Angle1,Angle2,Angle3,etc]
    '''
    ChassisRawList = ArisuCam.GetChassisPos()
    ChassisAngleList = []
    for c in ChassisRawList:
        if c[1] == 0:
            return 0
        try:
            if -int(math.degrees(math.atan2(c[1],c[0])) - 90) < 0:
                ChassisRltAngle = -int(math.degrees(math.atan2(c[1],c[0])) - 90) + 360
            else:
                ChassisRltAngle = -int(math.degrees(math.atan2(c[1],c[0])) - 90)
            ChassisAngleList.append(ChassisRltAngle)
        except ZeroDivisionError:
            ChassisAngleList.append(0)
    return ChassisAngleList

def AbsChassisAngle():
    '''
    ##### retrun a list of the absolute angles of the chassis
    #### Returns
        [Angle1,Angle2,Angle3,etc]
    '''
    OutputAngles = []
    CompassCache = compass()
    for i in getChassisAngle():
        ChassisAngleCache = i + CompassCache
        if ChassisAngleCache > 360:
            OutputAngles.append(int(ChassisAngleCache)%360)
        else:
            OutputAngles.append(int(ChassisAngleCache))
    return OutputAngles

#Operate models
def Cover2Start():
    global bCovered
    if GetDistance()[0] < 10 or bCovered:
        bCovered = True
        return True
    else:
        bCovered = False
        return False
    
def AvoidOutOfRange(InputPos:list[int,int,int]) -> list[int,int,int]:
    InputX,InputY,InputZ = InputPos
    if InputX > 0:
        kX = 1
    else:
        kX = -1
    if InputY > 0:
        kY = 1
    else:
        kY = -1
    if abs(InputX) > (cfg.read("Border","0")[0]):
        OutX = (cfg.read("Border","0")[0])*kX
    else:
        OutX = InputX
    if abs(InputY) > (cfg.read("Border","0")[1]):
        OutY = (cfg.read("Border","0")[1])*kY
    else:
        OutY = InputY
    OutZ = abs(InputZ%360)
    logger.success("Fixed Position: [%s,%s,%s]"%(OutX,OutY,OutZ))
    return [OutX,OutY,OutZ]
    
def Local2Angle(lAimPos:list[int,int]) -> int:
    '''
    lAimPos 一个坐标 示例：[0,0]
    '''
    iAimX = lAimPos[0]
    iAimY = lAimPos[1]
    iLocX = GetPos()[0]
    iLocY = GetPos()[1]
    iDeltaX = iAimX - iLocX
    iDeltaY = iAimY - iLocY
    try:
        iDeltaAngle = -math.degrees(math.atan(iDeltaX/iDeltaY))
    except:
        if iDeltaX > 0:
            iDeltaAngle = -90
        else:
            iDeltaAngle = 90
    return int(iDeltaAngle)

def Pos2Angle(lInputPos:list[int,int],lAimPos:list[int,int]) -> int:
    '''
    lInputPos 输入坐标
    lAimPos 目标坐标 示例：[0,0]
    '''
    iAimX = lAimPos[0]
    iAimY = lAimPos[1]
    iLocX = lInputPos[0]
    iLocY = lInputPos[1]
    iDeltaX = iAimX - iLocX
    iDeltaY = iAimY - iLocY
    iDeltaAngle = math.degrees(math.atan2(iDeltaY,iDeltaX))
    return int(iDeltaAngle)

def Pos2Pos(lAimPos:list[int,int,int], A2O:bool | None = False, SpeedRatio:int | None = None,Speed:int | None = None) -> int:
    '''
    iFacingAngle 移动时面对的方向 0~360
    lAimPos 目标坐标位置 如[0,0] 距离越近速度越小
    A2O 是否开启自动避障 默认True
    '''
    iAimX,iAimY,iAimZ = AvoidOutOfRange(lAimPos)
    iLocX,iLocY,iLocZ = GetPos()
    if iLocX < 0:
        kX = -1
    else:
        kX = 1
    if iLocY < 0:
        kY = -1
    else:
        kY = 1
    iDeltaX = (iAimX) - (iLocX)
    iDeltaY = (iAimY) - (iLocY)
    RestrictedX = cfg.read("Border","1")[0]
    RestrictedY = cfg.read("Border","1")[1]
    iAimX,iAimY,iAimZ = lAimPos
    logger.info([iAimX,iAimY,iAimZ])
    if iLocZ > 180:
        iDeltaZ = 360 - abs(iAimZ) - abs(iLocZ)
    else:
        iDeltaZ = (abs(iAimZ) - abs(iLocZ))
    logger.debug([iDeltaX,iDeltaY,iDeltaZ])
    LinearMap(iDeltaX,[0,300],[150,230])
    LinearMap(iDeltaY,[0,300],[150,230])
    iErrorRange = cfg.read("Position","ErrorRange")/4
    iMovedAngle = int(math.degrees(math.atan2(iDeltaY,iDeltaX)))
    if oldVersion:
        try:
            try:
                Slope = iDeltaX/iDeltaY
            except ZeroDivisionError:
                Slope = 1
            if Slope*RestrictedY > RestrictedX:
                iAimX = (RestrictedX - 3)*kX
            if Slope/RestrictedX > RestrictedY:
                iAimY = (RestrictedY - 3)*kY
        except:
            iAimX,iAimY,iAimZ = lAimPos
        logger.info([iAimX,iAimY,iAimZ])
        if iLocZ > 180:
            iDeltaZ = 360 - abs(iAimZ) - abs(iLocZ)
        else:
            iDeltaZ = (abs(iAimZ) - abs(iLocZ))
    else:
        try:
            availableAngles = []
            for k in range(1,2,1):
                for a in range(0,180,1):
                    RstrictedSlope = math.tan(math.radians(90-a))*k
                    if RstrictedSlope*RestrictedY > RestrictedX:
                        iFixedX = (RestrictedX - 3)*kX
                    if RstrictedSlope/RestrictedX > RestrictedY:
                        iFixedY = (RestrictedY - 3)*kY
                    if math.sqrt(iFixedX**2+iFixedY**2) <= 20:
                        availableAngles.append(a*k) 
            iMovedAngle = FindNearstAngle(iMovedAngle,availableAngles)
        except:
            pass
    if A2O:
        DistanceCache = GetDistance()
        if 0 < iMovedAngle%90 <= 1 :
            if DistanceCache[0] <= DistanceCache[1]:
                Anglek = 1
            else:
                AngleK = -1
        elif 1 < iMovedAngle%90 <= 2 :
            if DistanceCache[0] >= DistanceCache[3]:
                Anglek = 1
            else:
                AngleK = -1
        elif 2 < iMovedAngle%90 <= 3 :
            if DistanceCache[3] >= DistanceCache[2]:
                Anglek = 1
            else:
                AngleK = -1
        elif 3 < iMovedAngle%90 <= 4 :
            if DistanceCache[2] >= DistanceCache[1]:
                Anglek = 1
            else:
                AngleK = -1
        for a in AbsChassisAngle():
            if a == iMovedAngle:
                iMovedAngle = iMovedAngle + int((abs(iDeltaX)+abs(iDeltaY))*1.5)*-Anglek
    if iErrorRange > abs(iDeltaX) and iErrorRange > abs(iDeltaY) and abs(iErrorRange) > iDeltaZ:
        chassis.stop()
        return True
    elif iErrorRange > abs(iDeltaX) and iErrorRange > abs(iDeltaY) and not abs(iErrorRange) > abs(iDeltaZ):
        chassis.GoZSpeed(iDeltaZ)
    else:
        if SpeedRatio:
            chassis.GoA(lAimPos[2],90-iMovedAngle,SpeedRatio/100)
        if Speed:
            chassis.GoA(lAimPos[2],90-iMovedAngle,SpeedRatio/100)
        else:
            chassis.GoA(lAimPos[2],90-iMovedAngle,int((abs(iDeltaX)+abs(iDeltaY))*1.5))
        return False

def Move2Path(Posistions:list[list[int,int,int],list[int,int,int]],iWaitMs:int,A2O:bool | None = False):
    iErrorRange = cfg.read("Position","ErrorRange")/2
    for i in Posistions:
        while (1):
            iAimX = i[0]
            iAimY = i[1]
            iAimZ = i[2]
            lLocal = GetPos()
            iLocX = lLocal[0]
            iLocY = lLocal[1]
            iLocZ = lLocal[2]
            iDeltaX = iAimX - iLocX
            iDeltaY = iAimY - iLocY
            iDeltaZ = iAimZ - iLocZ
            if iErrorRange > abs(iDeltaX) and iErrorRange > abs(iDeltaY) and iErrorRange > abs(iDeltaZ):
                if i == Posistions[-1]:
                    return True
                else:
                    time.sleep(iWaitMs)
                    break
            else:
                Pos2Pos(lAimPos=i,A2O=A2O)

def Move2Pos(lPos):
    while not Pos2Pos(lPos,False,150):
        pass
    chassis.stop()
    # for _ in range(3):
    #     chassis.SetMotor(0,0,0,0)

