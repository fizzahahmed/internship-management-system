from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from config.supabase import supabase

evaluations_bp = Blueprint("evaluations", __name__)

def _get_student_internship_ids(user_id):
    """Return list of internship IDs for a student user."""
    student = supabase.table("students").select("id").eq("user_id", user_id).execute()
    if not student.data:
        return []
    student_id = student.data[0]["id"]
    interns = supabase.table("internships").select("id").eq("student_id", student_id).execute()
    return [i["id"] for i in interns.data] if interns.data else []

def _get_employer_internship_ids(user_id):
    """Return list of internship IDs for an employer user."""
    employer = supabase.table("employers").select("id").eq("user_id", user_id).execute()
    if not employer.data:
        return []
    employer_id = employer.data[0]["id"]
    interns = supabase.table("internships").select("id").eq("employer_id", employer_id).execute()
    return [i["id"] for i in interns.data] if interns.data else []

def _get_coordinator_internship_ids(user_id):
    """Return list of internship IDs for all students in coordinator's department."""
    coord = supabase.table("coordinator_profiles").select("department").eq("user_id", user_id).execute()
    if not coord.data:
        return []
    dept = coord.data[0]["department"]
    students = supabase.table("students").select("id").eq("department", dept).execute()
    if not students.data:
        return []
    student_ids = [s["id"] for s in students.data]
    interns = supabase.table("internships").select("id").in_("student_id", student_ids).execute()
    return [i["id"] for i in interns.data] if interns.data else []


@evaluations_bp.route("/", methods=["GET"])
@jwt_required()
def get_all_evaluations():
    user_id = get_jwt_identity()

    # Determine role and get internship IDs
    internship_ids = _get_student_internship_ids(user_id)
    if not internship_ids:
        internship_ids = _get_employer_internship_ids(user_id)
    if not internship_ids:
        internship_ids = _get_coordinator_internship_ids(user_id)
    if not internship_ids:
        return jsonify([]), 200

    result = supabase.table("evaluations").select(
        "*, internships(id, student_id, employer_id)"
    ).in_("internship_id", internship_ids).execute()
    return jsonify(result.data), 200


@evaluations_bp.route("/my", methods=["GET"])
@jwt_required()
def get_my_evaluations():
    """Dedicated endpoint for students — always returns their own evaluations."""
    user_id = get_jwt_identity()
    internship_ids = _get_student_internship_ids(user_id)
    if not internship_ids:
        return jsonify([]), 200
    result = supabase.table("evaluations").select(
        "*, internships(id, student_id, employer_id)"
    ).in_("internship_id", internship_ids).execute()
    return jsonify(result.data), 200


@evaluations_bp.route("/", methods=["POST"])
@jwt_required()
def submit_evaluation():
    data = request.get_json()
    internship_id = data.get("internship_id")

    existing = supabase.table("evaluations").select("id").eq("internship_id", internship_id).execute()
    if existing.data:
        return jsonify({"error": "Evaluation already submitted for this student"}), 400

    result = supabase.table("evaluations").insert({
        "internship_id": internship_id,
        "score":         data.get("score"),
        "comments":      data.get("comments", "")
    }).execute()
    return jsonify(result.data), 201