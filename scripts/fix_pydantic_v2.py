#!/usr/bin/env python3
"""Script to fix Pydantic V2 compatibility issues."""

import re
from pathlib import Path

def fix_pydantic_models(file_path: Path):
    """Fix Pydantic V1 to V2 compatibility issues in a file."""
    content = file_path.read_text(encoding='utf-8')
    
    # Replace class Config with model_config
    content = re.sub(
        r'    class Config:\s*\n\s*allow_population_by_field_name = True',
        '    model_config = ConfigDict(populate_by_name=True)',
        content
    )
    
    # Replace @validator with @field_validator
    content = re.sub(
        r'@validator\(([^)]+), pre=True\)',
        r'@field_validator(\1, mode="before")\n    @classmethod',
        content
    )
    
    # Replace single field validators
    content = re.sub(
        r'@validator\("([^"]+)", pre=True\)',
        r'@field_validator("\1", mode="before")\n    @classmethod',
        content
    )
    
    # Fix validator method signatures
    content = re.sub(
        r'def ([a-zA-Z_]+)\(cls, v\):',
        r'def \1(cls, v):',
        content
    )
    
    # Fix validator with field parameter
    content = re.sub(
        r'@validator\(([^)]+), pre=True\)\s*\n\s*def ([a-zA-Z_]+)\(cls, v, values, field\):',
        r'@field_validator(\1, mode="before")\n    @classmethod\n    def \2(cls, v):',
        content
    )
    
    file_path.write_text(content, encoding='utf-8')
    print(f"Fixed {file_path}")

def main():
    """Main function to fix Pydantic compatibility."""
    models_file = Path(__file__).parent.parent / "src" / "sonarqube_client" / "models.py"
    config_file = Path(__file__).parent.parent / "src" / "mcp_server" / "config.py"
    
    print("Fixing Pydantic V2 compatibility issues...")
    
    # Fix models.py
    if models_file.exists():
        fix_pydantic_models(models_file)
    
    # Fix config.py - different approach for pydantic-settings
    if config_file.exists():
        content = config_file.read_text(encoding='utf-8')
        
        # Replace Field with env parameter for pydantic-settings
        content = re.sub(
            r'Field\(([^,]+), env="([^"]+)"\)',
            r'Field(\1, description="Environment variable: \2")',
            content
        )
        
        # Add model_config for settings
        if 'class MCPServerSettings(BaseSettings):' in content and 'model_config' not in content:
            content = content.replace(
                'class MCPServerSettings(BaseSettings):',
                '''class MCPServerSettings(BaseSettings):
    """Main settings for the MCP server."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )'''
            )
            
            # Remove old Config class
            content = re.sub(
                r'\s*class Config:\s*\n\s*env_file = "\.env"\s*\n\s*env_file_encoding = "utf-8"\s*\n\s*case_sensitive = False\s*\n',
                '',
                content
            )
        
        # Add import for SettingsConfigDict
        if 'from pydantic_settings import BaseSettings' in content:
            content = content.replace(
                'from pydantic_settings import BaseSettings',
                'from pydantic_settings import BaseSettings, SettingsConfigDict'
            )
        
        config_file.write_text(content, encoding='utf-8')
        print(f"Fixed {config_file}")
    
    print("Pydantic V2 compatibility fixes completed!")

if __name__ == "__main__":
    main()