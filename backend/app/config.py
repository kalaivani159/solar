import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/solarsphere",
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(PROJECT_DIR, "data")
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "knowledge_base")
REPORTS_DIR = os.path.join(BASE_DIR, "generated_reports")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

DEFAULT_DATASET = os.path.join(
    DATA_DIR, "SolarSphere_Feature3_Demo_Dataset_Location_Based.xlsx"
)

EMISSION_FACTOR_DEFAULT = 0.71
EMISSION_FACTOR_UNIT = "kg CO2 / kWh"
EMISSION_FACTOR_SOURCE = (
    "Central Electricity Authority (CEA), CO2 Baseline Database for the Indian Power Sector, "
    "weighted grid emission factor (indicative value). Configurable by the user."
)

INDEX_WEIGHTS_DEFAULT = {
    "usable_area": 25,
    "generation": 25,
    "capacity": 20,
    "economics": 15,
    "payback": 10,
    "suitability": 5,
}

for _path in (REPORTS_DIR, UPLOAD_DIR, DATA_DIR):
    os.makedirs(_path, exist_ok=True)
