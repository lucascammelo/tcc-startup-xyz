"""GET /files/download-url?key=... : devolve URL assinada de leitura, so para arquivos do proprio usuario."""
import json, os
import boto3
from botocore.exceptions import ClientError

s3 = boto3.client("s3")
BUCKET = os.environ["BUCKET"]
EXPIRA = 300
FRIAS = {"GLACIER", "DEEP_ARCHIVE"}


def resp(code, body):
    return {"statusCode": code, "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body, ensure_ascii=False)}


def usuario(event):
    try:
        return event["requestContext"]["authorizer"]["claims"]["sub"]
    except (KeyError, TypeError):
        return None


def handler(event, context):
    sub = usuario(event)
    if not sub:
        return resp(401, {"erro": "Nao autenticado"})
    key = ((event.get("queryStringParameters") or {}).get("key") or "").strip()
    if not key:
        return resp(400, {"erro": "Informe ?key=..."})
    # Isolamento: a chave tem que comecar com o ID do proprio usuario e nao pode "subir" de pasta.
    if not key.startswith(f"{sub}/") or ".." in key:
        print(json.dumps({"evento": "ACESSO_NEGADO", "usuario": sub, "keyPedida": key}))
        return resp(403, {"erro": "Acesso negado a este documento"})
    try:
        meta = s3.head_object(Bucket=BUCKET, Key=key)
    except ClientError:
        return resp(404, {"erro": "Documento nao encontrado"})
    if meta.get("StorageClass") in FRIAS:
        return resp(409, {"erro": "Documento arquivado na camada fria (mais de 12 meses). "
                                  "Solicite a restauracao ao suporte."})
    url = s3.generate_presigned_url("get_object", Params={"Bucket": BUCKET, "Key": key},
                                    ExpiresIn=EXPIRA)
    return resp(200, {"key": key, "url": url, "expiraEmSegundos": EXPIRA})
