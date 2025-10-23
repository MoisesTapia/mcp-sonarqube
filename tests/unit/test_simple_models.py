"""Simple test for Pydantic models to verify V2 compatibility."""

import pytest
from datetime import datetime

# Test basic Pydantic V2 functionality
def test_pydantic_v2_basic():
    """Test basic Pydantic V2 functionality."""
    from pydantic import BaseModel, ConfigDict, Field, field_validator
    
    class TestModel(BaseModel):
        model_config = ConfigDict(populate_by_name=True)
        
        name: str
        value: int = Field(alias="test_value")
        created_at: datetime = Field(alias="createdAt")
        
        @field_validator("created_at", mode="before")
        @classmethod
        def parse_datetime(cls, v):
            if isinstance(v, str):
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
    
    # Test with alias
    data = {
        "name": "test",
        "test_value": 42,
        "createdAt": "2025-10-22T10:00:00Z"
    }
    
    model = TestModel(**data)
    assert model.name == "test"
    assert model.value == 42
    assert isinstance(model.created_at, datetime)
    
    # Test with field names
    data2 = {
        "name": "test2",
        "value": 24,
        "created_at": datetime.now()
    }
    
    model2 = TestModel(**data2)
    assert model2.name == "test2"
    assert model2.value == 24


def test_pydantic_settings():
    """Test Pydantic settings V2 functionality."""
    from pydantic import BaseModel, Field
    from pydantic_settings import BaseSettings, SettingsConfigDict
    
    class TestSettings(BaseSettings):
        model_config = SettingsConfigDict(
            env_file=".env",
            case_sensitive=False,
        )
        
        test_value: str = Field("default", description="Test value")
        test_number: int = Field(42, description="Test number")
    
    settings = TestSettings()
    assert settings.test_value == "default"
    assert settings.test_number == 42


if __name__ == "__main__":
    test_pydantic_v2_basic()
    test_pydantic_settings()
    print("All Pydantic V2 tests passed!")