import enum

from sqlalchemy import Enum


def str_enum[E: enum.Enum](cls: type[E], length: int = 20) -> Enum:
    """Enums are stored as their string values in a VARCHAR, identical on SQLite and PostgreSQL."""
    return Enum(cls, native_enum=False, length=length, values_callable=lambda e: [m.value for m in e], validate_strings=True)
