"""GET /files : lista somente os documentos do usuario autenticado (prefixo = ID do Cognito)."""
import json, os
import boto3

s3 = boto3.client("s3")
BUCKET = os.environ["BUCKET"]
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
    itens = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix=f"{sub}/"):
        for o in page.get("Contents", []):
            classe = o.get("StorageClass", "STANDARD")
            itens.append({
                "key": o["Key"],
                "nome": o["Key"].split("/", 1)[1],
                "tamanhoBytes": o["Size"],
                "enviadoEm": o["LastModified"].isoformat(),
                "classe": classe,
                "disponivel": classe not in FRIAS,
            })
    return resp(200, {"total": len(itens), "arquivos": itens})
