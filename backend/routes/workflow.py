from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from config.supabase import supabase
from datetime import datetime

workflow_bp = Blueprint("workflow", __name__)

STAGES = [
    "application_submitted",
    "department_approval",
    "placement_setup",
    "internship_progress",
    "employer_evaluation",
    "viva_assessment",
    "credit_verification"
]

def _get_coordinator_department(user_id):
    """Return the department string for a coordinator, or None."""
    res = supabase.table("coordinator_profiles").select("department").eq("user_id", user_id).execute()
    return res.data[0]["department"] if res.data else None

@workflow_bp.route("/", methods=["GET"])
@jwt_required()
def get_all_workflows():
    user_id = get_jwt_identity()
    dept = _get_coordinator_department(user_id)

    result = supabase.table("department_workflow").select(
        "*, students(id, department, credit_hours, users(name, email)), "
        "internships(id, status, employers(company_name, industry))"
    ).execute()

    if dept:
        # Post-filter by coordinator's department
        filtered = [w for w in result.data if w.get("students") and w["students"].get("department") == dept]
        return jsonify(filtered), 200

    return jsonify(result.data), 200

@workflow_bp.route("/student/<int:student_id>", methods=["GET"])
@jwt_required()
def get_student_workflow(student_id):
    result = supabase.table("department_workflow").select("*").eq("student_id", student_id).execute()
    if not result.data:
        return jsonify(None), 200
    return jsonify(result.data[0]), 200

@workflow_bp.route("/my", methods=["GET"])
@jwt_required()
def get_my_workflow():
    user_id = get_jwt_identity()
    student = supabase.table("students").select("id").eq("user_id", user_id).execute()
    if not student.data:
        return jsonify(None), 200
    student_id = student.data[0]["id"]
    result = supabase.table("department_workflow").select("*").eq("student_id", student_id).execute()
    if not result.data:
        return jsonify(None), 200
    return jsonify(result.data[0]), 200

@workflow_bp.route("/", methods=["POST"])
@jwt_required()
def create_workflow():
    data = request.get_json()
    existing = supabase.table("department_workflow").select("id").eq("student_id", data.get("student_id")).execute()
    if existing.data:
        return jsonify({"error": "Workflow already exists for this student"}), 400
    result = supabase.table("department_workflow").insert({
        "student_id":            data.get("student_id"),
        "internship_id":         data.get("internship_id"),
        "current_stage":         "application_submitted",
        "status":                "active",
        "application_submitted": True,
        "department_approval":   False,
        "placement_setup":       False,
        "internship_progress":   False,
        "employer_evaluation":   False,
        "viva_assessment":       False,
        "credit_verification":   False,
        "comments":              "",
        "coordinator_id":        None
    }).execute()
    # BUG FIX: was missing return — caused 500 errors on every workflow creation
    return jsonify(result.data), 201

@workflow_bp.route("/<int:workflow_id>/advance", methods=["PUT"])
@jwt_required()
def advance_stage(workflow_id):
    coordinator_id = get_jwt_identity()
    data     = request.get_json() or {}
    stage    = data.get("stage")
    comments = data.get("comments", "")
    extra    = data.get("extra", {})

    if stage not in STAGES:
        return jsonify({"error": "Invalid stage"}), 400

    idx        = STAGES.index(stage)
    next_stage = STAGES[idx + 1] if idx + 1 < len(STAGES) else "completed"

    update_payload = {
        stage:            True,
        "current_stage":  next_stage,
        "coordinator_id": int(coordinator_id),
        "comments":       comments,
        "updated_at":     datetime.now().isoformat()
    }
    if extra:
        update_payload.update(extra)
    if next_stage == "completed":
        update_payload["status"] = "approved"

    result = supabase.table("department_workflow").update(update_payload).eq("id", workflow_id).execute()
    return jsonify(result.data), 200

@workflow_bp.route("/<int:workflow_id>/reject", methods=["PUT"])
@jwt_required()
def reject_stage(workflow_id):
    coordinator_id = get_jwt_identity()
    data = request.get_json() or {}
    result = supabase.table("department_workflow").update({
        "status":         "rejected",
        "comments":       data.get("comments", "Rejected by coordinator"),
        "coordinator_id": int(coordinator_id),
        "updated_at":     datetime.now().isoformat()
    }).eq("id", workflow_id).execute()
    return jsonify(result.data), 200

@workflow_bp.route("/<int:workflow_id>/report", methods=["POST"])
@jwt_required()
def submit_report(workflow_id):
    user_id = get_jwt_identity()
    data = request.get_json()
    student_res = supabase.table("students").select("id").eq("user_id", user_id).execute()
    student_id  = student_res.data[0]["id"] if student_res.data else None
    result = supabase.table("progress_reports").insert({
        "workflow_id":  workflow_id,
        "student_id":   student_id,
        "report_text":  data.get("report_text", ""),
        "file_name":    data.get("file_name", ""),
        "approved":     False,
        "submitted_at": datetime.now().isoformat()
    }).execute()
    return jsonify(result.data), 201

@workflow_bp.route("/<int:workflow_id>/reports", methods=["GET"])
@jwt_required()
def get_reports(workflow_id):
    result = supabase.table("progress_reports").select("*").eq("workflow_id", workflow_id).order("submitted_at", desc=True).execute()
    return jsonify(result.data), 200

@workflow_bp.route("/<int:workflow_id>/approve-report/<int:report_id>", methods=["PUT"])
@jwt_required()
def approve_report(workflow_id, report_id):
    result = supabase.table("progress_reports").update({"approved": True}).eq("id", report_id).execute()
    # BUG FIX: was missing .eq("id", workflow_id).execute() — the update was never saved
    supabase.table("department_workflow").update({
        "internship_progress": True,
        "updated_at": datetime.now().isoformat()
    }).eq("id", workflow_id).execute()
    return jsonify(result.data), 200