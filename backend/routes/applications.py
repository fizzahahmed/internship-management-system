from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from config.supabase import supabase

applications_bp = Blueprint("applications", __name__)

def _get_coordinator_department(user_id):
    res = supabase.table("coordinator_profiles").select("department").eq("user_id", user_id).execute()
    return res.data[0]["department"] if res.data else None

@applications_bp.route("/", methods=["GET"])
@jwt_required()
def get_all_applications():
    user_id = get_jwt_identity()
    dept    = _get_coordinator_department(user_id)
    result  = supabase.table("applications").select(
        "*, students(id, department, users(name, email)), "
        "internship_listings(id, title, employers(company_name))"
    ).execute()
    if dept:
        result_data = [a for a in result.data if a.get("students") and a["students"].get("department") == dept]
    else:
        result_data = result.data
    return jsonify(result_data), 200

@applications_bp.route("/my", methods=["GET"])
@jwt_required()
def get_my_applications():
    user_id = get_jwt_identity()
    student = supabase.table("students").select("id").eq("user_id", user_id).execute()
    if not student.data:
        return jsonify([]), 200
    student_id = student.data[0]["id"]
    result = supabase.table("applications").select(
        "*, internship_listings(id, title, duration_weeks, employers(company_name, industry))"
    ).eq("student_id", student_id).execute()

    # Deduplicate by listing_id — keep the latest (highest id) per listing
    seen_listings = {}
    for app in result.data:
        lid = app.get("listing_id")
        if lid not in seen_listings or app["id"] > seen_listings[lid]["id"]:
            seen_listings[lid] = app
    deduped = list(seen_listings.values())
    return jsonify(deduped), 200

@applications_bp.route("/for-employer", methods=["GET"])
@jwt_required()
def get_employer_applications():
    user_id  = get_jwt_identity()
    employer = supabase.table("employers").select("id").eq("user_id", user_id).execute()
    if not employer.data:
        return jsonify([]), 200
    employer_id = employer.data[0]["id"]
    listings    = supabase.table("internship_listings").select("id").eq("employer_id", employer_id).execute()
    if not listings.data:
        return jsonify([]), 200
    listing_ids = [l["id"] for l in listings.data]
    result = supabase.table("applications").select(
        "*, students(id, department, users(name, email)), internship_listings(title)"
    ).in_("listing_id", listing_ids).execute()
    return jsonify(result.data), 200

@applications_bp.route("/pending-dept", methods=["GET"])
@jwt_required()
def get_pending_dept_approval():
    """Applications awaiting department approval — filtered by coordinator's department."""
    user_id = get_jwt_identity()
    dept    = _get_coordinator_department(user_id)
    result  = supabase.table("applications").select(
        "*, students(id, department, users(name, email)), "
        "internship_listings(id, title, employers(company_name, industry))"
    ).eq("status", "accepted").eq("dept_approved", False).execute()
    if dept:
        filtered = [a for a in result.data if a.get("students") and a["students"].get("department") == dept]
    else:
        filtered = result.data
    return jsonify(filtered), 200

@applications_bp.route("/", methods=["POST"])
@jwt_required()
def apply():
    user_id = get_jwt_identity()
    data    = request.get_json()
    student = supabase.table("students").select("id").eq("user_id", user_id).execute()
    if not student.data:
        return jsonify({"error": "Student profile not found"}), 404
    student_id = student.data[0]["id"]

    # Prevent duplicate applications to the same listing
    existing = supabase.table("applications").select("id")\
        .eq("student_id", student_id)\
        .eq("listing_id", data.get("listing_id")).execute()
    if existing.data:
        return jsonify({"error": "Already applied to this position"}), 400

    result = supabase.table("applications").insert({
        "student_id":    student_id,
        "listing_id":    data.get("listing_id"),
        "cover_letter":  data.get("cover_letter", ""),
        "status":        "pending",
        "dept_approved": False
    }).execute()
    return jsonify(result.data), 201

@applications_bp.route("/<int:app_id>/status", methods=["PUT"])
@jwt_required()
def update_status(app_id):
    data       = request.get_json()
    new_status = data.get("status")
    result     = supabase.table("applications").update({"status": new_status}).eq("id", app_id).execute()
    if new_status == "accepted" and result.data:
        app     = result.data[0]
        listing = supabase.table("internship_listings").select("*, employers(id)").eq("id", app["listing_id"]).execute()
        if listing.data:
            l = listing.data[0]
            # Only create internship if one doesn't already exist for this student
            existing_intern = supabase.table("internships").select("id").eq("student_id", app["student_id"]).execute()
            if not existing_intern.data:
                supabase.table("internships").insert({
                    "student_id":  app["student_id"],
                    "employer_id": l["employers"]["id"],
                    "start_date":  data.get("start_date"),
                    "end_date":    data.get("end_date"),
                    "status":      "ongoing"
                }).execute()
    return jsonify(result.data), 200

@applications_bp.route("/<int:app_id>/dept-approve", methods=["PUT"])
@jwt_required()
def dept_approve(app_id):
    coordinator_id = get_jwt_identity()
    data     = request.get_json() or {}
    approved = data.get("approved", True)

    try:
        coord_id_int = int(coordinator_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid coordinator identity"}), 400

    supabase.table("applications").update({
        "dept_approved": approved,
        "dept_comments": data.get("comments", "")
    }).eq("id", app_id).execute()

    if not approved:
        return jsonify({"message": "Application rejected"}), 200

    app_res = supabase.table("applications").select("*, students(id)").eq("id", app_id).execute()
    if not app_res.data:
        return jsonify({"error": "Application not found"}), 404

    app        = app_res.data[0]
    student_id = app["student_id"]

    intern_res = supabase.table("internships").select("id").eq("student_id", student_id).execute()
    if intern_res.data:
        internship_id = intern_res.data[0]["id"]
    else:
        listing_id    = app.get("listing_id")
        internship_id = None
        if listing_id:
            listing = supabase.table("internship_listings").select("*, employers(id)").eq("id", listing_id).execute()
            if listing.data and listing.data[0].get("employers"):
                new_intern = supabase.table("internships").insert({
                    "student_id":  student_id,
                    "employer_id": listing.data[0]["employers"]["id"],
                    "start_date":  None,
                    "end_date":    None,
                    "status":      "ongoing"
                }).execute()
                if new_intern.data:
                    internship_id = new_intern.data[0]["id"]

        if not internship_id:
            return jsonify({"error": "Could not create internship record"}), 400

    existing = supabase.table("department_workflow").select("id").eq("student_id", student_id).execute()
    if not existing.data:
        supabase.table("department_workflow").insert({
            "student_id":            student_id,
            "internship_id":         internship_id,
            "coordinator_id":        coord_id_int,
            "current_stage":         "placement_setup",
            "status":                "in_progress",
            "application_submitted": True,
            "department_approval":   True,
            "placement_setup":       False,
            "internship_progress":   False,
            "employer_evaluation":   False,
            "viva_assessment":       False,
            "credit_verification":   False,
            "comments":              "Department approved. Workflow started."
        }).execute()
    else:
        supabase.table("department_workflow").update({
            "department_approval": True,
            "current_stage":       "placement_setup",
            "coordinator_id":      coord_id_int
        }).eq("student_id", student_id).execute()

    return jsonify({"message": "Done"}), 200