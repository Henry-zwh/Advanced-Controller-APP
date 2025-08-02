import cv2


class CameraManager:
    """Including scanning available cameras and resolutions."""
    
    @staticmethod
    def find_available_cameras():
        """Scan and return a dictionary of available cameras."""
        available_cameras = {}
        index = 0
        while True:
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                available_cameras[f"CAM {index}"] = index
                cap.release()
                index += 1
            else:
                cap.release()
                break
        return available_cameras

    @staticmethod
    def find_available_resolutions(cam_index):
        """Scan and return a list of available resolutions for the chosen camera."""
        temp_cap = cv2.VideoCapture(cam_index)
        if not temp_cap.isOpened():
            return []
        resolutions = set()
        # try common resolutions
        common_resolutions = [
            (1920, 1080),
            (1600, 1200),
            (1280, 720),
            (640, 480)
        ]
        for width, height in common_resolutions:
            temp_cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            temp_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            actual_width = temp_cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = temp_cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            if abs(actual_width - width) < 2 and abs(actual_height - height) < 2:
                resolutions.add((int(actual_width), int(actual_height)))
        temp_cap.release()
        # sort resolutions by width and height
        sorted_resolutions = sorted(list(resolutions), key=lambda r: (r[0], r[1]))
        return [f"{w}x{h}" for w, h in sorted_resolutions]
    