from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from config.supabase import supabase

internships_bp = Blueprint("internships", __name__)

@internships_bp.route("/", methods=["GET"])
@jwt_required()
def get_all_internships():
    user_id = get_jwt_identity()

    # If caller is a student — return only their internship
    student = supabase.table("students").select("id").eq("user_id", user_id).execute()
    if student.data:
        student_id = student.data[0]["id"]
        result = supabase.table("internships").select(
            "*, students(id, department, users(name, email)), employers(id, company_name)"
        ).eq("student_id", student_id).execute()
        return jsonify(result.data), 200

    # If caller is an employer — return only their interns
    employer = supabase.table("employers").select("id").eq("user_id", user_id).execute()
    if employer.data:
        employer_id = employer.data[0]["id"]
        result = supabase.table("internships").select(
            "*, students(id, department, users(name, email)), employers(id, company_name)"
        ).eq("employer_id", employer_id).execute()
        return jsonify(result.data), 200

    # Coordinator — return all
    result = supabase.table("internships").select(
        "*, students(id, department, users(name, email)), employers(id, company_name)"
    ).execute()
    return jsonify(result.data), 200


@internships_bp.route("/", methods=["POST"])
@jwt_required()
def create_internship():
    data = request.get_json()
    result = supabase.table("internships").insert({
        "student_id":  data.get("student_id"),
        "employer_id": data.get("employer_id"),
        "start_date":  data.get("start_date"),
        "end_date":    data.get("end_date"),
        "status":      "ongoing"
    }).execute()
    return jsonify(result.data), 201


@internships_bp.route("/<int:internship_id>", methods=["PUT"])
@jwt_required()
def update_internship(internship_id):
    data   = request.get_json()
    result = supabase.table("internships").update(data).eq("id", internship_id).execute()
    return jsonify(result.data), 200


@internships_bp.route("/<int:internship_id>", methods=["DELETE"])
@jwt_required()
def delete_internship(internship_id):
    supabase.table("internships").delete().eq("id", internship_id).execute()
    return jsonify({"message": "Internship deleted"}), 200


@internships_bp.route("/assign", methods=["POST"])
@jwt_required()
def assign_internship():
    data   = request.get_json()
    result = supabase.table("internships").insert({
        "student_id":  data.get("student_id"),
        "employer_id": data.get("employer_id"),
        "start_date":  data.get("start_date"),
        "end_date":    data.get("end_date"),
        "status":      "ongoing"
    }).execute()
    supabase.table("department_workflow").insert({
        "student_id":   data.get("student_id"),
        "internship_id": result.data[0]["id"],
        "status":       "pending"
    }).execute()
    return jsonify(result.data), 201