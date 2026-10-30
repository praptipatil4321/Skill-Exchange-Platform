import hashlib
import mimetypes
import os
import re
import uuid

from flask import (
    Blueprint, render_template, request, jsonify, abort, current_app, url_for, send_from_directory,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from extensions import db
from models import ExchangeRequest, Message

chat_bp = Blueprint("chat", __name__, url_prefix="/messages")


def _get_authorized_exchange(exchange_id):
    """Fetch an exchange request and make sure the current user is allowed to
    chat about it: they must be one of the two participants, and the request
    must have been accepted by both sides."""
    exchange = ExchangeRequest.query.get_or_404(exchange_id)
    if not exchange.is_participant(current_user.id):
        abort(403)
    if exchange.status != "accepted":
        abort(403)
    return exchange


def _video_room_name(exchange_id):
    """Deterministic-but-unguessable Jitsi room name, unique per exchange."""
    salt = current_app.config["SECRET_KEY"]
    digest = hashlib.sha256(f"skillexchange-{exchange_id}-{salt}".encode()).hexdigest()[:16]
    return f"SkillExchange-{exchange_id}-{digest}"


# MIME types that are safe to display inline in the browser. Everything else
# (html, svg, js, exe, zip, docx, ...) is always forced to download, so an
# uploaded file can never execute as a script on this site.
INLINE_SAFE_MIMES = {
    "image/png", "image/jpeg", "image/gif", "image/webp", "image/bmp", "image/avif",
    "video/mp4", "video/webm", "video/ogg", "video/quicktime",
    "audio/mpeg", "audio/wav", "audio/x-wav", "audio/ogg", "audio/webm", "audio/mp4",
    "audio/aac", "audio/flac", "audio/x-m4a",
    "application/pdf",
}


def _human_size(num_bytes):
    size = float(num_bytes or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{int(size)} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def _kind(mime):
    if mime.startswith("image/") and mime in INLINE_SAFE_MIMES:
        return "image"
    if mime.startswith("video/") and mime in INLINE_SAFE_MIMES:
        return "video"
    if mime.startswith("audio/") and mime in INLINE_SAFE_MIMES:
        return "audio"
    if mime == "application/pdf":
        return "pdf"
    return "file"


def _save_attachment(file_storage, exchange_id):
    """Store any uploaded file privately. Returns (info_dict, error)."""
    original = os.path.basename((file_storage.filename or "").replace("\\", "/")).strip()
    if not original:
        return None, "The selected file has no name."
    display_name = original[:200]

    # Extension only; the stored name is a random UUID so nothing user-controlled
    # ever touches the filesystem path.
    ext = os.path.splitext(original)[1].lower()
    ext = re.sub(r"[^a-z0-9.]", "", ext)[:12]
    stored = f"{uuid.uuid4().hex}{ext}"

    folder = os.path.join(current_app.config["CHAT_FILES_FOLDER"], str(exchange_id))
    os.makedirs(folder, exist_ok=True)
    full_path = os.path.join(folder, stored)
    file_storage.save(full_path)

    size = os.path.getsize(full_path)
    if size == 0:
        os.remove(full_path)
        return None, "That file is empty."

    mime = mimetypes.guess_type(original)[0] or "application/octet-stream"
    return {
        "file_path": f"{exchange_id}/{stored}",
        "file_name": display_name,
        "file_mime": mime,
        "file_size": size,
    }, None


def _attachment_dict(message):
    """Describe a message's attachment (or None). Handles legacy image_path rows."""
    if message.file_path:
        mime = message.file_mime or "application/octet-stream"
        return {
            "url": url_for("chat.get_file", exchange_id=message.exchange_request_id, message_id=message.id),
            "name": message.file_name or "file",
            "size_label": _human_size(message.file_size),
            "kind": _kind(mime),
            "mime": mime,
        }
    if message.image_path:
        return {
            "url": url_for("static", filename=message.image_path),
            "name": os.path.basename(message.image_path),
            "size_label": "",
            "kind": "image",
            "mime": "image/*",
        }
    return None


@chat_bp.app_context_processor
def _inject_helpers():
    return {"attachment_of": _attachment_dict}


def _message_dict(message, current_user_id):
    return {
        "id": message.id,
        "body": message.body,
        "attachment": _attachment_dict(message),
        "sender_id": message.sender_id,
        "sender_username": message.sender.username,
        "created_at": message.created_at.strftime("%b %d, %I:%M %p"),
        "mine": message.sender_id == current_user_id,
    }


@chat_bp.route("/")
@login_required
def conversations():
    exchanges = (
        ExchangeRequest.query.filter(
            ExchangeRequest.status == "accepted",
            (ExchangeRequest.sender_id == current_user.id)
            | (ExchangeRequest.receiver_id == current_user.id),
        )
        .order_by(ExchangeRequest.created_at.desc())
        .all()
    )

    conversations_data = []
    for exchange in exchanges:
        last_message = (
            Message.query.filter_by(exchange_request_id=exchange.id)
            .order_by(Message.created_at.desc())
            .first()
        )
        unread_count = Message.query.filter(
            Message.exchange_request_id == exchange.id,
            Message.sender_id != current_user.id,
            Message.is_read.is_(False),
        ).count()
        conversations_data.append(
            {
                "exchange": exchange,
                "other_user": exchange.other_user(current_user.id),
                "last_message": last_message,
                "unread_count": unread_count,
            }
        )

    return render_template("messages_list.html", conversations=conversations_data)


@chat_bp.route("/<int:exchange_id>")
@login_required
def conversation(exchange_id):
    exchange = _get_authorized_exchange(exchange_id)
    other_user = exchange.other_user(current_user.id)
    messages = (
        Message.query.filter_by(exchange_request_id=exchange.id)
        .order_by(Message.created_at.asc())
        .all()
    )

    # Mark incoming messages as read now that the user has opened the thread.
    unread = [m for m in messages if m.sender_id != current_user.id and not m.is_read]
    if unread:
        for m in unread:
            m.is_read = True
        db.session.commit()

    return render_template(
        "chat.html",
        exchange=exchange,
        other_user=other_user,
        messages=messages,
        video_room=_video_room_name(exchange.id),
    )


@chat_bp.route("/<int:exchange_id>/send", methods=["POST"])
@login_required
def send_message(exchange_id):
    exchange = _get_authorized_exchange(exchange_id)

    body = (request.form.get("body") or "").strip()
    upload = request.files.get("file") or request.files.get("image")

    attachment = None
    if upload and upload.filename:
        attachment, error = _save_attachment(upload, exchange.id)
        if error:
            return jsonify({"error": error}), 400

    if not body and not attachment:
        return jsonify({"error": "Message cannot be empty."}), 400
    if body and len(body) > 2000:
        return jsonify({"error": "Message is too long (max 2000 characters)."}), 400

    message = Message(
        exchange_request_id=exchange.id,
        sender_id=current_user.id,
        body=body or None,
        **(attachment or {}),
    )
    db.session.add(message)
    db.session.commit()

    return jsonify(_message_dict(message, current_user.id))


@chat_bp.route("/<int:exchange_id>/file/<int:message_id>")
@login_required
def get_file(exchange_id, message_id):
    exchange = _get_authorized_exchange(exchange_id)
    message = Message.query.get_or_404(message_id)
    if message.exchange_request_id != exchange.id or not message.file_path:
        abort(404)

    mime = message.file_mime or "application/octet-stream"
    force_download = request.args.get("download") == "1" or mime not in INLINE_SAFE_MIMES

    response = send_from_directory(
        current_app.config["CHAT_FILES_FOLDER"],
        message.file_path,
        mimetype=mime,
        as_attachment=force_download,
        download_name=message.file_name or "file",
        conditional=True,  # enables Range requests so video/audio can seek
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "private, max-age=3600"
    return response


@chat_bp.route("/<int:exchange_id>/poll")
@login_required
def poll_messages(exchange_id):
    exchange = _get_authorized_exchange(exchange_id)
    after_id = request.args.get("after", 0, type=int)

    new_messages = (
        Message.query.filter(
            Message.exchange_request_id == exchange.id,
            Message.id > after_id,
        )
        .order_by(Message.created_at.asc())
        .all()
    )

    # Mark any incoming messages the poller hasn't seen yet as read, since
    # they're actively viewing the conversation.
    changed = False
    for m in new_messages:
        if m.sender_id != current_user.id and not m.is_read:
            m.is_read = True
            changed = True
    if changed:
        db.session.commit()

    return jsonify({"messages": [_message_dict(m, current_user.id) for m in new_messages]})


@chat_bp.route("/notifications/summary")
@login_required
def notifications_summary():
    """Lightweight counts used to render red-dot badges in the nav bar."""
    unread_messages = (
        Message.query.join(ExchangeRequest, Message.exchange_request_id == ExchangeRequest.id)
        .filter(
            (ExchangeRequest.sender_id == current_user.id)
            | (ExchangeRequest.receiver_id == current_user.id),
            Message.sender_id != current_user.id,
            Message.is_read.is_(False),
        )
        .count()
    )
    pending_requests = ExchangeRequest.query.filter_by(
        receiver_id=current_user.id, status="pending"
    ).count()

    return jsonify({"unread_messages": unread_messages, "pending_requests": pending_requests})
