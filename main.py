# app.py
import io
from pathlib import Path

import torch
from torch import nn
from torchvision import models, transforms

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse

from PIL import Image

# ---------------------------
# Config de base
# ---------------------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Device:", device)

IMG_SIZE = 224
class_names = ["NORMAL", "PNEUMONIA"]

MODEL_PATH = Path("ai_model/best_model.pt")


# ---------------------------
# Build du modèle (même archi que training)
# ---------------------------
def build_model(num_classes: int = 2):
    model = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)

    # On garde comme en inference : on ne fine-tune plus
    for param in model.parameters():
        param.requires_grad = False

    in_features = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Linear(in_features, 256),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(256, num_classes),
    )

    return model.to(device)


# ---------------------------
# Chargement du modèle
# ---------------------------
if not MODEL_PATH.exists():
    raise FileNotFoundError(f"Model file not found at {MODEL_PATH}")

model = build_model(num_classes=len(class_names))
state_dict = torch.load(MODEL_PATH, map_location=device)
model.load_state_dict(state_dict)
model.eval()
print("✅ Model loaded")


# ---------------------------
# Transformations (identiques au training)
# ---------------------------
transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])


def preprocess_image(image_bytes: bytes) -> torch.Tensor:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = transform(image).unsqueeze(0)  # shape: [1, C, H, W]
    return tensor.to(device)


def predict(image_bytes: bytes):
    tensor = preprocess_image(image_bytes)

    with torch.no_grad():
        outputs = model(tensor)
        probs = torch.softmax(outputs, dim=1)[0]  # shape: [2]

    probs_list = probs.cpu().numpy().tolist()
    pred_idx = int(torch.argmax(probs).item())
    pred_label = class_names[pred_idx]

    # Probabilité sous forme {label: prob}
    probs_dict = {
        class_names[i]: float(probs_list[i]) for i in range(len(class_names))
    }

    return pred_label, probs_dict


# ---------------------------
# FastAPI app
# ---------------------------
app = FastAPI(
    title="Chest X-Ray Pneumonia API (Demo)",
    description=(
        "⚠️ Démo pédagogique uniquement. "
        "Ne pas utiliser pour un diagnostic médical réel."
    ),
    version="1.0.0",
)


from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Page HTML simple pour upload
@app.get("/", response_class=FileResponse)
async def root():
    return FileResponse("static/index.html")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# Endpoint API JSON pur
@app.post("/predict")
async def predict_endpoint(file: UploadFile = File(...)):
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Le fichier doit être une image JPG ou PNG.")

    image_bytes = await file.read()
    try:
        pred_label, probs = predict(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur pendant la prédiction: {e}")

    return {
        "prediction": pred_label,
        "probabilities": probs,
    }
