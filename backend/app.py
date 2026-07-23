from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")


CORS(app, supports_credentials=True)
jwt = JWTManager(app)

from routes.auth import auth_bp
from routes.students import students_bp
from routes.employers import employers_bp
from routes.internships import internships_bp
from routes.evaluations import evaluations_bp
from routes.viva import viva_bp
from routes.workflow import workflow_bp
from routes.credit import credit_bp
from routes.applications import applications_bp
from routes.listings import listings_bp

app.register_blueprint(listings_bp, url_prefix="/api/listings")
app.register_blueprint(applications_bp, url_prefix="/api/applications")
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(students_bp, url_prefix="/api/students")
app.register_blueprint(employers_bp, url_prefix="/api/employers")
app.register_blueprint(internships_bp, url_prefix="/api/internships")
app.register_blueprint(evaluations_bp, url_prefix="/api/evaluations")
app.register_blueprint(viva_bp, url_prefix="/api/viva")
app.register_blueprint(workflow_bp, url_prefix="/api/workflow")
app.register_blueprint(credit_bp, url_prefix="/api/credit")

if __name__ == "__main__":
    app.run(debug=True)