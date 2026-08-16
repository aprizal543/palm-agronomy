from sqlalchemy import Enum


def palm_enum(enum_cls, name: str) -> Enum:
    return Enum(
        enum_cls,
        name=name,
        schema="palm",
        values_callable=lambda values: [item.value for item in values],
        create_type=False,
    )

