import os
import requests
import zipfile
from io import BytesIO
from datetime import datetime
from dateutil.relativedelta import relativedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
RAW_PATH = os.path.join(BASE_DIR, "data", "raw_csv")

os.makedirs(RAW_PATH, exist_ok=True)

BASE_URL = "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/"

# gerar lista com n meses
def gerar_lista_meses(n_months=24):
    today = datetime.today()
    months = []

    for i in range(n_months):
        month = today - relativedelta(months=i)
        months.append(month.strftime("%Y%m"))

    return sorted(months)


def download_arq():
    months = gerar_lista_meses(24)

    for m in months:
        zip_name = f"inf_diario_fi_{m}.zip"
        csv_name = f"inf_diario_fi_{m}.csv"

        zip_path = os.path.join(RAW_PATH, zip_name)
        csv_path = os.path.join(RAW_PATH, csv_name)

        # evita baixar de novo
        if os.path.exists(csv_path):
            print(f"Já existe: {csv_name}")
            continue

        url = BASE_URL + zip_name

        print(f"Baixando: {zip_name}")

        response = requests.get(url)

        if response.status_code == 200:
            with zipfile.ZipFile(BytesIO(response.content)) as z:
                z.extractall(RAW_PATH)
                print(f"Extraído: {csv_name}")
        else:
            print(f"Erro ao baixar {zip_name}")

if __name__ == "__main__":
    download_arq()