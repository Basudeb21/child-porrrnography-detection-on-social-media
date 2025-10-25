# save_to_mysql.py
import mysql.connector
from config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
from datetime import datetime

def insert_attachment(data: dict):
    """
    Insert the processed JSON into the `attachments` table.
    """
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data["created_at"] = now
    data["updated_at"] = now

    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )
    cursor = conn.cursor()

    sql = """
        INSERT INTO attachments (
            id, filename, driver, type, user_id, post_id, story_id, message_id,
            collab_id, coconut_id, has_thumbnail, has_blurred_preview,
            payment_request_id, is_personal_details_detected, blur_applied,
            minor_detected, nsfw_detected, flagged_by_ai, animal_detected,
            is_reported, report_status, report_create_date,
            admin_verified_status, moderator_notes, is_deleted,
            created_at, updated_at
        ) VALUES (
            %(id)s, %(filename)s, %(driver)s, %(type)s, %(user_id)s, %(post_id)s,
            %(story_id)s, %(message_id)s, %(collab_id)s, %(coconut_id)s,
            %(has_thumbnail)s, %(has_blurred_preview)s, %(payment_request_id)s,
            %(is_personal_details_detected)s, %(blur_applied)s, %(minor_detected)s,
            %(nsfw_detected)s, %(flagged_by_ai)s, %(animal_detected)s,
            %(is_reported)s, %(report_status)s, %(report_create_date)s,
            %(admin_verified_status)s, %(moderator_notes)s, %(is_deleted)s,
            %(created_at)s, %(updated_at)s
        )
    """

    cursor.execute(sql, data)
    conn.commit()
    cursor.close()
    conn.close()
