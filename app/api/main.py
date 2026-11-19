"""API prakiraan PM2.5 tiga jam ke depan.

Jalankan dari folder utama repo:
    uvicorn app.api.main:app --reload
Dokumentasi interaktif ada di http://127.0.0.1:8000/docs
"""
from datetime import datetime
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.predict import BATAS, muat_model, prakirakan

model, metadata = muat_model()
app = FastAPI(title="Prakiraan PM2.5 Bandung", version=metadata["versi_model"])


class Masukan(BaseModel):
    stasiun: Literal["Dago", "Soekarno-Hatta", "Cibeureum", "Antapani", "Ujungberung"]
    waktu: datetime = Field(description="Jam saat ini (WIB)", examples=["2026-06-10T15:00:00"])
    pm25: float = Field(ge=BATAS["pm25"][0], le=BATAS["pm25"][1], description="PM2.5 jam ini (µg/m³)")
    suhu: float = Field(ge=BATAS["suhu"][0], le=BATAS["suhu"][1], description="Suhu (°C)")
    kelembaban: float = Field(ge=BATAS["kelembaban"][0], le=BATAS["kelembaban"][1], description="Kelembapan (%)")
    kecepatan_angin: float = Field(ge=BATAS["kecepatan_angin"][0], le=BATAS["kecepatan_angin"][1], description="m/detik")
    arah_angin: float = Field(ge=BATAS["arah_angin"][0], le=BATAS["arah_angin"][1], description="Derajat")
    curah_hujan: float = Field(ge=BATAS["curah_hujan"][0], le=BATAS["curah_hujan"][1], description="mm per jam")


@app.get("/")
def status():
    return {"status": "ok", "versi_model": metadata["versi_model"]}


@app.get("/metadata")
def info_model():
    return metadata


@app.post("/predict")
def predict(masukan: Masukan):
    try:
        return prakirakan(model, metadata, masukan.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
