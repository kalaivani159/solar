import os

from dotenv import load_dotenv

load_dotenv()

IS_VERCEL = bool(os.environ.get("VERCEL"))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(PROJECT_DIR, "data")
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "knowledge_base")
BUNDLED_DATA_DIR = os.path.join(BASE_DIR, "data")
BUNDLED_UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

DEMO_DATASET_FILENAME = "SolarSphere_Feature3_Demo_Dataset_Location_Based.xlsx"


def _temp_root() -> str:
    if IS_VERCEL:
        return "/tmp"
    return (
        os.environ.get("TEMP")
        or os.environ.get("TMP")
        or os.path.join(BASE_DIR, ".tmp")
    )


def _writable_dir(preferred: str, name: str) -> str:
    if not IS_VERCEL:
        try:
            os.makedirs(preferred, exist_ok=True)
            if os.access(preferred, os.W_OK):
                return preferred
        except OSError:
            pass
    path = os.path.join(_temp_root(), "solarsphere", name)
    os.makedirs(path, exist_ok=True)
    return path


def _database_url() -> str:
    url = (os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or "").strip()
    if not url:
        if IS_VERCEL:
            return "sqlite:///" + os.path.join(_temp_root(), "solarsphere.db")
        return "postgresql+psycopg2://postgres:postgres@localhost:5432/solarsphere"
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://") :]
    return url


DATABASE_URL = _database_url()

REPORTS_DIR = _writable_dir(os.path.join(BASE_DIR, "generated_reports"), "generated_reports")
UPLOAD_DIR = _writable_dir(BUNDLED_UPLOAD_DIR, "uploads")

DEFAULT_DATASET = next(
    (
        path
        for path in (
            os.path.join(DATA_DIR, DEMO_DATASET_FILENAME),
            os.path.join(BUNDLED_DATA_DIR, DEMO_DATASET_FILENAME),
            os.path.join(BUNDLED_UPLOAD_DIR, DEMO_DATASET_FILENAME),
        )
        if os.path.exists(path)
    ),
    os.path.join(DATA_DIR, DEMO_DATASET_FILENAME),
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
