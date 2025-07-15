import cv2
import numpy as np
import time
import math

CamIndex = 6
# Change your camera index here

Cam = cv2.VideoCapture(CamIndex,cv2.CAP_V4L2)
Cam.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
Cam.set(cv2.CAP_PROP_BRIGHTNESS, -64)
Cam.set(cv2.CAP_PROP_CONTRAST, 32)
Cam.set(cv2.CAP_PROP_SATURATION, 64)
Cam.set(cv2.CAP_PROP_SHARPNESS, 2)
# Ensure the exposure is the lowest

def applyPerspectiveTransform(X, Y, Matrix):
    Point = np.array([X, Y, 1], dtype=np.float64)
    Transformed = Matrix @ Point
    Transformed /= Transformed[2]
    return int(Transformed[0]), int(Transformed[1])


time.sleep(2)
_,Frame = Cam.read()
while True:
    _,Frame = Cam.read()
    cv2.imshow("Frame", Frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
Gray = cv2.cvtColor(Frame, cv2.COLOR_BGR2GRAY)
# Adjust the chessboard and press q

Ret,Corners = cv2.findChessboardCornersSB(Gray, (9, 9), None)
# Use Structured Binary for robustness

# Auto save to /root/CalibrationDataX.npz