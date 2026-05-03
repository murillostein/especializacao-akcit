from flask import Blueprint, jsonify, render_template, request

from .services.password_service import PasswordGenerationError, PasswordService

web = Blueprint("web", __name__)


@web.get("/")
def index():
    return render_template("index.html")


@web.post("/api/passwords")
def generate_password():
    payload = request.get_json(silent=True) or {}

    try:
        password = PasswordService.generate(
            length=payload.get("length"),
            use_uppercase=payload.get("use_uppercase", True),
            use_lowercase=payload.get("use_lowercase", True),
            use_digits=payload.get("use_digits", True),
            use_symbols=payload.get("use_symbols", True),
        )
    except PasswordGenerationError as exc:
        return jsonify({"error": str(exc)}), 400

    strength = PasswordService.evaluate_strength(password)
    return jsonify({"password": password, "strength": strength})
