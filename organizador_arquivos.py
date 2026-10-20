"""
Robozinho Organizador de Arquivos & Mesclador Inteligente de PDFs
Funciona no Windows e Linux.

Recursos:
1. Extração automática de arquivos ZIP (em pastas individuais para não misturar).
2. Junção Inteligente de PDFs:
   - Identifica grupos por número/código do cliente (ex: 496 IRPJ, 496 CSLL, 496 PIS...).
   - Suporta 2, 3, 4 ou mais PDFs por cliente.
   - Junta todos os PDFs encontrados na mesma pasta extraída.
   - Ordena os documentos com prioridade lógica (ex: Declaração antes de Recibo/DARF).
3. Organização de pastas (Downloads, PDFs, Planilhas, Imagens, etc.).
4. Preserva os arquivos originais e evita sobrescrever nomes existentes.
"""

import os
import sys
import re
import shutil
import zipfile
from pathlib import Path
from typing import List, Dict, Optional

# Garante suporte a UTF-8 no terminal Windows sem travar em charmap
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Tenta importar pypdf
try:
    import pypdf
except ImportError:
    pypdf = None


# Prioridades conhecidas para ordenação de páginas fiscais/contábeis
ORDEM_PRIORIDADE = [
    "irpj", "csll", "pis", "cofins", "das", "simples",
    "declaracao", "declarac", "recibo", "darf", "guia", "extrato", "relatorio"
]

CATEGORIAS = {
    "PDFs": [".pdf"],
    "Compactados": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "Planilhas": [".xlsx", ".xls", ".csv", ".ods"],
    "Documentos": [".docx", ".doc", ".txt", ".odt", ".rtf"],
    "Imagens": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"],
    "Instaladores": [".exe", ".msi", ".bat", ".cmd"],
}

# Arquivos e pastas do sistema para ignorar
IGNORAR_ARQUIVOS = {
    "organizador_arquivos.py", "robozinho.py", "executar_robozinho.bat",
    ".gitignore", "README.md", "requirements.txt", "testar_robozinho.py"
}
IGNORAR_PASTAS = {
    ".git", ".vscode", "__pycache__", "PDFs_Juntados", "PDFs_Separados", "Extraidos", "venv", ".venv",
    "Compactados", "Planilhas", "Documentos", "Imagens", "Instaladores", "Outros", "PDFs"
}


def obter_caminho_unico(caminho: Path) -> Path:
    """Evita sobrescrever arquivos existentes adicionando sufixo (1), (2), etc."""
    if not caminho.exists():
        return caminho
    
    pasta = caminho.parent
    nome = caminho.stem
    ext = caminho.suffix
    contador = 1
    
    while True:
        novo_caminho = pasta / f"{nome} ({contador}){ext}"
        if not novo_caminho.exists():
            return novo_caminho
        contador += 1


def extrair_todos_zips(diretorio: Path, pasta_destino: Optional[Path] = None) -> List[Path]:
    """
    Extrai todos os arquivos .zip encontrados no diretório.
    Cria uma subpasta para cada ZIP dentro de 'Extraidos/'.
    Retorna a lista de pastas descompactadas.
    """
    if pasta_destino is None:
        pasta_destino = diretorio / "Extraidos"
    pasta_destino.mkdir(exist_ok=True, parents=True)

    pastas_extraidas = []
    zips = list(diretorio.glob("*.zip"))
    
    if not zips:
        print(" [i] Nenhum arquivo .zip encontrado na pasta.")
        return pastas_extraidas

    print(f" [*] Encontrados {len(zips)} arquivo(s) ZIP para extrair...")
    
    for zip_path in zips:
        nome_pasta = zip_path.stem
        destino_zip = pasta_destino / nome_pasta
        destino_zip.mkdir(exist_ok=True, parents=True)
        
        print(f"   -> Extraindo '{zip_path.name}' para '{destino_zip.name}/'...")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # Trata caracteres especiais e acentuação no zip
                for member in zf.infolist():
                    try:
                        # Tenta decodificar nomes com utf-8 ou cp437 padrão do Windows
                        try:
                            filename = member.filename.encode('cp437').decode('utf-8')
                        except (UnicodeDecodeError, UnicodeEncodeError):
                            filename = member.filename
                        
                        target_path = destino_zip / filename
                        if member.is_dir():
                            target_path.mkdir(parents=True, exist_ok=True)
                        else:
                            target_path.parent.mkdir(parents=True, exist_ok=True)
                            with zf.open(member) as source, open(target_path, "wb") as target:
                                shutil.copyfileobj(source, target)
                    except Exception:
                        # Fallback seguro para extração nativa
                        zf.extract(member, destino_zip)
                        
            pastas_extraidas.append(destino_zip)
            print(f"      [OK] Concluído: {zip_path.name}")
        except Exception as e:
            print(f"      [ERRO] Falha ao extrair {zip_path.name}: {e}")
            
    return pastas_extraidas


def extrair_codigo_identificador(nome_arquivo: str) -> Optional[str]:
    """
    Identifica o código do cliente ou identificador comum no nome do PDF.
    Exemplos:
      '496 IRPJ.pdf' -> '496'
      '496 CSLL.pdf' -> '496'
      '496-PIS.pdf'  -> '496'
      'CLI_1020_RECIBO.pdf' -> 'CLI_1020'
    """
    # 1. Tenta número no começo do nome (muito comum em contabilidade: '496 IRPJ')
    match_num = re.match(r"^(\d+)", nome_arquivo.strip())
    if match_num:
        return match_num.group(1)

    # 2. Tenta código alfanumérico antes do primeiro hífen, underline ou espaço
    match_cod = re.match(r"^([A-Za-z0-9]+)[\s_\-]+", nome_arquivo.strip())
    if match_cod:
        return match_cod.group(1)

    return None


def peso_ordenacao_pdf(caminho: Path) -> tuple:
    """Calcula prioridade lógica para ordenar os PDFs antes de juntar."""
    nome = caminho.stem.lower()
    
    # Prioridade por palavra-chave contábil
    prioridade = 999
    for idx, palavra in enumerate(ORDEM_PRIORIDADE):
        if palavra in nome:
            prioridade = idx
            break
            
    return (prioridade, nome)


def juntar_lista_pdfs(lista_pdfs: List[Path], caminho_saida: Path) -> bool:
    """Combina uma lista de PDFs em um único arquivo de saída."""
    if pypdf is None:
        print(" [ERRO] Biblioteca 'pypdf' não instalada! Instale com: pip install pypdf")
        return False

    if not lista_pdfs:
        return False

    caminho_final = obter_caminho_unico(caminho_saida)
    caminho_final.parent.mkdir(parents=True, exist_ok=True)
    
    merger = pypdf.PdfWriter()
    arquivos_abertos = []

    try:
        # Ordena para garantir boa sequência (IRPJ antes de CSLL, etc.)
        lista_ordenada = sorted(lista_pdfs, key=peso_ordenacao_pdf)
        
        for pdf in lista_ordenada:
            reader = pypdf.PdfReader(str(pdf))
            arquivos_abertos.append(reader)
            merger.append(reader)

        with open(caminho_final, "wb") as f_out:
            merger.write(f_out)
        merger.close()

        print(f" [OK] PDF combinado criado: '{caminho_final.name}' ({len(lista_ordenada)} documentos)")
        for pdf in lista_ordenada:
            print(f"       + {pdf.name}")
        return True
    except Exception as e:
        print(f" [ERRO] Falha ao juntar PDFs para '{caminho_saida.name}': {e}")
        return False


def juntar_pdfs_inteligente(diretorio_base: Path, pasta_destino: Optional[Path] = None):
    """
    Agrupa e junta PDFs automaticamente:
    1. PDFs que compartilham o mesmo número/código (ex: 496 IRPJ e 496 CSLL),
       mesmo que estejam em subpastas diferentes (como 'GUIA IR' e 'CSLL'),
       são todos mesclados no arquivo correspondente (ex: 496_Completo.pdf).
    2. Suporta 2, 3, 4 ou mais PDFs por cliente.
    3. Para PDFs sem código específico em subpastas de ZIP, junta pelo nome da pasta.
    """
    if pypdf is None:
        print(" [ERRO] Biblioteca 'pypdf' necessária. Instale com: pip install pypdf")
        return

    if pasta_destino is None:
        pasta_destino = diretorio_base / "PDFs_Juntados"
    pasta_destino.mkdir(exist_ok=True, parents=True)

    print("\n [*] Iniciando agrupamento inteligente de PDFs...")

    # Coleta todos os PDFs do diretório (inclusive subpastas e extraídos),
    # ignorando pastas do sistema ou a própria pasta de saída
    todos_candidatos = []
    for pdf in diretorio_base.rglob("*.pdf"):
        partes = [p.name for p in pdf.parents]
        if any(ign in partes or pdf.parent.name == ign for ign in IGNORAR_PASTAS):
            continue
        todos_candidatos.append(pdf)

    # Remove duplicatas de mesmo nome de arquivo (caso o mesmo arquivo esteja na raiz e em Extraidos)
    arquivos_unicos: Dict[str, Path] = {}
    for pdf in todos_candidatos:
        # Chave por nome do arquivo (ex: '496 IRPJ.pdf')
        if pdf.name not in arquivos_unicos:
            arquivos_unicos[pdf.name] = pdf

    lista_pdfs = list(arquivos_unicos.values())
    processados = set()

    # 1. Agrupar globalmente por Código de Cliente (ex: 496)
    grupos_codigo: Dict[str, List[Path]] = {}
    for pdf in lista_pdfs:
        cod = extrair_codigo_identificador(pdf.stem)
        if cod:
            grupos_codigo.setdefault(cod, []).append(pdf)

    for cod, lista in grupos_codigo.items():
        if len(lista) >= 2:
            print(f"\n -> Encontrado cliente/código '{cod}' com {len(lista)} documento(s):")
            nome_saida = f"{cod}_Completo.pdf"
            if juntar_lista_pdfs(lista, pasta_destino / nome_saida):
                for p in lista:
                    processados.add(p.resolve())

    # 2. Agrupar PDFs restantes que estão na mesma pasta (se houver >= 2 sem código)
    pastas_restantes: Dict[Path, List[Path]] = {}
    for pdf in lista_pdfs:
        if pdf.resolve() not in processados:
            pastas_restantes.setdefault(pdf.parent, []).append(pdf)

    for pasta_origem, lista in pastas_restantes.items():
        if len(lista) >= 2 and pasta_origem != diretorio_base:
            print(f"\n -> Agrupando {len(lista)} PDFs da pasta '{pasta_origem.name}':")
            nome_saida = f"{pasta_origem.name}_Completo.pdf"
            if juntar_lista_pdfs(lista, pasta_destino / nome_saida):
                for p in lista:
                    processados.add(p.resolve())


def organizar_downloads(diretorio: Path):
    """Organiza os arquivos restantes em pastas por categoria."""
    print(f"\n [*] Organizando arquivos em '{diretorio}' por extensão...")
    
    for item in diretorio.iterdir():
        if item.is_dir() or item.name in IGNORAR_ARQUIVOS:
            continue
            
        ext = item.suffix.lower()
        if not ext:
            continue
            
        pasta_destino_nome = "Outros"
        for categoria, extensoes in CATEGORIAS.items():
            if ext in extensoes:
                pasta_destino_nome = categoria
                break
                
        pasta_alvo = diretorio / pasta_destino_nome
        pasta_alvo.mkdir(exist_ok=True)
        
        destino_final = obter_caminho_unico(pasta_alvo / item.name)
        try:
            shutil.move(str(item), str(destino_final))
            print(f"   [Mover] {item.name} -> {pasta_destino_nome}/")
        except Exception as e:
            print(f"   [ERRO] Não foi possível mover {item.name}: {e}")


def executar_fluxo_completo(diretorio: Path):
    """Executa a rotina inteira: descompacta, junta PDFs inteligentemente e organiza."""
    print("=" * 60)
    print(" ROBOZINHO: EXTRAIR ZIPS -> JUNTAR PDFS -> ORGANIZAR")
    print(f" Pasta de trabalho: {diretorio}")
    print("=" * 60)

    # 1. Extrair Zips
    extrair_todos_zips(diretorio)

    # 2. Juntar PDFs de forma inteligente (respeitando códigos e pastas)
    juntar_pdfs_inteligente(diretorio)

    # 3. Organizar os arquivos soltos por categoria
    organizar_downloads(diretorio)

    print("\n" + "=" * 60)
    print(" [CONCLUÍDO] Processo finalizado com sucesso!")
    print(f" - Arquivos extraídos em: {diretorio / 'Extraidos'}")
    print(f" - PDFs combinados em:   {diretorio / 'PDFs_Juntados'}")
    print("=" * 60)


def sanitizar_nome_arquivo(nome: str, max_len: int = 50) -> str:
    """Remove caracteres proibidos pelo Windows para criar nomes de arquivos válidos."""
    limpo = re.sub(r'[\\/*?:"<>|]', '_', nome.strip())
    limpo = re.sub(r'\s+', ' ', limpo).strip(' ._')
    return limpo[:max_len] if limpo else "Documento"


def extrair_identificador_texto_pagina(texto: str) -> Optional[str]:
    """
    Busca no texto de uma página de PDF algum identificador único de cliente:
    - CNPJ (ex: 12.345.678/0001-90)
    - CPF (ex: 123.456.789-00)
    - Código/Cliente (ex: Código: 496)
    - Razão Social / Colaborador (ex: Razão Social: Empresa ABC)
    """
    if not texto:
        return None

    # 1. Busca CNPJ
    match_cnpj = re.search(r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b', texto)
    if match_cnpj:
        cnpj_limpo = match_cnpj.group(0).replace('/', '_').replace('.', '_')
        return f"CNPJ_{cnpj_limpo}"

    # 2. Busca Código do Cliente ou Empresa
    match_cod = re.search(r'(?:C[óo]d(?:igo)?|Cliente|Empresa|Inscri[çc][ãa]o|Matr[íi]cula)\s*[:#-]?\s*([A-Za-z0-9_-]{2,20})', texto, re.IGNORECASE)
    if match_cod:
        return f"Cliente_{sanitizar_nome_arquivo(match_cod.group(1))}"

    # 3. Busca CPF
    match_cpf = re.search(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b', texto)
    if match_cpf:
        return f"CPF_{match_cpf.group(0).replace('.', '_')}"

    # 4. Busca Razão Social ou Colaborador
    match_nome = re.search(r'(?:Raz[ãa]o\s*Social|Nome\s*Empresarial|Colaborador|Funcion[áa]rio)\s*[:#-]?\s*([A-Za-zÀ-ÿ0-9\.\- ]{3,35})', texto, re.IGNORECASE)
    if match_nome:
        return f"{sanitizar_nome_arquivo(match_nome.group(1))}"

    return None


def separar_pdf(caminho_pdf: Path, modo: str = "inteligente", paginas_por_bloco: int = 1, pasta_destino: Optional[Path] = None) -> List[Path]:
    """
    Separa (split) um PDF grande em múltiplos PDFs menores.
    Modos:
      - 'inteligente': agrupa por CNPJ, Código ou Nome extraído de cada página.
      - 'pagina': 1 página por arquivo.
      - 'bloco': a cada N páginas por arquivo.
    """
    if pypdf is None:
        print(" [ERRO] Biblioteca 'pypdf' necessária. Instale com: pip install pypdf")
        return []

    caminho_pdf = Path(caminho_pdf)
    if not caminho_pdf.exists() or not caminho_pdf.is_file():
        print(f" [ERRO] Arquivo não encontrado: {caminho_pdf}")
        return []

    if pasta_destino is None:
        pasta_destino = caminho_pdf.parent / "PDFs_Separados" / caminho_pdf.stem
    pasta_destino.mkdir(exist_ok=True, parents=True)

    print("\n" + "=" * 60)
    print(f" ✂️ SEPARANDO PDF: '{caminho_pdf.name}'")
    print(f" Pasta de saída: {pasta_destino}")
    print("=" * 60)

    try:
        reader = pypdf.PdfReader(str(caminho_pdf))
        total_paginas = len(reader.pages)
    except Exception as e:
        print(f" [ERRO] Falha ao abrir o PDF: {e}")
        return []

    print(f" [*] Total de páginas encontradas: {total_paginas}")
    arquivos_gerados = []

    # MODO 1: Separação Inteligente (por CNPJ, Código ou Cliente)
    if modo == "inteligente":
        grupos: List[Dict] = []
        grupo_atual = None

        print(" [*] Analisando texto das páginas para identificar clientes...")

        for idx, page in enumerate(reader.pages):
            num_pag = idx + 1
            texto = ""
            try:
                texto = page.extract_text() or ""
            except Exception:
                pass

            identificador = extrair_identificador_texto_pagina(texto)

            if identificador:
                # Se achou identificador, inicia novo grupo (ou continua se for igual ao anterior)
                if grupo_atual and grupo_atual["id"] == identificador:
                    grupo_atual["paginas"].append(page)
                    grupo_atual["num_paginas"].append(num_pag)
                else:
                    if grupo_atual:
                        grupos.append(grupo_atual)
                    grupo_atual = {
                        "id": identificador,
                        "paginas": [page],
                        "num_paginas": [num_pag]
                    }
            else:
                # Se não achou identificador na página, anexa ao cliente anterior se houver
                if grupo_atual:
                    grupo_atual["paginas"].append(page)
                    grupo_atual["num_paginas"].append(num_pag)
                else:
                    # Primeira página sem identificador
                    grupo_atual = {
                        "id": f"Pagina_{num_pag:03d}",
                        "paginas": [page],
                        "num_paginas": [num_pag]
                    }

        if grupo_atual:
            grupos.append(grupo_atual)

        # Se quase tudo ficou como 'Pagina_XXX' (PDF escaneado/sem texto), avisa o usuário
        sem_texto = sum(1 for g in grupos if g["id"].startswith("Pagina_"))
        if len(grupos) > 1 and sem_texto == len(grupos):
            print(" [i] Nota: O PDF não possui texto digital pesquisável (pode ser escaneado).")
            print("     Separando por páginas individuais...")

        print(f" [*] Gerando {len(grupos)} arquivo(s) separado(s)...")

        for grupo in grupos:
            writer = pypdf.PdfWriter()
            for p in grupo["paginas"]:
                writer.add_page(p)

            nome_arquivo = f"{grupo['id']}.pdf"
            caminho_saida = obter_caminho_unico(pasta_destino / nome_arquivo)

            with open(caminho_saida, "wb") as f_out:
                writer.write(f_out)
            writer.close()

            pags_str = ", ".join(str(p) for p in grupo["num_paginas"])
            print(f"   [OK] {caminho_saida.name} (páginas: {pags_str})")
            arquivos_gerados.append(caminho_saida)

    # MODO 2: Página por Página ou Blocos de N páginas
    else:
        bloco_size = max(1, paginas_por_bloco)
        total_blocos = (total_paginas + bloco_size - 1) // bloco_size

        print(f" [*] Gerando {total_blocos} arquivo(s) de {bloco_size} página(s)...")

        for i in range(0, total_paginas, bloco_size):
            writer = pypdf.PdfWriter()
            num_bloco = (i // bloco_size) + 1
            paginas_do_bloco = []

            for j in range(i, min(i + bloco_size, total_paginas)):
                writer.add_page(reader.pages[j])
                paginas_do_bloco.append(j + 1)

            if bloco_size == 1:
                nome_saida = f"{caminho_pdf.stem}_Pagina_{num_bloco:03d}.pdf"
            else:
                nome_saida = f"{caminho_pdf.stem}_Parte_{num_bloco:03d}_pags_{paginas_do_bloco[0]}-{paginas_do_bloco[-1]}.pdf"

            caminho_saida = obter_caminho_unico(pasta_destino / nome_saida)
            with open(caminho_saida, "wb") as f_out:
                writer.write(f_out)
            writer.close()

            print(f"   [OK] {caminho_saida.name}")
            arquivos_gerados.append(caminho_saida)

    print("\n" + "=" * 60)
    print(f" [CONCLUÍDO] {len(arquivos_gerados)} PDFs gerados com sucesso!")
    print(f" Pasta: {pasta_destino}")
    print("=" * 60)
    return arquivos_gerados


def menu_separar_pdf(diretorio_base: Path):
    """Sub-menu interativo para guiar a separação de PDFs."""
    pasta_downloads = obter_pasta_downloads()

    # Procura PDFs disponíveis na pasta atual e nos Downloads
    pdfs_locais = list(diretorio_base.glob("*.pdf"))
    pdfs_downloads = list(pasta_downloads.glob("*.pdf")) if pasta_downloads.exists() else []

    print("\n" + "=" * 60)
    print("       ✂️ SEPARADOR DE PDFS GIGANTES (SPLIT) ✂️")
    print("=" * 60)

    todos_pdfs = pdfs_locais + [p for p in pdfs_downloads if p not in pdfs_locais]
    # Limita listagem a 9 itens para não poluir
    pdfs_para_mostrar = todos_pdfs[:9]

    if pdfs_para_mostrar:
        print(" PDFs encontrados recentemente:")
        for idx, pdf in enumerate(pdfs_para_mostrar, start=1):
            origem = "Downloads" if pdf.parent == pasta_downloads else "Pasta Atual"
            print(f"  [{idx}] {pdf.name} ({origem})")
        print("  [0] Digitar outro nome ou arrastar o arquivo PDF para cá")
    else:
        print(" [i] Nenhum PDF encontrado automaticamente.")

    escolha = input("\n Escolha o PDF para separar (número ou arraste o arquivo): ").strip().strip('"').strip("'")
    
    arquivo_selecionado = None
    if escolha.isdigit():
        num = int(escolha)
        if 1 <= num <= len(pdfs_para_mostrar):
            arquivo_selecionado = pdfs_para_mostrar[num - 1]

    if arquivo_selecionado is None:
        if escolha and Path(escolha).exists() and Path(escolha).is_file():
            arquivo_selecionado = Path(escolha)
        else:
            print(" [!] Arquivo não encontrado ou seleção cancelada.")
            return

    print(f"\n Arquivo selecionado: '{arquivo_selecionado.name}'")
    print("\n Como deseja separar esse PDF?")
    print(" [1] 🧠 Inteligente: Detectar CNPJ, Código ou Nome de cada cliente")
    print(" [2] 📄 Página por página: cada folha vira 1 PDF separado")
    print(" [3] 📑 Por bloco: a cada N páginas (ex: a cada 2 páginas por cliente)")
    print(" [0] Cancelar")

    opcao_modo = input("\n Escolha a opção [1-3]: ").strip()

    if opcao_modo == "1":
        separar_pdf(arquivo_selecionado, modo="inteligente")
    elif opcao_modo == "2":
        separar_pdf(arquivo_selecionado, modo="pagina", paginas_por_bloco=1)
    elif opcao_modo == "3":
        qtd_str = input(" Quantas páginas pertencem a cada cliente? (Ex: 2): ").strip()
        qtd = int(qtd_str) if qtd_str.isdigit() and int(qtd_str) > 0 else 2
        separar_pdf(arquivo_selecionado, modo="bloco", paginas_por_bloco=qtd)
    else:
        print(" Operação cancelada.")


def menu_interativo(diretorio_padrao: Path):
    """Exibe menu interativo e amigável para qualquer usuário."""
    pasta_downloads = obter_pasta_downloads()
    
    while True:
        print("\n" + "=" * 60)
        print("          🤖 ROBOZINHO DE ARQUIVOS & PDFS 🤖")
        print("=" * 60)
        print(f" [1] 📥 Organizar a pasta DOWNLOADS:")
        print(f"     -> {pasta_downloads}")
        print(f" [2] 📁 Organizar ESTA PASTA do Robozinho:")
        print(f"     -> {diretorio_padrao}")
        print(f" [3] 📂 Escolher OUTRA pasta (digite ou arraste a pasta)")
        print(f" [4] 📑 Apenas Extrair ZIPs e Juntar PDFs (fiscal/contábil)")
        print(f" [5] ✂️  Separar PDF gigante (Split por CNPJ, página ou bloco)")
        print(f" [0] ❌ Sair")
        print("=" * 60)
        
        opcao = input(" Escolha uma opção [0-5]: ").strip()
        
        if opcao == "1":
            print(f"\n [*] Acessando pasta Downloads...")
            executar_fluxo_completo(pasta_downloads)
            break
        elif opcao == "2":
            executar_fluxo_completo(diretorio_padrao)
            break
        elif opcao == "3":
            caminho_input = input("\n Arraste a pasta para cá ou cole o caminho: ").strip().strip('"').strip("'")
            pasta_escolhida = Path(caminho_input)
            if pasta_escolhida.exists() and pasta_escolhida.is_dir():
                executar_fluxo_completo(pasta_escolhida)
            else:
                print(f" [!] Pasta não encontrada: {caminho_input}")
                continue
            break
        elif opcao == "4":
            print("\n Onde deseja processar os PDFs?")
            print(f" [1] Na pasta Downloads ({pasta_downloads})")
            print(f" [2] Nesta pasta atual ({diretorio_padrao})")
            sub_opcao = input(" Escolha [1 ou 2]: ").strip()
            alvo = pasta_downloads if sub_opcao == "1" else diretorio_padrao
            extrair_todos_zips(alvo)
            juntar_pdfs_inteligente(alvo)
            print("\n [OK] Processo de extração e junção de PDFs concluído!")
            break
        elif opcao == "5":
            menu_separar_pdf(diretorio_padrao)
            break
        elif opcao == "0":
            print(" Até mais!")
            break
        else:
            print(" [!] Opção inválida. Digite um número de 0 a 5.")


if __name__ == "__main__":
    diretorio_atual = Path.cwd()

    # Suporte a argumentos CLI
    if len(sys.argv) > 1:
        comando = sys.argv[1].lower()
        
        if comando in ("downloads", "download"):
            executar_fluxo_completo(obter_pasta_downloads())

        elif comando in ("auto", "tudo", "full"):
            executar_fluxo_completo(diretorio_atual)
            
        elif comando in ("extrair", "unzip"):
            extrair_todos_zips(diretorio_atual)
            
        elif comando in ("juntar-inteligente", "fiscal", "smart"):
            juntar_pdfs_inteligente(diretorio_atual)
            
        elif comando in ("separar", "split") and len(sys.argv) >= 3:
            arquivo = Path(sys.argv[2])
            modo = "inteligente"
            if "--pagina" in sys.argv:
                modo = "pagina"
            separar_pdf(arquivo, modo=modo)

        elif comando == "juntar" and len(sys.argv) >= 4:
            args = sys.argv[2:]
            saida = Path("PDF_Combinado.pdf")
            if "-o" in args:
                idx_o = args.index("-o")
                if idx_o + 1 < len(args):
                    saida = Path(args[idx_o + 1])
                    args = args[:idx_o] + args[idx_o + 2:]
            
            lista_arquivos = [Path(a) for a in args if a.endswith(".pdf")]
            juntar_lista_pdfs(lista_arquivos, saida)
            
        elif comando in ("organizar", "sort"):
            organizar_downloads(diretorio_atual)
            
        elif comando == "pasta" and len(sys.argv) >= 3:
            pasta_alvo = Path(sys.argv[2])
            if pasta_alvo.exists() and pasta_alvo.is_dir():
                executar_fluxo_completo(pasta_alvo)
            else:
                print(f"[ERRO] Pasta não encontrada: {pasta_alvo}")
        else:
            print("Comandos disponíveis:")
            print("  python organizador_arquivos.py downloads             (processa a pasta Downloads)")
            print("  python organizador_arquivos.py auto                  (processa a pasta atual)")
            print("  python organizador_arquivos.py separar arquivo.pdf   (separa por CNPJ/Cliente)")
            print("  python organizador_arquivos.py pasta \"C:\\caminho\"")
            print("  python organizador_arquivos.py fiscal")
            print("  python organizador_arquivos.py juntar doc1.pdf doc2.pdf -o final.pdf")
    else:
        # Modo interativo padrão (duplo clique ou sem argumentos)
        menu_interativo(diretorio_atual)

