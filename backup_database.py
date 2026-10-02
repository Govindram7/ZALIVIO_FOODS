import os
import sqlite3
from datetime import datetime


# =========================================================
# PATH CONFIGURATION
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE_PATH = os.path.join(
    BASE_DIR,
    "instance",
    "zalivio.db"
)

BACKUP_FOLDER = os.path.join(
    BASE_DIR,
    "instance",
    "backups"
)


# =========================================================
# BACKUP RETENTION CONFIGURATION
# =========================================================

# Keep the newest 14 automatic backups.
MAX_AUTOMATIC_BACKUPS = 14

# Files containing this text are protected from cleanup.
PROTECTED_BACKUP_TEXT = "before-production"


# =========================================================
# CLEAN OLD AUTOMATIC BACKUPS
# =========================================================

def cleanup_old_backups():

    if not os.path.isdir(BACKUP_FOLDER):
        return

    automatic_backups = []

    for filename in os.listdir(BACKUP_FOLDER):

        # Only consider Zalivio SQLite backup files.
        if (
            not filename.startswith("zalivio_")
            or not filename.endswith(".db")
        ):
            continue

        # Never automatically delete protected backups.
        if PROTECTED_BACKUP_TEXT in filename:
            continue

        full_path = os.path.join(
            BACKUP_FOLDER,
            filename
        )

        if os.path.isfile(full_path):
            automatic_backups.append(
                full_path
            )

    # Newest backup first.
    automatic_backups.sort(
        key=os.path.getmtime,
        reverse=True
    )

    old_backups = automatic_backups[
        MAX_AUTOMATIC_BACKUPS:
    ]

    if not old_backups:
        print(
            "Backup cleanup: "
            "No old automatic backups to remove."
        )
        return

    removed_count = 0

    for backup_path in old_backups:

        try:

            os.remove(
                backup_path
            )

            removed_count += 1

            print(
                "Removed old backup:",
                os.path.basename(
                    backup_path
                )
            )

        except OSError as error:

            print(
                "Could not remove old backup:",
                os.path.basename(
                    backup_path
                ),
                "-",
                error
            )

    print(
        f"Backup cleanup: "
        f"{removed_count} old backup(s) removed."
    )


# =========================================================
# CREATE VERIFIED DATABASE BACKUP
# =========================================================

def create_backup():

    print("=" * 55)
    print("ZALIVIO DATABASE BACKUP")
    print("=" * 55)

    # -----------------------------------------------------
    # CHECK LIVE DATABASE
    # -----------------------------------------------------

    if not os.path.isfile(DATABASE_PATH):

        print(
            "ERROR: Live database was not found."
        )

        print(
            f"Expected location: {DATABASE_PATH}"
        )

        return False

    # -----------------------------------------------------
    # CREATE BACKUP DIRECTORY
    # -----------------------------------------------------

    os.makedirs(
        BACKUP_FOLDER,
        exist_ok=True
    )

    # -----------------------------------------------------
    # GENERATE UNIQUE BACKUP NAME
    # -----------------------------------------------------

    timestamp = datetime.now().strftime(
        "%Y-%m-%d_%H%M%S"
    )

    backup_filename = (
        f"zalivio_{timestamp}.db"
    )

    backup_path = os.path.join(
        BACKUP_FOLDER,
        backup_filename
    )

    source_connection = None
    backup_connection = None

    try:

        # -------------------------------------------------
        # OPEN LIVE DATABASE
        # -------------------------------------------------

        source_connection = sqlite3.connect(
            DATABASE_PATH
        )

        # -------------------------------------------------
        # CHECK LIVE DATABASE INTEGRITY
        # -------------------------------------------------

        live_integrity = (
            source_connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]
        )

        if live_integrity != "ok":

            print(
                "ERROR: Live database integrity "
                "check failed."
            )

            print(
                f"SQLite result: {live_integrity}"
            )

            return False

        print(
            "Live database integrity: OK"
        )

        # -------------------------------------------------
        # CREATE SQLITE BACKUP
        # -------------------------------------------------

        backup_connection = sqlite3.connect(
            backup_path
        )

        source_connection.backup(
            backup_connection
        )

        backup_connection.commit()

        backup_connection.close()
        backup_connection = None

        print(
            f"Backup created: {backup_filename}"
        )

        # -------------------------------------------------
        # VERIFY NEW BACKUP
        # -------------------------------------------------

        verification_connection = sqlite3.connect(
            backup_path
        )

        try:

            backup_integrity = (
                verification_connection.execute(
                    "PRAGMA integrity_check"
                ).fetchone()[0]
            )

            if backup_integrity != "ok":

                raise RuntimeError(
                    "Backup integrity check failed: "
                    f"{backup_integrity}"
                )

            product_count = (
                verification_connection.execute(
                    "SELECT COUNT(*) FROM product"
                ).fetchone()[0]
            )

            order_count = (
                verification_connection.execute(
                    'SELECT COUNT(*) FROM "order"'
                ).fetchone()[0]
            )

        finally:

            verification_connection.close()

        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        backup_size = os.path.getsize(
            backup_path
        )

        print("-" * 55)

        print(
            "Backup integrity: OK"
        )

        print(
            f"Products: {product_count}"
        )

        print(
            f"Orders: {order_count}"
        )

        print(
            f"Backup size: {backup_size} bytes"
        )

        print(
            f"Backup location: {backup_path}"
        )

        # -------------------------------------------------
        # CLEAN OLD AUTOMATIC BACKUPS
        # -------------------------------------------------

        print("-" * 55)

        cleanup_old_backups()

        print("-" * 55)

        print(
            "BACKUP COMPLETED SUCCESSFULLY"
        )

        print("=" * 55)

        return True

    except Exception as error:

        print("-" * 55)

        print(
            "BACKUP FAILED"
        )

        print(
            f"Reason: {error}"
        )

        # Remove incomplete backup.
        try:

            if os.path.isfile(
                backup_path
            ):

                os.remove(
                    backup_path
                )

        except OSError:

            pass

        print("=" * 55)

        return False

    finally:

        if backup_connection is not None:
            backup_connection.close()

        if source_connection is not None:
            source_connection.close()


# =========================================================
# RUN BACKUP
# =========================================================

if __name__ == "__main__":

    success = create_backup()

    if not success:
        raise SystemExit(1)