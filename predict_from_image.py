import os
import sys
from functools import partial
from http import HTTPStatus
from fastapi import FastAPI, File, UploadFile
from PIL import Image
from pathlib import Path
import hashlib
from fastapi.middleware.cors import CORSMiddleware
import fitz
import torch
from nougat import NougatModel
from nougat.postprocessing import markdown_compatible, close_envs
from nougat.utils.dataset import ImageDataset
from nougat.utils.checkpoint import get_checkpoint
from nougat.dataset.rasterize import rasterize_paper
from tqdm import tqdm
from io import BytesIO

import json

BATCHSIZE = os.environ.get("NOUGAT_BATCHSIZE", 6)

model = None
NOUGAT_CHECKPOINT = get_checkpoint()


def load_model():
    '''
    loads the model
    '''
    print("loading model...")
    global model
    if model is None:
        model = NougatModel.from_pretrained(NOUGAT_CHECKPOINT).to(torch.bfloat16)
        if torch.cuda.is_available():
            model.to("cuda")
        model.eval()
    print("done loading model")

def predict_from_image(image: Image.Image):
    '''
    image: a PIL image
    '''

    image_bytesIO = BytesIO(image.tobytes())
    
    dataset = ImageDataset(
        [image_bytesIO],
        partial(model.encoder.prepare_input, random_padding=False),
    )

    dataloader = torch.utils.data.DataLoader(
        dataset,
        batch_size=BATCHSIZE,
        pin_memory=True,
        shuffle=False,
    )

    result = []

    for idx, sample in tqdm(enumerate(dataloader), total=len(dataloader)):
        if sample is None:
            continue
        model_output = model.inference(image_tensors=sample)
        result.append(model_output)

    return json.dumps(result)

