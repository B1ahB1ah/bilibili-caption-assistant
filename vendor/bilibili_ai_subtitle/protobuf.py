"""Minimal protobuf decoder for Bilibili's web subtitle metadata response."""

from dataclasses import dataclass


@dataclass
class ProtoField:
    number: int
    wire_type: int
    value: int | None = None
    data: bytes | None = None


def _read_varint(payload: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while offset < len(payload):
        byte = payload[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, offset
        shift += 7
        if shift > 63:
            raise ValueError("protobuf varint is too long")
    raise ValueError("unterminated protobuf varint")


def decode_message(payload: bytes) -> list[ProtoField]:
    fields: list[ProtoField] = []
    offset = 0

    while offset < len(payload):
        key, offset = _read_varint(payload, offset)
        number = key >> 3
        wire_type = key & 0x07
        if number <= 0:
            raise ValueError("invalid protobuf field number")

        if wire_type == 0:
            value, offset = _read_varint(payload, offset)
            fields.append(ProtoField(number, wire_type, value=value))
        elif wire_type in (1, 5):
            size = 8 if wire_type == 1 else 4
            end = offset + size
            if end > len(payload):
                raise ValueError("truncated protobuf fixed field")
            fields.append(ProtoField(number, wire_type, data=payload[offset:end]))
            offset = end
        elif wire_type == 2:
            length, offset = _read_varint(payload, offset)
            end = offset + length
            if end > len(payload):
                raise ValueError("truncated protobuf bytes field")
            fields.append(ProtoField(number, wire_type, data=payload[offset:end]))
            offset = end
        else:
            raise ValueError(f"unsupported protobuf wire type: {wire_type}")

    return fields


def _bytes(fields: list[ProtoField], number: int) -> bytes | None:
    return next(
        (field.data for field in fields if field.number == number and field.wire_type == 2),
        None,
    )


def _varint(fields: list[ProtoField], number: int) -> int | None:
    return next(
        (field.value for field in fields if field.number == number and field.wire_type == 0),
        None,
    )


def _text(fields: list[ProtoField], number: int) -> str | None:
    value = _bytes(fields, number)
    return value.decode("utf-8") if value is not None else None


def parse_web_subtitle_response(payload: bytes) -> list[dict]:
    """Parse ``/x/v2/subtitle/web/view`` and return subtitle tracks."""
    top_fields = decode_message(payload)
    data_payload = _bytes(top_fields, 1)
    if not data_payload:
        return []

    tracks = []
    for field in decode_message(data_payload):
        if field.number != 3 or field.wire_type != 2 or not field.data:
            continue

        item_fields = decode_message(field.data)
        language = _text(item_fields, 3)
        subtitle_url = _text(item_fields, 5)
        if not language or not subtitle_url:
            continue

        tracks.append(
            {
                "id": _varint(item_fields, 1),
                "id_str": _text(item_fields, 2),
                "lan": language,
                "lan_doc": _text(item_fields, 4),
                "subtitle_url": subtitle_url,
            }
        )

    return tracks
