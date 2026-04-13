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
    df["CNPJ_FUNDO"] = df["CNPJ_FUNDO_CLASSE"].astype(str).str.replace(r"\D", "", regex=True)
    df["DT_COMPTC"] = pd.to_datetime(df["DT_COMPTC"])

    df_list.append(df)

#concatenando tudo
df_concat = pd.concat(df_list, ignore_index=True)
print("Shape após concat:", df_concat.shape)

cad_path = os.path.join(RAW_PATH, "cad_fi.csv")

#lendo cadastro
df_cad = pd.read_csv(
    cad_path,
    sep=";",
    encoding="latin-1",
    low_memory=False
)

df_cad["CNPJ_FUNDO"] = df_cad["CNPJ_FUNDO"].astype(str).str.replace(r"\D", "", regex=True)

# JOIN (merge)
df = df_concat.merge(df_cad, on="CNPJ_FUNDO", how="left")
print("Shape após join:", df.shape)

# ordenacao e exportacao em Parquet
df = df.sort_values(["CNPJ_FUNDO", "DT_COMPTC"])

output_path = os.path.join(PROCESSED_PATH, "funds_raw.parquet")
df.to_parquet(output_path)

print(f"Arquivo salvo em: {output_path}")

print("Concluído!")