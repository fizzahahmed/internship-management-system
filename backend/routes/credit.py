from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from config.supabase import supabase

credit_bp = Blueprint("credit", __name__)

def _get_coordinator_department(user_id):
    res = supabase.table("coordinator_profiles").select("department").eq("user_id", user_id).execute()
    return res.data[0]["department"] if res.data else None

@credit_bp.route("/", methods=["GET"])
@jwt_required()
def get_all_credits():
    user_id = get_jwt_identity()
    dept    = _get_coordinator_department(user_id)
    result  = supabase.table("credit_verifications").select(
        "*, students(id, department, credit_hours, users(name, email))"
    ).execute()
    if dept:
        # Filter so coordinator only sees their own dept students
        filtered = [c for c in result.data if c.get("students") and c["students"].get("department") == dept]
        return jsonify(filtered), 200
    return jsonify(result.data), 200

@credit_bp.route("/pending", methods=["GET"])
@jwt_required()
def get_pending_credits():
    """Get all students who have completed internships but credit not yet verified,
    filtered by the coordinator's department."""
    user_id = get_jwt_identity()
    dept    = _get_coordinator_department(user_id)

    # Get all internships
    internships = supabase.table("internships").select(
        "*, students(id, department, credit_hours, users(name, email)), employers(company_name)"
    ).execute()

    # Get existing credit verifications (all, to exclude already-initiated)
    verifications = supabase.table("credit_verifications").select("student_id").execute()
    verified_ids  = {v["student_id"] for v in verifications.data}

    # Return internships for students not yet verified AND in coordinator's dept
    pending = []
    for i in internships.data:
        if i.get("student_id") in verified_ids:
            continue
        student_dept = i.get("students", {}).get("department") if i.get("students") else None
        if dept and student_dept != dept:
            continue
        pending.append(i)
    return jsonify(pending), 200

@credit_bp.route("/", methods=["POST"])
@jwt_required()
def create_credit():
    data = request.get_json()
    # Check if already exists to prevent duplicates
    existing = supabase.table("credit_verifications").select("id").eq("student_id", data.get("student_id")).execute()
    if existing.data:
        return jsonify({"error": "Credit verification already exists for this student"}), 400
    result = supabase.table("credit_verifications").insert({
        "student_id":      data.get("student_id"),
        "required_hours":  data.get("required_hours", 120),
        "completed_hours": data.get("completed_hours", 0),
        "verified":        False
    }).execute()
    return jsonify(result.data), 201

@credit_bp.route("/<int:credit_id>/verify", methods=["PUT"])
@jwt_required()
def verify_credit(credit_id):
    coordinator_id = get_jwt_identity()
    from datetime import datetime
    data = request.get_json() or {}
    result = supabase.table("credit_verifications").update({
        "verified":        True,
        "completed_hours": data.get("completed_hours"),
        "verified_by":     int(coordinator_id),
        "verified_at":     datetime.now().isoformat()
    }).eq("id", credit_id).execute()
    return jsonify(result.data), 200

@credit_bp.route("/<int:credit_id>/reject", methods=["PUT"])
@jwt_required()
def reject_credit(credit_id):
    result = supabase.table("credit_verifications").update({
        "verified": False
    }).eq("id", credit_id).execute()
    return jsonify(result.data), 200

@credit_bp.route("/initiate", methods=["POST"])
@jwt_required()
def initiate_credit():
    """HOD initiates credit verification for a student after internship."""
    data          = request.get_json()
    student_id    = data.get("student_id")
    internship_id = data.get("internship_id")

    # Prevent duplicate initiation
    existing = supabase.table("credit_verifications").select("id").eq("student_id", student_id).execute()
    if existing.data:
        # Return existing record's id so the caller can proceed to /verify
        return jsonify(existing.data), 200

    # Calculate completed hours from internship dates
    internship      = supabase.table("internships").select("*").eq("id", internship_id).execute()
    completed_hours = 0
    if internship.data:
        i = internship.data[0]
        if i.get("start_date") and i.get("end_date"):
            from datetime import date
            start           = date.fromisoformat(i["start_date"])
            end             = date.fromisoformat(i["end_date"])
            weeks           = (end - start).days / 7
            completed_hours = int(weeks * 40)  # 40 hrs/week

    # Get student credit_hours requirement
    student  = supabase.table("students").select("credit_hours").eq("id", student_id).execute()
    required = student.data[0]["credit_hours"] if student.data else 120

    result = supabase.table("credit_verifications").insert({
        "student_id":      student_id,
        "required_hours":  required,
        "completed_hours": completed_hours,
        "verified":        False
    }).execute()
    return jsonify(result.data), 201