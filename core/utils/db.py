from django.db import close_old_connections, connections


def refresh_db_connections() -> None:
    if any(connection.in_atomic_block for connection in connections.all()):
        return
    close_old_connections()
