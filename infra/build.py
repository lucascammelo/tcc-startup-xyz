"""Gera infra/template.yaml embutindo o codigo de src/*.py nas Lambdas (ZipFile)."""
from pathlib import Path
base = Path(__file__).parent
src = base.parent / "src"
t = (base / "template.base.yaml").read_text()
for marca, arq in {"%%UPLOAD%%": "upload.py", "%%LIST%%": "list_files.py", "%%DOWNLOAD%%": "download.py"}.items():
    codigo = (src / arq).read_text()
    assert len(codigo.encode()) < 4096, f"{arq} passa de 4096 bytes (limite do ZipFile)"
    t = t.replace(marca, "\n".join(("          " + l) if l.strip() else "" for l in codigo.splitlines()))
(base / "template.yaml").write_text("# GERADO por infra/build.py a partir de template.base.yaml + src/. Nao edite direto.\n" + t)
print("template.yaml gerado")
