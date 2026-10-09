"""Testes locais das Lambdas com S3 simulado (moto). Rodar: pytest -v"""
import importlib, json, os, sys
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
BUCKET = "docs-teste"
ANA, BRUNO = "aaaa-1111", "bbbb-2222"  # dois "sub" do Cognito


def evento(sub, body=None, query=None):
    return {"requestContext": {"authorizer": {"claims": {"sub": sub}}},
            "body": json.dumps(body) if body is not None else None,
            "queryStringParameters": query}


@pytest.fixture
def s3():
    os.environ.update(BUCKET=BUCKET, AWS_DEFAULT_REGION="us-east-1",
                      AWS_ACCESS_KEY_ID="x", AWS_SECRET_ACCESS_KEY="x")
    with mock_aws():
        cli = boto3.client("s3", region_name="us-east-1")
        cli.create_bucket(Bucket=BUCKET)
        cli.put_object(Bucket=BUCKET, Key=f"{ANA}/1-contrato.pdf", Body=b"%PDF ana")
        cli.put_object(Bucket=BUCKET, Key=f"{ANA}/2-antigo.pdf", Body=b"%PDF velho",
                       StorageClass="DEEP_ARCHIVE")
        cli.put_object(Bucket=BUCKET, Key=f"{BRUNO}/1-segredo.pdf", Body=b"%PDF bruno")
        yield cli


def carregar(nome):
    mod = importlib.import_module(nome)
    return importlib.reload(mod)  # recria o client dentro do mock


def corpo(r):
    return json.loads(r["body"])


# ------------------------------------------------------------------ upload
def test_upload_gera_url_no_prefixo_do_usuario(s3):
    r = carregar("upload").handler(evento(ANA, {"filename": "nota fiscal.pdf"}), None)
    assert r["statusCode"] == 200
    b = corpo(r)
    assert b["key"].startswith(f"{ANA}/") and b["key"].endswith("nota_fiscal.pdf")
    assert b["upload"]["fields"]["Content-Type"] == "application/pdf"


def test_upload_ignora_tentativa_de_escolher_pasta(s3):
    r = carregar("upload").handler(evento(ANA, {"filename": f"../{BRUNO}/x.pdf"}), None)
    assert corpo(r)["key"].startswith(f"{ANA}/")


def test_upload_recusa_tipo_nao_permitido(s3):
    r = carregar("upload").handler(evento(ANA, {"filename": "virus.exe"}), None)
    assert r["statusCode"] == 400


def test_upload_sem_token_retorna_401(s3):
    r = carregar("upload").handler({"body": "{}"}, None)
    assert r["statusCode"] == 401


# ------------------------------------------------------------------ listagem
def test_lista_somente_arquivos_do_proprio_usuario(s3):
    b = corpo(carregar("list_files").handler(evento(ANA), None))
    keys = {a["key"] for a in b["arquivos"]}
    assert keys == {f"{ANA}/1-contrato.pdf", f"{ANA}/2-antigo.pdf"}
    assert not any(BRUNO in k for k in keys)


def test_lista_indica_arquivo_arquivado(s3):
    b = corpo(carregar("list_files").handler(evento(ANA), None))
    antigo = next(a for a in b["arquivos"] if a["nome"] == "2-antigo.pdf")
    assert antigo["classe"] == "DEEP_ARCHIVE" and antigo["disponivel"] is False


# ------------------------------------------------------------------ download
def test_download_do_proprio_arquivo_retorna_url_assinada(s3):
    r = carregar("download").handler(evento(ANA, query={"key": f"{ANA}/1-contrato.pdf"}), None)
    assert r["statusCode"] == 200
    assert "Signature" in corpo(r)["url"] or "X-Amz-Signature" in corpo(r)["url"]


def test_download_de_arquivo_de_outro_usuario_e_bloqueado(s3):
    r = carregar("download").handler(evento(ANA, query={"key": f"{BRUNO}/1-segredo.pdf"}), None)
    assert r["statusCode"] == 403


def test_download_com_path_traversal_e_bloqueado(s3):
    r = carregar("download").handler(
        evento(ANA, query={"key": f"{ANA}/../{BRUNO}/1-segredo.pdf"}), None)
    assert r["statusCode"] == 403


def test_download_de_arquivo_arquivado_retorna_409(s3):
    r = carregar("download").handler(evento(ANA, query={"key": f"{ANA}/2-antigo.pdf"}), None)
    assert r["statusCode"] == 409


def test_download_inexistente_retorna_404(s3):
    r = carregar("download").handler(evento(ANA, query={"key": f"{ANA}/nao-existe.pdf"}), None)
    assert r["statusCode"] == 404
