"""Gera docs/arquitetura-startup-xyz.drawio (abre em app.diagrams.net ou no draw.io desktop).

Rodar: python3 docs/gerar_drawio.py
Os nomes de icones seguem a biblioteca oficial AWS4 do draw.io.
"""
from pathlib import Path
from xml.sax.saxutils import escape

PTS = ("points=[[0,0],[0.25,0],[0.5,0],[0.75,0],[1,0],[1,0.25],[1,0.5],[1,0.75],[1,1],[0.75,1],"
       "[0.5,1],[0.25,1],[0,1],[0,0.75],[0,0.5],[0,0.25]];")
LBL_BAIXO = "verticalLabelPosition=bottom;verticalAlign=top;align=center;"
LBL_CIMA = "verticalLabelPosition=top;verticalAlign=bottom;align=center;"
LBL_DIR = "labelPosition=right;verticalLabelPosition=middle;align=left;verticalAlign=middle;spacingLeft=6;"


def icone(res, cor):  # icone de servico (quadrado colorido)
    return ("sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;strokeColor=#ffffff;dashed=0;"
            "html=1;fontSize=12;fontStyle=0;aspect=fixed;" + PTS +
            f"fillColor={cor};shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{res};")


def recurso(shape, cor):  # icone de recurso (desenho sem fundo)
    return ("sketch=0;outlineConnect=0;fontColor=#232F3E;strokeColor=none;dashed=0;html=1;"
            "fontSize=12;fontStyle=0;aspect=fixed;" + PTS + f"fillColor={cor};shape=mxgraph.aws4.{shape};")


def grupo(gr, cor_borda, cor_fonte, tracejado):
    return (PTS + "outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=13;fontStyle=1;"
            f"container=0;shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.{gr};strokeColor={cor_borda};"
            f"fillColor=none;verticalAlign=top;align=left;spacingLeft=30;fontColor={cor_fonte};dashed={tracejado};")


celulas, arestas = [], []


def cel(id_, valor, estilo, x, y, w, h):
    celulas.append((id_, valor, estilo, x, y, w, h))


def seta(id_, origem, destino, valor="", saida=None, entrada=None, pontos=(), cor="#232F3E",
         tracejado=False, largura=2, rotulo_x=0, rotulo_dy=0):
    estilo = (f"edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;html=1;endArrow=block;endFill=1;"
              f"strokeColor={cor};strokeWidth={largura};fontSize=11;fontColor=#232F3E;"
              "labelBackgroundColor=#FFFFFF;")
    if tracejado:
        estilo += "dashed=1;dashPattern=6 4;"
    if saida:
        estilo += f"exitX={saida[0]};exitY={saida[1]};exitDx=0;exitDy=0;"
    if entrada:
        estilo += f"entryX={entrada[0]};entryY={entrada[1]};entryDx=0;entryDy=0;"
    arestas.append((id_, valor, estilo, origem, destino, pontos, rotulo_x, rotulo_dy))


# ------------------------------------------------------------------ título
cel("titulo", "<b style='font-size:22px'>Startup XYZ | Gestão de documentos para IA</b><br>"
    "<span style='font-size:13px;color:#545B64'>Arquitetura serverless na AWS · TCC Escola da Nuvem</span>",
    "text;html=1;align=left;verticalAlign=middle;whiteSpace=wrap;strokeColor=none;fillColor=none;",
    40, 15, 900, 60)

# ------------------------------------------------------------------ grupos
cel("nuvem", "AWS Cloud", grupo("group_aws_cloud_alt", "#232F3E", "#232F3E", 0), 200, 90, 1470, 940)
cel("leste", "Região us-east-1 (N. Virginia)", grupo("group_region", "#00A4A6", "#147EBA", 1),
    230, 130, 1080, 880)
cel("oeste", "Região us-east-2 (Ohio) · DR", grupo("group_region", "#00A4A6", "#147EBA", 1),
    1340, 130, 300, 330)
cel("faixa", "Observabilidade, custos e infraestrutura como código",
    "rounded=1;arcSize=4;whiteSpace=wrap;html=1;fillColor=#F7F7F7;strokeColor=#AAB7B8;dashed=1;"
    "verticalAlign=top;align=right;spacingRight=12;spacingTop=6;fontSize=12;fontStyle=1;fontColor=#545B64;",
    260, 790, 1020, 180)

# ------------------------------------------------------------------ fora da AWS
cel("cliente", "<b>Cliente XYZ</b><br>app ou script", recurso("users", "#232F3D") + LBL_BAIXO, 60, 420, 78, 78)
cel("equipe", "<b>Equipe XYZ</b><br>recebe alertas", recurso("users", "#232F3D") + LBL_CIMA, 60, 830, 78, 78)

# ------------------------------------------------------------------ us-east-1
cel("cognito", "<b>Amazon Cognito</b><br>User Pool (Lite)<br>token JWT · 60 min",
    icone("cognito", "#DD344C") + LBL_DIR, 470, 230, 78, 78)
cel("api", "<b>API Gateway</b><br>REST · 50 req/s",
    icone("api_gateway", "#E7157B") + LBL_BAIXO, 470, 420, 78, 78)
for id_, y, rota, perm in [("lb_up", 270, "upload-url", "s3:PutObject"),
                           ("lb_list", 420, "list", "s3:ListBucket"),
                           ("lb_down", 570, "download-url", "s3:GetObject")]:
    cel(id_, f"<b>Lambda {rota}</b><br>role: {perm}", icone("lambda", "#ED7100") + LBL_BAIXO, 780, y, 78, 78)
cel("s3", "<b>Amazon S3</b><br>docs/&lt;id-do-cliente&gt;/", icone("s3", "#7AA116") + LBL_BAIXO,
    1120, 420, 78, 78)
cel("deep", "<b>S3 Glacier<br>Deep Archive</b>", recurso("glacier_deep_archive", "#7AA116") + LBL_BAIXO,
    1121, 640, 75, 78)
cel("seg", "<b>Segurança no bucket</b><br>• Block Public Access<br>• Criptografia SSE-S3<br>"
    "• Bucket policy: só HTTPS<br>• Versionamento ligado<br>• Pasta = ID do token",
    "rounded=1;arcSize=6;whiteSpace=wrap;html=1;fillColor=#FDF2F4;strokeColor=#DD344C;align=left;"
    "verticalAlign=top;spacingLeft=10;spacingTop=6;fontSize=11;fontColor=#232F3E;", 900, 640, 190, 120)

# faixa inferior
cel("cw", "<b>CloudWatch</b><br>logs, 5 alarmes, painel", icone("cloudwatch_2", "#E7157B") + LBL_BAIXO,
    330, 830, 78, 78)
cel("sns", "<b>Amazon SNS</b><br>tópico de alertas", icone("sns", "#E7157B") + LBL_CIMA, 560, 830, 78, 78)
cel("budgets", "<b>AWS Budgets</b><br>80% real · 100% previsto", icone("budgets_2", "#7AA116") + LBL_CIMA,
    790, 830, 78, 78)
cel("cfn", "<b>CloudFormation</b><br>sobe toda a solução", icone("cloudformation", "#E7157B") + LBL_BAIXO,
    1020, 830, 78, 78)

# ------------------------------------------------------------------ us-east-2 (Ohio)
cel("replica", "<b>Bucket réplica</b><br>Deep Archive", recurso("glacier_deep_archive", "#7AA116") + LBL_BAIXO,
    1490, 270, 75, 78)

# ------------------------------------------------------------------ legenda
cel("legenda",
    "<b style='font-size:13px'>Fluxo</b><br>"
    "<b>1</b> Login no Cognito, recebe token<br>"
    "<b>2</b> Chama a API com o token<br>"
    "<b>3</b> API valida o token no Cognito<br>"
    "<b>4</b> API invoca a Lambda da rota<br>"
    "<b>5</b> Lambda gera URL assinada (5 min) só para a pasta do cliente<br>"
    "<b>6</b> Arquivo vai e volta direto do S3, por HTTPS<br>"
    "<b>7</b> Lifecycle move para Deep Archive após 365 dias<br>"
    "<b>8</b> Replicação para outra região (DR)<br><br>"
    "<b style='font-size:13px'>Linhas</b><br>"
    "Preta: requisição · Laranja: dados do arquivo<br>"
    "Verde: armazenamento · Cinza tracejada: monitoramento",
    "rounded=1;arcSize=3;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#AAB7B8;align=left;"
    "verticalAlign=top;spacingLeft=12;spacingTop=8;spacingRight=8;fontSize=11;fontColor=#232F3E;",
    1350, 490, 300, 240)

# ------------------------------------------------------------------ setas
LARANJA, VERDE, CINZA = "#ED7100", "#3F8624", "#879196"
seta("e1", "cliente", "cognito", "1. login", saida=(0.7, 0), entrada=(0, 0.5), pontos=[(115, 269)])
seta("e2", "cliente", "api", "2. HTTPS + token", saida=(1, 0.5), entrada=(0, 0.5))
seta("e3", "api", "cognito", "3. valida token", saida=(0.5, 0), entrada=(0.5, 1))
for id_, alvo, rot in [("e4a", "lb_up", ""), ("e4b", "lb_list", "4. invoca"), ("e4c", "lb_down", "")]:
    seta(id_, "api", alvo, rot, saida=(1, 0.5), entrada=(0, 0.5), pontos=[(680, 459)], rotulo_x=-0.45)
for id_, origem, rot in [("e5a", "lb_up", ""), ("e5b", "lb_list", "5. URL assinada"), ("e5c", "lb_down", "")]:
    seta(id_, origem, "s3", rot, saida=(1, 0.5), entrada=(0, 0.5), pontos=[(1000, 459)], rotulo_x=0.45)
seta("e6", "cliente", "s3", "6. upload e download direto no S3 (URL assinada · 5 min · HTTPS)",
     saida=(0.3, 0), entrada=(0.5, 0), pontos=[(83, 185), (1159, 185)], cor=LARANJA, largura=3)
seta("e7", "s3", "deep", "7. Lifecycle<br>365 dias", saida=(1, 0.7), entrada=(1, 0.5),
     pontos=[(1250, 475), (1250, 679)], cor=VERDE)
seta("e8", "s3", "replica", "8. Replicação (CRR)", saida=(1, 0.3), entrada=(0, 0.5),
     pontos=[(1420, 443), (1420, 309)], cor=VERDE, rotulo_x=-0.35)
seta("e9a", "api", "cw", "logs e métricas", saida=(0, 0.8), entrada=(0.77, 0),
     pontos=[(430, 482), (430, 800), (390, 800)], cor=CINZA, tracejado=True, largura=1.5, rotulo_x=-0.2)
seta("e9b", "lb_down", "cw", "", saida=(0, 0.85), entrada=(0.77, 0),
     pontos=[(430, 636), (430, 800), (390, 800)], cor=CINZA, tracejado=True, largura=1.5)
seta("e10", "cw", "sns", "alarmes", saida=(1, 0.5), entrada=(0, 0.5), cor=CINZA, tracejado=True, largura=1.5)
seta("e11", "sns", "equipe", "e-mail", saida=(0.5, 1), entrada=(0.65, 1),
     pontos=[(599, 960), (111, 960)], cor=CINZA, tracejado=True, largura=1.5)
seta("e12", "budgets", "equipe", "e-mail de orçamento", saida=(0.5, 1), entrada=(0.25, 1),
     pontos=[(829, 995), (80, 995)], cor=CINZA, tracejado=True, largura=1.5)


# ------------------------------------------------------------------ XML
def xml():
    out = ['<mxfile host="app.diagrams.net" agent="Claude" version="24.7.17">',
           '  <diagram id="arquitetura-xyz" name="Arquitetura AWS">',
           '    <mxGraphModel dx="1700" dy="1060" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
           'arrows="1" fold="1" page="1" pageScale="1" pageWidth="1700" pageHeight="1060" math="0" shadow="0">',
           '      <root>', '        <mxCell id="0" />', '        <mxCell id="1" parent="0" />']
    for id_, valor, estilo, x, y, w, h in celulas:
        out.append(f'        <mxCell id="{id_}" value="{escape(valor, {chr(34): "&quot;"})}" '
                   f'style="{escape(estilo)}" vertex="1" parent="1">')
        out.append(f'          <mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" />')
        out.append('        </mxCell>')
    for id_, valor, estilo, o, d, pts, rx, rdy in arestas:
        out.append(f'        <mxCell id="{id_}" value="{escape(valor, {chr(34): "&quot;"})}" '
                   f'style="{escape(estilo)}" edge="1" parent="1" source="{o}" target="{d}">')
        out.append(f'          <mxGeometry x="{rx}" y="{rdy}" relative="1" as="geometry">')
        if pts:
            out.append('            <Array as="points">')
            out += [f'              <mxPoint x="{px}" y="{py}" />' for px, py in pts]
            out.append('            </Array>')
        out.append('          </mxGeometry>')
        out.append('        </mxCell>')
    out += ['      </root>', '    </mxGraphModel>', '  </diagram>', '</mxfile>']
    return "\n".join(out) + "\n"


destino = Path(__file__).parent / "arquitetura-startup-xyz.drawio"
destino.write_text(xml(), encoding="utf-8")
print(f"gerado: {destino}")
