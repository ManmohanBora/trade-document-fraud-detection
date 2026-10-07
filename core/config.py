"""
Multi-Modal AI Pipeline for Trade Document Fraud Detection & Compliance Auditing.

Configuration management using Pydantic Settings for type-safe,
environment-variable-driven configuration with sensible defaults.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    from pydantic import BaseModel as BaseSettings  # type: ignore[assignment]
    SettingsConfigDict = dict  # type: ignore[misc,assignment]


class DatabaseSettings(BaseSettings):
    """PostgreSQL connection configuration."""

    model_config = SettingsConfigDict(env_prefix="DB_")

    host: str = "localhost"
    port: int = 5432
    user: str = "fraud_pipeline"
    password: str = "changeme"
    name: str = "trade_fraud_audit"
    pool_size: int = Field(default=10, ge=1, le=50)
    pool_overflow: int = Field(default=5, ge=0, le=20)

    @property
    def dsn(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def sync_dsn(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class OCRSettings(BaseSettings):
    """OCR engine configuration."""

    model_config = SettingsConfigDict(env_prefix="OCR_")

    engine: Literal["tesseract", "easyocr"] = "tesseract"
    language: str = "eng"
    dpi: int = Field(default=300, ge=72, le=600)
    preprocessing_enabled: bool = True


class ImageAnalyticsSettings(BaseSettings):
    """Image analytics model configuration."""

    model_config = SettingsConfigDict(env_prefix="IMG_")

    yolo_model_path: str = "models/yolo/best.pt"
    resnet_model_path: str = "models/resnet/stamp_classifier.pth"
    confidence_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    manipulation_sensitivity: float = Field(default=0.7, ge=0.0, le=1.0)


class NLPSettings(BaseSettings):
    """NLP and document understanding configuration."""

    model_config = SettingsConfigDict(env_prefix="NLP_")

    layoutlm_model: str = "microsoft/layoutlmv3-base"
    max_sequence_length: int = Field(default=512, ge=128, le=2048)
    batch_size: int = Field(default=8, ge=1, le=64)
    device: Literal["cpu", "cuda", "mps"] = "cpu"


class RiskSettings(BaseSettings):
    """Risk assessment thresholds."""

    model_config = SettingsConfigDict(env_prefix="RISK_")

    high_threshold: int = Field(default=70, ge=0, le=100)
    medium_threshold: int = Field(default=40, ge=0, le=100)
    max_risk_score: int = 100
    visual_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    textual_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    layout_weight: float = Field(default=0.2, ge=0.0, le=1.0)

    @field_validator("textual_weight")
    @classmethod
    def weights_must_sum_to_one(cls, v: float, info) -> float:
        visual = info.data.get("visual_weight", 0.4)
        layout = info.data.get("layout_weight", 0.2)
        total = visual + v + layout
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"Weights must sum to 1.0, got {total:.2f} "
                f"(visual={visual}, textual={v}, layout={layout})"
            )
        return v


class Settings(BaseSettings):
    """Root application settings, composing all sub-configurations."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application metadata
    app_name: str = "Trade Document Fraud Detection Pipeline"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Upload constraints
    upload_dir: Path = Path("data/uploads")
    max_upload_size_mb: int = Field(default=50, ge=1, le=500)
    allowed_extensions: list[str] = [".pdf", ".png", ".jpg", ".jpeg", ".tiff"]

    # Sub-configurations
    database: DatabaseSettings = DatabaseSettings()
    ocr: OCRSettings = OCRSettings()
    image_analytics: ImageAnalyticsSettings = ImageAnalyticsSettings()
    nlp: NLPSettings = NLPSettings()
    risk: RiskSettings = RiskSettings()

    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        self.upload_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Cached settings factory.

    Returns a singleton Settings instance, loaded once from environment
    variables and .env file. Use dependency injection in FastAPI to
    override in tests.
    """
    return Settings()
