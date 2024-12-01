# signal_generator.py
import sys
import time
import firebase_setup  # Import Firebase setup to ensure Firebase is initialized
from firebase_admin import db
from PyQt5.QtWidgets import QApplication, QSlider, QVBoxLayout, QHBoxLayout, QLabel, QWidget
from PyQt5.QtCore import Qt, QTimer


class SignalGenerator(QWidget):
    def __init__(self):
        super().__init__()

        # Firebase references
        self.trains_ref = db.reference('/trains')
        self.tracks_ref = db.reference('/tracks')

        # Store previous segment to free up occupancy later
        self.previous_segments = {}

        # Store segment sliders dynamically
        self.track_sliders = {}

        # Setup UI for segment status display
        self.init_ui()

        # Timer to update the occupancy status periodically
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_occupancy)
        self.timer.start(100)  # Check occupancy status every 100ms

    def init_ui(self):
        self.setWindowTitle('Track Segment Status')
        self.setGeometry(100, 100, 800, 600)

        # Layouts to organize the sliders
        main_layout = QHBoxLayout()  # Main layout to hold Track 1 and Track 2

        # Track Layouts
        for track_id in ['T1', 'T2']:
            track_main_layout = QVBoxLayout()
            track_label = QLabel(f"Track {track_id[-1]}")
            track_label.setAlignment(Qt.AlignCenter)
            track_main_layout.addWidget(track_label)

            # Nested layout for track segments
            track_inner_layout = QHBoxLayout()
            track_label_column = QVBoxLayout()  # Left column for segment labels
            track_slider_column = QVBoxLayout()  # Right column for sliders

            # Load segments from Firebase
            track_data = self.tracks_ref.child(track_id).get()
            if not track_data or 'segments' not in track_data:
                continue
            segments = track_data['segments']

            # Create sliders for each segment dynamically
            self.track_sliders[track_id] = {}
            for segment_id, segment_info in segments.items():
                segment_label = QLabel(f"Segment {segment_id}")
                track_label_column.addWidget(segment_label)

                slider = QSlider(Qt.Horizontal)
                slider.setRange(0, 1)  # Binary range 0 or 1
                slider.setValue(1 if segment_info['occupied'] else 0)
                slider.valueChanged.connect(self.slider_value_changed)  # Connect slider change signal
                track_slider_column.addWidget(slider)

                # Store the slider reference
                self.track_sliders[track_id][segment_id] = slider

            # Add the inner layouts to the main track layout
            track_inner_layout.addLayout(track_label_column)
            track_inner_layout.addLayout(track_slider_column)
            track_main_layout.addLayout(track_inner_layout)

            # Add Track main layout to the main layout
            main_layout.addLayout(track_main_layout)

        self.setLayout(main_layout)

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

            # Update the current segment to occupied in Firebase
            self.tracks_ref.child(segment_path).set(True)

            # Update the slider based on the current segment's occupancy
            if current_track in self.track_sliders and current_segment in self.track_sliders[current_track]:
                self.track_sliders[current_track][current_segment].blockSignals(True)
                self.track_sliders[current_track][current_segment].setValue(1)
                self.track_sliders[current_track][current_segment].blockSignals(False)

            # Check if the train was on a different segment before
            if train_id in self.previous_segments:
                previous_track, previous_segment = self.previous_segments[train_id]

                # If the previous segment is different from the current one, mark it as free
                if previous_track != current_track or previous_segment != current_segment:
                    previous_segment_path = f'{previous_track}/segments/{previous_segment}/occupied'
                    self.tracks_ref.child(previous_segment_path).set(False)

                    # Update the slider to reflect that the segment is now unoccupied
                    if previous_track in self.track_sliders and previous_segment in self.track_sliders[previous_track]:
                        self.track_sliders[previous_track][previous_segment].blockSignals(True)
                        self.track_sliders[previous_track][previous_segment].setValue(0)
                        self.track_sliders[previous_track][previous_segment].blockSignals(False)

            # Update the previous segment for the next iteration
            self.previous_segments[train_id] = (current_track, current_segment)

    def slider_value_changed(self):
        """
        Handle slider value change and update Firebase accordingly.
        """
        slider = self.sender()  # Get the slider that triggered the event

        # Find which track and segment the slider belongs to
        for track_id, segments in self.track_sliders.items():
            for segment_id, track_slider in segments.items():
                if track_slider == slider:
                    # Update Firebase with the new value
                    new_value = slider.value() == 1
                    self.tracks_ref.child(f'{track_id}/segments/{segment_id}/occupied').set(new_value)
                    break

    def run(self):
        # Start the Qt application event loop
        self.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    signal_generator = SignalGenerator()
    signal_generator.run()
    sys.exit(app.exec_())
