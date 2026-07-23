from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from config.supabase import supabase

employers_bp = Blueprint("employers", __name__)

@employers_bp.route("/", methods=["GET"])
@jwt_required()
def get_all_employers():
    result = supabase.table("employers").select("*, users(name, email)").execute()
    return jsonify(result.data), 200

@employers_bp.route("/", methods=["POST"])
@jwt_required()
def create_employer():
    data = request.get_json()
    result = supabase.table("employers").insert({
        "user_id": data.get("user_id"),
        "company_name": data.get("company_name"),
        "industry": data.get("industry")
    }).execute()
    return jsonify(result.data), 201

@employers_bp.route("/<int:employer_id>", methods=["PUT"])
@jwt_required()
def update_employer(employer_id):
    data = request.get_json()
    result = supabase.table("employers").update(data).eq("id", employer_id).execute()
    return jsonify(result.data), 200

@employers_bp.route("/<int:employer_id>", methods=["DELETE"])
@jwt_required()
def delete_employer(employer_id):
    supabase.table("employers").delete().eq("id", employer_id).execute()
    return jsonify({"message": "Employer deleted"}), 200