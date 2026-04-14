import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def run_step(step_name, script_path):
    print(f"\n[PIPELINE] Iniciando etapa: {step_name}")
    print(f"[PIPELINE] Script: {script_path}")
    subprocess.run(
        [sys.executable, str(script_path)],
        check=True,
        cwd=ROOT,
    )
    print(f"[PIPELINE] Etapa concluída: {step_name}")


def main():
    parser = argparse.ArgumentParser(
        description="Executa o pipeline completo do case CVM fim a fim"
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Pula a etapa de download dos arquivos brutos.",
    )
    args = parser.parse_args()

    steps = []
    if not args.skip_download:
        steps.append(
            (
                "download dos arquivos brutos",
                ROOT / "cvm-case" / "data" / "raw_csv" / "download_csv.py",
            )
        )

    steps.extend(
        [
            (
                "consolidação da base bruta",
                ROOT / "cvm-case" / "data" / "processed" / "consolidar_csv.py",
            ),
            (
                "construção do dataset de escopo",
                ROOT / "cvm-case" / "data" / "processed" / "build_scope_dataset.py",
            ),
            (
                "validação manual de amostras",
                ROOT / "cvm-case" / "data" / "processed" / "validate_manual_samples.py",
            ),
            (
                "construção da base de features",
                ROOT / "cvm-case" / "modeling" / "build_features_dataset.py",
            ),
            (
                "treino e avaliação do baseline",
                ROOT / "cvm-case" / "modeling" / "train_flow_baseline.py",
            ),
        ]
    )

    print("[PIPELINE] Execução iniciada.")
    for step_name, script_path in steps:
        run_step(step_name, script_path)
    print("\n[PIPELINE] Execução completa com sucesso.")


if __name__ == "__main__":
    main()
