import os
import requests
import zipfile
from io import BytesIO
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
RAW_PATH = os.path.join(BASE_DIR, "data", "raw_csv")

os.makedirs(RAW_PATH, exist_ok=True)

BASE_URL = "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/"
REGISTRY_URL = "https://dados.cvm.gov.br/dados/FI/CAD/DADOS/registro_fundo_classe.zip"
REGISTRY_OUTPUT_NAME = "registro_classe.csv"

# gerar lista com n meses
def gerar_lista_meses(n_months=24):
    today = datetime.today()
    months = []

    for i in range(n_months):
        month_index = today.year * 12 + today.month - 1 - i
        year = month_index // 12
        month = month_index % 12 + 1
        month = datetime(year, month, 1)
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


def download_registro_classe():
    output_path = os.path.join(RAW_PATH, REGISTRY_OUTPUT_NAME)

    if os.path.exists(output_path):
        print(f"Já existe: {REGISTRY_OUTPUT_NAME}")
        return

    print("Baixando: registro_fundo_classe.zip")
    response = requests.get(REGISTRY_URL)

    if response.status_code != 200:
        print("Erro ao baixar registro_fundo_classe.zip")
        return

    with zipfile.ZipFile(BytesIO(response.content)) as z:
        members = [name for name in z.namelist() if name.lower().endswith(".csv")]
        if not members:
            print("Nenhum CSV encontrado em registro_fundo_classe.zip")
            return

        source_name = members[0]
        with z.open(source_name) as source, open(output_path, "wb") as target:
            target.write(source.read())

    print(f"Extraído: {REGISTRY_OUTPUT_NAME}")

if __name__ == "__main__":
    download_arq()
    download_registro_classe()
