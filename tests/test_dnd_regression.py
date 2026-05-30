import pytest
import uuid
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "2. Source Code")))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QModelIndex, QMimeData
import json

from models import PlaylistModel, QueueModel

@pytest.fixture(scope="session")
def app():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    yield app

def test_queue_live_state_shift():
    """Test that live_index updates correctly when items are removed via removeRows."""
    model = QueueModel()
    
    # Add 5 items
    for i in range(5):
        model.add_item({"reference": f"Verse {i}"})
        
    assert model.rowCount() == 5
    
    # Set live to item 2 (Verse 2)
    model.set_live(2)
    assert model.live_index == 2
    
    # Remove item 0. Live should shift to 1.
    model.removeRows(0, 1)
    assert model.live_index == 1
    
    # Remove items 3 and 4 (after live). Live should stay 1.
    model.removeRows(2, 2)
    assert model.live_index == 1
    assert model.rowCount() == 2
    
    # Remove the live item. Live should become -1.
    model.removeRows(1, 1)
    assert model.live_index == -1

def test_drop_mime_data_returns_false():
    """Verify models no longer mutate data via dropMimeData."""
    model = PlaylistModel()
    model.add_item({"reference": "Test"})
    
    mime = QMimeData()
    payload = json.dumps([{"type": "verse", "reference": "New"}]).encode("utf-8")
    mime.setData("application/x-verseflow-playlist-item", payload)
    
    # Call dropMimeData
    result = model.dropMimeData(mime, Qt.DropAction.MoveAction, 1, 0, QModelIndex())
    
    # Should return False and NOT mutate the model
    assert result is False
    assert model.rowCount() == 1

def test_remove_rows_playlist():
    """Verify removeRows works correctly for PlaylistModel."""
    model = PlaylistModel()
    for i in range(5):
        model.add_item({"reference": f"Verse {i}"})
        
    assert model.rowCount() == 5
    result = model.removeRows(1, 2)
    assert result is True
    assert model.rowCount() == 3
    assert model.item_at(0)["reference"] == "Verse 0"
    assert model.item_at(1)["reference"] == "Verse 3"
