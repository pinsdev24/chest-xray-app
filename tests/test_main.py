import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Mock the model loading parts BEFORE importing main
# This is necessary because main.py runs code at module level
sys.modules["torch"] = MagicMock()
sys.modules["torchvision"] = MagicMock()
sys.modules["PIL"] = MagicMock()

# We need to mock the specific attributes used in main.py
with patch("pathlib.Path.exists", return_value=True), \
     patch("torch.load", return_value={}), \
     patch("torch.device", return_value="cpu"), \
     patch("torchvision.models.resnet18"), \
     patch("torch.nn.Sequential"), \
     patch("torch.nn.Linear"), \
     patch("torch.nn.ReLU"), \
     patch("torch.nn.Dropout"), \
     patch("torchvision.transforms.Compose"):
    
    from main import app, predict

client = TestClient(app)

def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_read_root():
    """Test that the root endpoint returns the index.html file."""
    # We need to mock FileResponse to avoid looking for the actual file
    with patch("main.FileResponse") as mock_file_response:
        from fastapi.responses import Response
        mock_file_response.return_value = Response(content="index.html content", media_type="text/html")
        response = client.get("/")
        assert response.status_code == 200
        assert response.text == "index.html content"

def test_predict_endpoint_invalid_file():
    """Test uploading a non-image file."""
    response = client.post(
        "/predict",
        files={"file": ("test.txt", b"content", "text/plain")}
    )
    assert response.status_code == 400
    assert "doit être une image" in response.json()["detail"]

@patch("main.predict")
def test_predict_endpoint_success(mock_predict):
    """Test a successful prediction."""
    # Mock the predict function to return a fixed result
    mock_predict.return_value = ("NORMAL", {"NORMAL": 0.95, "PNEUMONIA": 0.05})
    
    # Create a dummy image file
    files = {"file": ("test.jpg", b"fakeimagebytes", "image/jpeg")}
    
    response = client.post("/predict", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["prediction"] == "NORMAL"
    assert data["probabilities"]["NORMAL"] == 0.95
