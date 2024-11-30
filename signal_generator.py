# signal_generator.py
import time
import firebase_setup  # Import Firebase setup to ensure Firebase is initialized
from firebase_admin import db


class SignalGenerator:
    def __init__(self):
        # Firebase references
        self.trains_ref = db.reference('/trains')
        self.tracks_ref = db.reference('/tracks')

        # Store previous segment to free up occupancy later
        self.previous_segments = {}

    def update_occupancy(self):
        # Fetch current data for all trains
        trains_data = self.trains_ref.get()

        if not trains_data:
            return

        for train_id, train_data in trains_data.items():
            current_track = train_data.get('current_track')
            current_segment = train_data.get('current_segment')

            if not current_track or not current_segment:
                continue

            # Construct the full path to the current segment in the tracks section
            segment_path = f'{current_track}/segments/{current_segment}/occupied'

            # Update the current segment to occupied
            self.tracks_ref.child(segment_path).set(True)

            # Check if the train was on a different segment before
            if train_id in self.previous_segments:
                previous_track, previous_segment = self.previous_segments[train_id]

                # If the previous segment is different from the current one, mark it as free
                if previous_track != current_track or previous_segment != current_segment:
                    previous_segment_path = f'{previous_track}/segments/{previous_segment}/occupied'
                    self.tracks_ref.child(previous_segment_path).set(False)

            # Update the previous segment for the next iteration
            self.previous_segments[train_id] = (current_track, current_segment)

    def run(self):
        # Continuously monitor and update track occupancy
        while True:
            self.update_occupancy()
            time.sleep(0.1)  # Short delay to avoid overwhelming the database with updates


if __name__ == "__main__":
    signal_generator = SignalGenerator()
    signal_generator.run()
