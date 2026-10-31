"""One bounded parse. Sanitized environment, no network-capable document processing."""

import sys


def main() -> None:
    from vmarket_ai.ingestion.limits import constrain

    constrain()
    import base64
    import json
    import socket

    def deny_network(*args: object, **kwargs: object) -> None:
        raise OSError("Parser network disabled")

    socket.socket.connect = deny_network  # type: ignore[method-assign]
    socket.create_connection = deny_network  # type: ignore[assignment]

    from vmarket_ai.ingestion.parsing import extract_in_worker
    from vmarket_ai.ingestion.spec import IngestionError

    try:
        payload = sys.stdin.buffer.read(7_000_001)
        if len(payload) > 7_000_000:
            raise IngestionError("size_or_media")
        data = json.loads(payload)
        result = extract_in_worker(base64.b64decode(data["raw"], validate=True), data["media_type"])
        sys.stdout.buffer.write(result.model_dump_json().encode())
    except IngestionError as error:
        print(str(error))
        raise SystemExit(1) from None
    except Exception:
        print("parse_failed")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
