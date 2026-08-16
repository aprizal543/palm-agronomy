from enum import StrEnum


class UserRole(StrEnum):
    FARMER = "farmer"
    FIELD_OFFICER = "field_officer"
    ADMIN = "admin"


class FarmAccessRole(StrEnum):
    VIEWER = "viewer"
    EDITOR = "editor"
    VALIDATOR = "validator"


class RecordStatus(StrEnum):
    DRAFT = "draft"
    PENDING_VALIDATION = "pending_validation"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class DataOrigin(StrEnum):
    SYNTHETIC = "synthetic"
    USER_INPUT = "user_input"
    FIELD_VERIFIED = "field_verified"
    PUBLIC_API = "public_api"
    SYSTEM_GENERATED = "system_generated"


class BoundarySource(StrEnum):
    MAP_DRAW = "map_draw"
    GPS_TRACK = "gps_track"
    GIS_IMPORT = "gis_import"
    AI_CANDIDATE = "ai_candidate"
