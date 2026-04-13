import os
import glob
import pandas as pd

#path dinamico
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

RAW_PATH = os.path.join(BASE_DIR, "data", "raw_csv")
PROCESSED_PATH = os.path.join(BASE_DIR, "data", "processed")

os.makedirs(PROCESSED_PATH, exist_ok=True)

#listando os csv
files = glob.glob(os.path.join(RAW_PATH, "inf_diario_fi_*.csv"))

print(f"{len(files)} arquivos encontrados")

df_list = []

for file in files:
    print(f"Lendo: {file}")

    df = pd.read_csv(
        file,
        sep=";",
        encoding="latin-1",
        low_memory=False
    )

    # padronizacao
    df["CNPJ_FUNDO_CLASSE"] = df["CNPJ_FUNDO_CLASSE"].astype(str).str.replace(r"\D", "", regex=True)
    df["DT_COMPTC"] = pd.to_datetime(df["DT_COMPTC"])

    df_list.append(df)

#concatenando tudo
df_concat = pd.concat(df_list, ignore_index=True)
print("Shape após concat:", df_all.shape)