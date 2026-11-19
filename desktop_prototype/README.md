# Original local desktop prototype

This folder stores the previous OpenCV desktop dashboard as a reference.
It uses cv2.VideoCapture(0) and opens a local OpenCV window. Do not use that
desktop webcam capture loop on Render: a cloud host has no access to a visitor's
local webcam. The cloud version uses browser webcam access and MediaPipe Tasks
Vision JavaScript in ../static/app.js instead.
