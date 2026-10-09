"""POST /files/upload-url : gera uma URL pre-assinada para o cliente enviar o arquivo direto ao S3."""
import json, os, re, uuid
import boto3

s3 = boto3.client("s3")
BUCKET = os.environ["BUCKET"]
MAX_BYTES = int(os.environ.get("MAX_BYTES", "10485760"))  # 10 MB
EXPIRA = 300  # segundos
TIPOS = {"pdf": "application/pdf", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}


def resp(code, body):
    return {"statusCode": code, "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body, ensure_ascii=False)}


def usuario(event):
    # O ID vem do token validado pelo Cognito, nunca de um campo enviado pelo cliente.
    try:
        return event["requestContext"]["authorizer"]["claims"]["sub"]
    except (KeyError, TypeError):
        return None


def handler(event, context):
    sub = usuario(event)
    if not sub:
        return resp(401, {"erro": "Nao autenticado"})
    try:
        nome = str(json.loads(event.get("body") or "{}")["filename"])
    except (ValueError, KeyError, TypeError):
        return resp(400, {"erro": "Envie o corpo {\"filename\": \"arquivo.pdf\"}"})
    nome = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(nome))[:100]
    ext = nome.rsplit(".", 1)[-1].lower() if "." in nome else ""
    if ext not in TIPOS:
        return resp(400, {"erro": "Tipos aceitos: pdf, png, jpg"})
    key = f"{sub}/{uuid.uuid4().hex[:12]}-{nome}"
    post = s3.generate_presigned_post(
        BUCKET, key,
        Fields={"Content-Type": TIPOS[ext]},
        Conditions=[{"Content-Type": TIPOS[ext]}, ["content-length-range", 1, MAX_BYTES]],
        ExpiresIn=EXPIRA)
    return resp(200, {"key": key, "upload": post, "expiraEmSegundos": EXPIRA})
