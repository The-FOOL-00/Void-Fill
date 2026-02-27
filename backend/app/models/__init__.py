"""SQLAlchemy ORM models.

All models are imported here so that ``Base.metadata`` sees every table
when ``create_all`` is called during application startup.
"""

from app.models.goal import Goal
from app.models.note import Note
from app.models.schedule_block import ScheduleBlock
from app.models.suggestion import Suggestion
from app.models.user import User
from app.models.voice_intelligence import VoiceIntelligence
from app.models.voice_job import VoiceJob
from app.models.voice_log import VoiceLog

__all__ = [
    "Goal",
    "Note",
    "ScheduleBlock",
    "Suggestion",
    "User",
    "VoiceIntelligence",
    "VoiceJob",
    "VoiceLog",
]
