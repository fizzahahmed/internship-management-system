from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from config.supabase import supabase

listings_bp = Blueprint("listings", __name__)

@listings_bp.route("/", methods=["GET"])
@jwt_required()
def get_all_listings():
    """Return open listings — filtered by student's department if target_department is set."""
    user_id = get_jwt_identity()

    # Get student's department (if caller is a student)
    student = supabase.table("students").select("department").eq("user_id", user_id).execute()
    student_dept = student.data[0]["department"] if student.data else None

    result = supabase.table("internship_listings").select(
        "*, employers(company_name, industry)"
    ).eq("status", "open").execute()

    listings = result.data or []

    # Filter: show listing if target_department is blank/null (open to all)
    # OR if it matches the student's department exactly
    if student_dept:
        listings = [
            l for l in listings
            if not l.get("target_department") or l["target_department"] == student_dept
        ]

    return jsonify(listings), 200


@listings_bp.route("/my", methods=["GET"])
@jwt_required()
def get_my_listings():
    user_id  = get_jwt_identity()
    employer = supabase.table("employers").select("id").eq("user_id", user_id).execute()
    if not employer.data:
        return jsonify([]), 200
    employer_id = employer.data[0]["id"]
    result = supabase.table("internship_listings").select("*").eq("employer_id", employer_id).execute()
    return jsonify(result.data), 200


@listings_bp.route("/", methods=["POST"])
@jwt_required()
def create_listing():
    user_id  = get_jwt_identity()
    employer = supabase.table("employers").select("id").eq("user_id", user_id).execute()
    if not employer.data:
        return jsonify({"error": "Employer profile not found"}), 404
    employer_id = employer.data[0]["id"]
    data = request.get_json()
    result = supabase.table("internship_listings").insert({
        "employer_id":        employer_id,
        "title":              data.get("title"),
        "description":        data.get("description", ""),
        "required_skills":    data.get("required_skills", ""),
        "target_department":  data.get("target_department", ""),
        "duration_weeks":     data.get("duration_weeks", 8),
        "positions":          data.get("positions", 1),
        "status":             "open"
    }).execute()
    return jsonify(result.data), 201


@listings_bp.route("/<int:listing_id>", methods=["PUT"])
@jwt_required()
def update_listing(listing_id):
    data   = request.get_json()
    result = supabase.table("internship_listings").update(data).eq("id", listing_id).execute()
    return jsonify(result.data), 200


@listings_bp.route("/<int:listing_id>", methods=["DELETE"])
@jwt_required()
def delete_listing(listing_id):
    supabase.table("internship_listings").delete().eq("id", listing_id).execute()
    return jsonify({"message": "Listing deleted"}), 200