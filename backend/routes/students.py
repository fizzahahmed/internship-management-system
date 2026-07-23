from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from config.supabase import supabase

students_bp = Blueprint("students", __name__)

def _get_coordinator_department(user_id):
    res = supabase.table("coordinator_profiles").select("department").eq("user_id", user_id).execute()
    return res.data[0]["department"] if res.data else None

@students_bp.route("/", methods=["GET"])
@jwt_required()
def get_all_students():
    user_id = get_jwt_identity()
    dept    = _get_coordinator_department(user_id)
    if dept:
        result = supabase.table("students").select("*, users(name, email)").eq("department", dept).execute()
    else:
        result = supabase.table("students").select("*, users(name, email)").execute()
    return jsonify(result.data), 200

@students_bp.route("/<int:student_id>", methods=["GET"])
@jwt_required()
def get_student(student_id):
    result = supabase.table("students").select("*, users(name, email)").eq("id", student_id).execute()
    if not result.data:
        return jsonify({"error": "Student not found"}), 404
    return jsonify(result.data[0]), 200

@students_bp.route("/", methods=["POST"])
@jwt_required()
def create_student():
    data   = request.get_json()
    result = supabase.table("students").insert({
        "user_id":      data.get("user_id"),
        "department":   data.get("department"),
        "credit_hours": data.get("credit_hours"),
        "status":       "active"
    }).execute()
    return jsonify(result.data), 201

@students_bp.route("/<int:student_id>", methods=["PUT"])
@jwt_required()
def update_student(student_id):
    data   = request.get_json()
    result = supabase.table("students").update(data).eq("id", student_id).execute()
    return jsonify(result.data), 200

@students_bp.route("/<int:student_id>", methods=["DELETE"])
@jwt_required()
def delete_student(student_id):
    supabase.table("students").delete().eq("id", student_id).execute()
    return jsonify({"message": "Student deleted"}), 200