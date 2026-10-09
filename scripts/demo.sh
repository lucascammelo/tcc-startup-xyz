#!/usr/bin/env bash
# Demonstracao ponta a ponta da solucao Startup XYZ.
# Requisitos: AWS CLI v2 configurada, curl e python3. Uso: ./scripts/demo.sh
set -euo pipefail

STACK="${STACK:-startup-xyz}"
REGION="${AWS_REGION:-us-east-1}"
# Senha dos usuarios de teste. NUNCA coloque uma senha real neste arquivo.
# Defina antes de rodar:  export SENHA_DEMO='<SUA_SENHA_DE_TESTE>'
# Politica do Cognito: 8+ caracteres, com maiuscula, minuscula e numero.
SENHA="${SENHA_DEMO:?Defina a variavel SENHA_DEMO antes de rodar (ex.: export SENHA_DEMO='<SUA_SENHA_DE_TESTE>')}"
ANA="ana@exemplo.com.br"
BRUNO="bruno@exemplo.com.br"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

titulo() { printf '\n\033[1;33m== %s\033[0m\n' "$1"; }
json()   { python3 -m json.tool --no-ensure-ascii; }
campo()  { python3 -c "import sys,json; d=json.load(sys.stdin); print($1)"; }
saida()  { aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" \
             --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }

titulo "1. Lendo as saidas do stack $STACK ($REGION)"
API="$(saida ApiUrl)"; POOL="$(saida UserPoolId)"; CLIENT="$(saida UserPoolClientId)"; BUCKET="$(saida BucketName)"
echo "API: $API"; echo "Bucket: $BUCKET"

criar_usuario() {
  aws cognito-idp admin-create-user --region "$REGION" --user-pool-id "$POOL" --username "$1" \
    --message-action SUPPRESS --user-attributes Name=email,Value="$1" Name=email_verified,Value=true \
    >/dev/null 2>&1 || true   # ja existe: segue
  aws cognito-idp admin-set-user-password --region "$REGION" --user-pool-id "$POOL" \
    --username "$1" --password "$SENHA" --permanent
}
login() {
  aws cognito-idp initiate-auth --region "$REGION" --client-id "$CLIENT" --auth-flow USER_PASSWORD_AUTH \
    --auth-parameters "USERNAME=$1,PASSWORD=$SENHA" --query AuthenticationResult.IdToken --output text
}
enviar() {  # $1 token, $2 nome do arquivo -> imprime a key criada
  local resp url args=()
  resp="$(curl -s -X POST "$API/files/upload-url" -H "Authorization: $1" \
          -H "Content-Type: application/json" -d "{\"filename\": \"$2\"}")"
  url="$(echo "$resp" | campo 'd["upload"]["url"]')"
  while IFS= read -r linha; do args+=(--form-string "$linha"); done < <(echo "$resp" | \
    python3 -c 'import sys,json; [print(f"{k}={v}") for k,v in json.load(sys.stdin)["upload"]["fields"].items()]')
  printf '%%PDF-1.4\n%% documento de teste da Startup XYZ\n%%%%EOF\n' > "$TMP/$2"
  local code; code="$(curl -s -o /dev/null -w '%{http_code}' "${args[@]}" -F "file=@$TMP/$2" "$url")"
  [ "$code" = "204" ] || { echo "Falha no upload (HTTP $code)" >&2; exit 1; }
  echo "$resp" | campo 'd["key"]'
}

titulo "2. Criando os clientes Ana e Bruno no Cognito e fazendo login"
criar_usuario "$ANA"; criar_usuario "$BRUNO"
TOKEN_ANA="$(login "$ANA")"; TOKEN_BRUNO="$(login "$BRUNO")"
echo "Tokens recebidos (validos por 60 minutos)."

titulo "3. Ana envia um PDF (direto para o S3, por URL assinada)"
KEY_ANA="$(enviar "$TOKEN_ANA" "contrato-ana.pdf")"
echo "Gravado em s3://$BUCKET/$KEY_ANA"
KEY_BRUNO="$(enviar "$TOKEN_BRUNO" "segredo-bruno.pdf")"
echo "Bruno tambem enviou: $KEY_BRUNO"

titulo "4. Ana lista os documentos dela (so aparecem os dela)"
curl -s "$API/files" -H "Authorization: $TOKEN_ANA" | json

titulo "4b. Ana pede o link de leitura do proprio arquivo"
URL_ANA="$(curl -s -G "$API/files/download-url" --data-urlencode "key=$KEY_ANA" \
           -H "Authorization: $TOKEN_ANA" | campo 'd["url"]')"
echo "Abrindo a URL assinada: HTTP $(curl -s -o /dev/null -w '%{http_code}' "$URL_ANA") (200 = ok, vence em 5 min)"

titulo "5. Ana tenta abrir o arquivo do Bruno"
curl -s -G -w '\nHTTP %{http_code}\n' "$API/files/download-url" --data-urlencode "key=$KEY_BRUNO" \
     -H "Authorization: $TOKEN_ANA"

titulo "5b. Chamada sem login"
curl -s -w '\nHTTP %{http_code}\n' "$API/files"

titulo "Fim. Mostre agora no console: pastas no bucket, regra de Lifecycle, Block Public Access e o painel."
