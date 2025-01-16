# signal_logic.py
import firebase_admin
from firebase_admin import db

class SignalLogic:
    """
    This class centralizes all the logic for starter and advance starter signals.
    For each signal, we define:
      - which track segments to monitor
      - how to compute the final status (red/green/yellow)
    """

    def __init__(self):
        # Keep references to your Firebase Realtime Database
        self.tracks_ref = db.reference("/tracks")
        self.signals_ref = db.reference("/signals/starters")

        # Define the logic for each signal here.
        # Example: signal #1 becomes red if ANY of T2's S1, S2, S3 is occupied,
        # else green. You can extend for more signals (2,3,4...) and more complex conditions.
        self.signal_definitions = {
            "1": {
                "description": "Starter signal #1 on Track T2, depends on S1, S2, S3",
                "track_id": "T2",
                "segments": ["S1", "S2", "S3"],
                "trigger_type": "ANY",    # or ALL
                "red_status": 1,
                "green_status": 0,
                "yellow_status": 2
            },
            "2": {
                "description": "Starter signal #2 on Track T1, depends on S7",
                "track_id": "T1",
                "segments": ["S7"],
                "trigger_type": "ANY",  # or ALL
                "red_status": 1,
                "green_status": 0,
                "yellow_status": 2
            },
            "3": {
                "description": "Starter signal #3 on Track T2, depends on S4",
                "track_id": "T2",
                "segments": ["S4"],
                "trigger_type": "ANY",  # or ALL
                "red_status": 1,
                "green_status": 0,
                "yellow_status": 2
            },
        }

    def update_signals(self):
        """
        Scan the relevant track segments for each signal definition,
        then compute the correct status and push to Firebase.
        """
        for signal_id, definition in self.signal_definitions.items():
            track_id = definition.get("track_id")
            segment_list = definition.get("segments", [])
            trigger_type = definition.get("trigger_type", "ANY")  # "ANY" or "ALL"

            # The color statuses if you want them
            red_status = definition.get("red_status", 1)
            green_status = definition.get("green_status", 0)

            # 1) Determine occupancy
            occupancy_flags = []
            for seg in segment_list:
                # read the 'occupied' boolean from /tracks/<track_id>/segments/<seg>/occupied
                is_occupied = self.tracks_ref.child(track_id)\
                                             .child("segments")\
                                             .child(seg)\
                                             .child("occupied").get()
                occupancy_flags.append(bool(is_occupied))

            # 2) Based on trigger_type, decide if the signal is red or green
            if trigger_type == "ANY":
                # If ANY segment is occupied => red, else => green
                is_any_occupied = any(occupancy_flags)
                new_status = red_status if is_any_occupied else green_status
            else:  # "ALL"
                # If ALL segments are occupied => red, else => green
                is_all_occupied = all(occupancy_flags)
                new_status = red_status if is_all_occupied else green_status

            # 3) Optionally, you could have more complex logic for YELLOW, etc.

            # 4) Update the signal's status in Firebase
            self.signals_ref.child(signal_id).child("status").set(new_status)
