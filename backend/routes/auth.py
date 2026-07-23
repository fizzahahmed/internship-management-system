from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from config.supabase import supabase
import bcrypt
import re

auth_bp = Blueprint("auth", __name__)

ALLOWED_DEPARTMENTS  = ["Computer Science", "Software Engineering", "Information Technology"]
ALLOWED_COMPANIES    = ["TechNova Solutions", "DataBridge Corp"]
MAX_EMPLOYERS        = 2
MAX_COORDINATORS     = 3

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')

def is_valid_email(email):
    return bool(EMAIL_REGEX.match(email))

@auth_bp.route("/register", methods=["POST"])
def register():
    data         = request.get_json()
    name         = data.get("name")
    email        = data.get("email")
    password     = data.get("password")
    role         = data.get("role")
    department   = data.get("department", "")
    credit_hours = data.get("credit_hours", 120)
    company_name = data.get("company_name", "")
    industry     = data.get("industry", "")

    if not all([name, email, password, role]):
        return jsonify({"error": "All fields are required"}), 400

    if not is_valid_email(email):
        return jsonify({"error": "Invalid email format. Please enter a valid email address (e.g. name@example.com)"}), 400

    existing = supabase.table("users").select("id").eq("email", email).execute()
    if existing.data:
        return jsonify({"error": "Email already exists"}), 400

    if role == "student":
        if department not in ALLOWED_DEPARTMENTS:
            return jsonify({"error": f"Invalid department. Choose one of: {', '.join(ALLOWED_DEPARTMENTS)}"}), 400

    elif role == "employer":
        if company_name not in ALLOWED_COMPANIES:
            return jsonify({"error": f"Invalid company. Choose one of: {', '.join(ALLOWED_COMPANIES)}"}), 400
        existing_company = supabase.table("employers").select("id").eq("company_name", company_name).execute()
        if existing_company.data:
            return jsonify({"error": f"An employer account for '{company_name}' already exists."}), 400
        count_res = supabase.table("users").select("id").eq("role", "employer").execute()
        if len(count_res.data) >= MAX_EMPLOYERS:
            return jsonify({"error": f"Maximum of {MAX_EMPLOYERS} employer accounts allowed."}), 400

    elif role == "coordinator":
        if department not in ALLOWED_DEPARTMENTS:
            return jsonify({"error": f"Invalid department. Choose one of: {', '.join(ALLOWED_DEPARTMENTS)}"}), 400
        existing_coord = supabase.table("coordinator_profiles").select("id").eq("department", department).execute()
        if existing_coord.data:
            return jsonify({"error": f"A coordinator for '{department}' already exists."}), 400
        count_coord = supabase.table("users").select("id").eq("role", "coordinator").execute()
        if len(count_coord.data) >= MAX_COORDINATORS:
            return jsonify({"error": f"Maximum of {MAX_COORDINATORS} coordinator accounts allowed."}), 400
    else:
        return jsonify({"error": "Invalid role"}), 400

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user_result = supabase.table("users").insert({
        "name": name, "email": email, "password": hashed, "role": role
    }).execute()
    user_id = user_result.data[0]["id"]

    if role == "student":
        supabase.table("students").insert({
            "user_id": user_id, "department": department,
            "credit_hours": credit_hours, "status": "active"
        }).execute()
    elif role == "employer":
        supabase.table("employers").insert({
            "user_id": user_id, "company_name": company_name, "industry": industry
        }).execute()
    elif role == "coordinator":
        supabase.table("coordinator_profiles").insert({
            "user_id": user_id, "department": department
        }).execute()

    return jsonify({"message": "Account created successfully"}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data     = request.get_json()
    email    = data.get("email")
    password = data.get("password")

    result = supabase.table("users").select("*").eq("email", email).execute()
    if not result.data:
        return jsonify({"error": "User not found"}), 404

    user = result.data[0]
    if not bcrypt.checkpw(password.encode("utf-8"), user["password"].encode("utf-8")):
        return jsonify({"error": "Wrong password"}), 401

    profile_id = None
    department = None
    company_name = None

    if user["role"] == "student":
        profile = supabase.table("students").select("id, department").eq("user_id", user["id"]).execute()
        if profile.data:
            profile_id = profile.data[0]["id"]
            department = profile.data[0]["department"]
    elif user["role"] == "employer":
        profile = supabase.table("employers").select("id, company_name").eq("user_id", user["id"]).execute()
        if profile.data:
            profile_id   = profile.data[0]["id"]
            company_name = profile.data[0]["company_name"]
    elif user["role"] == "coordinator":
        profile = supabase.table("coordinator_profiles").select("id, department").eq("user_id", user["id"]).execute()
        if profile.data:
            profile_id = profile.data[0]["id"]
            department = profile.data[0]["department"]

    token = create_access_token(identity=str(user["id"]))
    return jsonify({
        "token": token, "role": user["role"], "name": user["name"],
        "id": user["id"], "profile_id": profile_id,
        "department": department, "company_name": company_name
    }), 200