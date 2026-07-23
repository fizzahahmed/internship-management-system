from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from config.supabase import supabase

viva_bp = Blueprint("viva", __name__)

def _get_coordinator_department(user_id):
    res = supabase.table("coordinator_profiles").select("department").eq("user_id", user_id).execute()
    return res.data[0]["department"] if res.data else None

@viva_bp.route("/", methods=["GET"])
@jwt_required()
def get_all_viva():
    user_id = get_jwt_identity()
    dept    = _get_coordinator_department(user_id)
    result  = supabase.table("viva_assessments").select(
        "*, students(id, department, users(name, email))"
    ).execute()
    if dept:
        filtered = [v for v in result.data if v.get("students") and v["students"].get("department") == dept]
        return jsonify(filtered), 200
    return jsonify(result.data), 200

@viva_bp.route("/my", methods=["GET"])
@jwt_required()
def get_my_viva():
    user_id = get_jwt_identity()
    student = supabase.table("students").select("id").eq("user_id", user_id).execute()
    if not student.data:
        return jsonify([]), 200
    student_id = student.data[0]["id"]
    result     = supabase.table("viva_assessments").select("*").eq("student_id", student_id).execute()
    return jsonify(result.data), 200

@viva_bp.route("/", methods=["POST"])
@jwt_required()
def create_viva():
    data   = request.get_json()
    result = supabase.table("viva_assessments").insert({
        "student_id":      data.get("student_id"),
        "date":            data.get("date"),
        "marks":           None,
        "remarks":         data.get("remarks", ""),
        "assessment_type": data.get("assessment_type", "written"),
        "questions":       data.get("questions", "")
    }).execute()
    return jsonify(result.data), 201

@viva_bp.route("/<int:viva_id>", methods=["PUT"])
@jwt_required()
def update_viva(viva_id):
    data   = request.get_json()
    result = supabase.table("viva_assessments").update(data).eq("id", viva_id).execute()
    return jsonify(result.data), 200

@viva_bp.route("/<int:viva_id>/grade", methods=["PUT"])
@jwt_required()
def grade_viva(viva_id):
    data   = request.get_json()
    marks  = data.get("marks")
    if marks is None:
        return jsonify({"error": "Marks required"}), 400
    result = supabase.table("viva_assessments").update({
        "marks":   int(marks),
        "remarks": data.get("remarks", "")
    }).eq("id", viva_id).execute()
    return jsonify(result.data), 200

@viva_bp.route("/<int:viva_id>/submit", methods=["POST"])
@jwt_required()
def submit_viva(viva_id):
    user_id = get_jwt_identity()
    data    = request.get_json()
    student = supabase.table("students").select("id").eq("user_id", user_id).execute()
    if not student.data:
        return jsonify({"error": "Student not found"}), 404
    student_id = student.data[0]["id"]
    existing   = supabase.table("viva_submissions").select("id").eq("viva_id", viva_id).eq("student_id", student_id).execute()
    if existing.data:
        return jsonify({"error": "Already submitted"}), 400
    result = supabase.table("viva_submissions").insert({
        "viva_id":    viva_id,
        "student_id": student_id,
        "answers":    data.get("answers"),
        "file_url":   data.get("file_url", "")
    }).execute()
    return jsonify(result.data), 201

@viva_bp.route("/<int:viva_id>/submissions", methods=["GET"])
@jwt_required()
def get_submissions(viva_id):
    result = supabase.table("viva_submissions").select(
        "*, students(id, users(name, email))"
    ).eq("viva_id", viva_id).execute()
    return jsonify(result.data), 200