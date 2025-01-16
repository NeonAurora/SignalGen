# signal_generator.py
import sys
import time
import firebase_setup  # Ensure Firebase is initialized here
from firebase_admin import db
from PyQt5.QtWidgets import QApplication, QSlider, QVBoxLayout, QHBoxLayout, QLabel, QWidget
from PyQt5.QtCore import Qt, QTimer

# Import our newly created logic class
from signal_logic import SignalLogic

class SignalGenerator(QWidget):
    def __init__(self):
        super().__init__()

        # Firebase references
        self.trains_ref = db.reference('/trains')
        self.tracks_ref = db.reference('/tracks')

        # We only handle track occupancy in this file
        # For signals, we delegate to SignalLogic
        self.signal_logic = SignalLogic()

        # Keep track of previous segments for each train
        self.previous_segments = {}

        # Store track segment sliders dynamically
        self.track_sliders = {}

        # Push the initial starter signals to Firebase (or handle in signal_logic)
        # NOTE: This might remain or move to signal_logic if you want
        self.push_starter_signals()

        # Setup UI for track segments
        self.init_ui()

        # Timer to update occupancy AND signals
        self.timer = QTimer()
        self.timer.timeout.connect(self.main_update)
        self.timer.start(300)  # every 300ms

    def push_starter_signals(self):
        """
        (Optional) We can still do an initial push of static data for signals.
        This could also be placed in the SignalLogic class, up to you.
        """
        starters_data = {
            "1": {"row": 38, "col": 160, "status": 0},  # We'll dynamically update this one
            "2": {"row": 58, "col": 160, "status": 1},
            "3": {"row": 72, "col": 130, "status": 2},
            "4": {"row": 92, "col": 130, "status": 0},
            "5": {"row": 58, "col": 200, "status": 1},
        }
        signals_ref = db.reference('/signals/starters')
        signals_ref.set(starters_data)
        print("Starter signals pushed to Firebase.")

    def init_ui(self):
        self.setWindowTitle('Track Segment Status')
        self.setGeometry(0, 0, 1500, 900)

        # 1) The main layout is vertical, so we can have a "top box" and a "bottom box".
        main_layout = QVBoxLayout()

        # 2) Create top_layout (for label + sliders) and bottom_layout (empty).
        top_layout = QVBoxLayout()
        bottom_layout = QVBoxLayout()  # intentionally empty

        # ----------------------------------------------------------------
        #  A) BUILD THE TOP BOX CONTENT
        # ----------------------------------------------------------------
        # We'll have a single 'track label' area plus the 'track inner layout'.
        # Then we want the track label to take 1 part, the track_inner_layout 4 parts
        # so that total=5. This yields 20% vs 80% of the top box.
        # But overall, that is 10% vs 40% of the entire window, since top_layout is only 50%.
        #
        # top_layout
        #    |--- track_label (stretch 1)
        #    |--- track_inner_layout (stretch 4)
        #
        # track_inner_layout can itself hold multiple track columns horizontally.

        # Create a horizontal layout that will hold all track columns (T1..T9) side by side
        track_inner_layout = QHBoxLayout()

        # For each track, build the vertical layout: label column + slider column
        for track_id in ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9']:
            track_main_layout = QVBoxLayout()

            # You might want a small title, e.g. "Track T1"
            # but if you only want a single label for all tracks, skip this
            track_label = QLabel(f"Track {track_id}")
            track_label.setAlignment(Qt.AlignCenter)
            track_main_layout.addWidget(track_label)

            # A horizontal layout: left column for segment labels, right column for sliders
            track_columns_layout = QHBoxLayout()
            track_label_column = QVBoxLayout()
            track_slider_column = QVBoxLayout()

            # Load segments from Firebase
            track_data = self.tracks_ref.child(track_id).get()
            if not track_data or 'segments' not in track_data:
                # If track has no segments, skip
                continue

            segments = track_data['segments']
            self.track_sliders[track_id] = {}

            # Add each segment’s label and slider
            for segment_id, segment_info in segments.items():
                segment_label = QLabel(f"Segment {segment_id}")
                track_label_column.addWidget(segment_label)

                slider = QSlider(Qt.Horizontal)
                slider.setRange(0, 1)
                slider.setValue(1 if segment_info.get('occupied') else 0)
                slider.valueChanged.connect(self.slider_value_changed)
                track_slider_column.addWidget(slider)

                self.track_sliders[track_id][segment_id] = slider

            track_columns_layout.addLayout(track_label_column)
            track_columns_layout.addLayout(track_slider_column)
            track_main_layout.addLayout(track_columns_layout)

            # Now add this track’s layout to the big horizontal layout
            track_inner_layout.addLayout(track_main_layout)

        # ----------------------------------------------------------------
        #  B) Add track label + track_inner_layout to the top_layout
        # ----------------------------------------------------------------
        top_layout.addLayout(track_inner_layout)

        # ----------------------------------------------------------------
        #  C) Combine top_layout and bottom_layout in the main_layout
        # ----------------------------------------------------------------
        # top_layout => 50% of the window
        # bottom_layout => 50% of the window (empty by design)
        main_layout.addLayout(top_layout, 1)
        dummy_label = QLabel(f"Starter and Advance Starter")
        bottom_layout.addWidget(dummy_label)
        main_layout.addLayout(bottom_layout, 1)

        # 3) Finally, apply main_layout as the layout for our QWidget
        self.setLayout(main_layout)

    def main_update(self):
        """
        Runs every 300ms.
        1) update track occupancy from train data
        2) update all signals via SignalLogic
        """
        self.update_occupancy()
        self.signal_logic.update_signals()  # <--- new call to external logic

    def update_occupancy(self):
        # Read train data from Firebase
        trains_data = self.trains_ref.get()
        if not trains_data:
            return

        for train_id, train_data in trains_data.items():
            current_track = train_data.get('current_track')
            current_segment = train_data.get('current_segment')
            if not current_track or not current_segment:
                continue

            # Mark current segment as occupied
            path = f'{current_track}/segments/{current_segment}/occupied'
            self.tracks_ref.child(path).set(True)

            # Update slider
            if current_track in self.track_sliders:
                if current_segment in self.track_sliders[current_track]:
                    sldr = self.track_sliders[current_track][current_segment]
                    sldr.blockSignals(True)
                    sldr.setValue(1)
                    sldr.blockSignals(False)

            # Free the previous segment
            if train_id in self.previous_segments:
                prev_track, prev_segment = self.previous_segments[train_id]
                if prev_track != current_track or prev_segment != current_segment:
                    prev_path = f'{prev_track}/segments/{prev_segment}/occupied'
                    self.tracks_ref.child(prev_path).set(False)

                    if (prev_track in self.track_sliders and
                            prev_segment in self.track_sliders[prev_track]):
                        psldr = self.track_sliders[prev_track][prev_segment]
                        psldr.blockSignals(True)
                        psldr.setValue(0)
                        psldr.blockSignals(False)

            self.previous_segments[train_id] = (current_track, current_segment)

    def slider_value_changed(self):
        """
        Handle manual slider changes for track segments
        """
        slider = self.sender()
        for track_id, segments in self.track_sliders.items():
            for segment_id, track_slider in segments.items():
                if track_slider == slider:
                    new_value = (slider.value() == 1)
                    path = f'{track_id}/segments/{segment_id}/occupied'
                    self.tracks_ref.child(path).set(new_value)
                    return  # done

    def run(self):
        self.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    signal_generator = SignalGenerator()
    signal_generator.run()
    sys.exit(app.exec_())
