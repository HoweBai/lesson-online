"""Service for managing user Claude API configurations."""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from ..models.claude_config import ClaudeConfig
from .crypto_service import SecureCryptoService


class ClaudeConfigService:
    """Manages storage and retrieval of user Claude API configurations with encryption."""

    def __init__(self, crypto_service: SecureCryptoService, db_session: Session):
        self.crypto = crypto_service
        self.db = db_session

    def save_config(self, user_id: str, config_dict: dict) -> ClaudeConfig:
        """Save or update a Claude API configuration for a user."""
        encrypted_key = self.crypto.encrypt_api_key(config_dict['api_key'])

        # Check if config already exists for this user
        existing = self.db.query(ClaudeConfig).filter_by(user_id=user_id).first()

        if existing:
            # Update existing config
            existing.base_url = config_dict['base_url']
            existing.api_key_encrypted = encrypted_key
            existing.model_name = config_dict.get('model_name', 'claude-3-opus-20240925')
            existing.system_prompt = config_dict.get('system_prompt', '')
            existing.is_default = config_dict.get('is_default', True)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # Create new config
            config = ClaudeConfig(
                user_id=str(user_id),
                base_url=config_dict['base_url'],
                api_key_encrypted=encrypted_key,
                model_name=config_dict.get('model_name', 'claude-3-opus-20240925'),
                system_prompt=config_dict.get('system_prompt', ''),
                created_at=datetime.utcnow(),
                is_default=config_dict.get('is_default', True)
            )
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
            return config

    def get_config(self, user_id: str, config_id: str) -> Optional[Dict[str, Any]]:
        """Get decrypted config for API calls."""
        config = self.db.query(ClaudeConfig).filter_by(
            id=config_id, user_id=user_id
        ).first()
        if not config:
            return None

        try:
            decrypted_key = self.crypto.decrypt_api_key(config.api_key_encrypted)
            return {
                'id': str(config.id),
                'base_url': config.base_url,
                'api_key': decrypted_key,
                'model_name': config.model_name,
                'system_prompt': config.system_prompt,
                'is_default': config.is_default
            }
        except Exception as e:
            print(f"Decryption error: {e}")
            return None

    def get_config_metadata(self, user_id: str, config_id: str) -> Optional[Dict]:
        """Get config metadata without decrypting the API key."""
        config = self.db.query(ClaudeConfig).filter_by(
            id=config_id, user_id=user_id
        ).first()
        if not config:
            return None
        return {
            'id': str(config.id),
            'user_id': str(config.user_id),
            'base_url': config.base_url,
            'model_name': config.model_name,
            'created_at': config.created_at.isoformat(),
            'last_used_at': config.last_used_at.isoformat() if config.last_used_at else None,
            'is_default': config.is_default
        }

    def get_user_configs(self, user_id: str) -> List[Dict]:
        """Get all configs for a user."""
        configs = self.db.query(ClaudeConfig).filter_by(user_id=user_id).all()
        return [
            {
                'id': str(c.id),
                'base_url': c.base_url,
                'model_name': c.model_name,
                'is_default': c.is_default,
                'created_at': c.created_at.isoformat()
            }
            for c in configs
        ]

    def get_default_config(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's default config."""
        config = self.db.query(ClaudeConfig).filter_by(
            user_id=user_id, is_default=True
        ).first()
        if config:
            return self.get_config(user_id, str(config.id))
        return None

    def delete_config(self, user_id: str, config_id: str) -> bool:
        """Delete a config."""
        config = self.db.query(ClaudeConfig).filter_by(
            id=config_id, user_id=user_id
        ).first()
        if not config:
            return False
        self.db.delete(config)
        self.db.commit()
        return True
